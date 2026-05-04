from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import threading
import logging
from typing import Any
from uuid import UUID

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import AgentRuntime, normalize_message_language, normalize_message_style
from .config import Settings
from .connectors import build_tool_registry
from .domain import (
    AgentTask,
    AgentTaskType,
    ContactAttempt,
    ContactAttemptStatus,
    ConversationMessage,
    Product,
    SearchRequest,
    SupplierContact,
)
from .model_providers import LocalDemoModelProvider, OllamaModelProvider
from .repositories import InMemoryRepository
from .workers import process_product_search, process_supplier_contact, run_gmail_inbound_sync_loop, sync_gmail_inbound_messages


logger = logging.getLogger(__name__)


class CreateSearchRequestPayload(BaseModel):
    queryText: str
    maxResults: int = Field(default=5, ge=1, le=50)


class ContactSupplierPayload(BaseModel):
    supplierContactId: UUID | None = None
    language: str = "ru"
    style: str = "formal"


class RecordInboundMessagePayload(BaseModel):
    supplierContactId: UUID
    contactAttemptId: UUID
    channel: str
    body: str
    subject: str | None = None
    fromAddress: str | None = None
    toAddress: str | None = None
    externalMessageId: str | None = None
    providerTimestamp: datetime | None = None


class AgentReplyPayload(BaseModel):
    supplierContactId: UUID
    replyToMessageId: UUID | None = None
    language: str = "ru"
    style: str = "formal"


class GmailSyncPayload(BaseModel):
    requireAiReplyApproval: bool = False


class ConfiguredModelProvider:
    def __init__(self, provider: str, model_name: str) -> None:
        self.provider = provider
        self.model_name = model_name
        self.name = f"{provider}:{model_name}" if provider and model_name else "unconfigured-model"

    def complete(self, prompt: str, tools=None):
        raise RuntimeError("configured model provider is not wired for direct completions yet")


def build_model_provider(settings: Settings):
    provider = settings.model_provider.strip().lower()
    if provider == "local_demo":
        return LocalDemoModelProvider(name=f"local_demo:{settings.model_name or 'browser-extraction-v0'}")
    if provider == "ollama":
        return OllamaModelProvider(
            base_url=settings.ollama_base_url,
            model_name=settings.model_name,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
    return ConfiguredModelProvider(settings.model_provider, settings.model_name)


def build_runtime(settings: Settings) -> AgentRuntime:
    model_provider = build_model_provider(settings)
    return AgentRuntime(
        model_provider=model_provider,
        tool_registry=build_tool_registry(settings, model_provider),
    )


def create_app(repository: InMemoryRepository | None = None, runtime: AgentRuntime | None = None) -> FastAPI:
    settings = Settings.from_env()
    repo = repository or InMemoryRepository()
    app = FastAPI(title="Product Sourcing MVP", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.webui_base_url,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://host.docker.internal:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.repo = repo
    app.state.runtime = runtime
    app.state.gmail_sync_stop_event = None
    app.state.gmail_sync_thread = None

    @app.on_event("startup")
    def start_gmail_inbound_sync_loop():
        if not settings.auto_sync_gmail_inbound or not settings.email_inbound_provider:
            return
        if app.state.gmail_sync_thread is not None:
            return
        try:
            runtime_value = _runtime()
            gmail_connector = runtime_value.tool_registry.require("gmail_inbound")
        except Exception as exc:
            logger.warning("Gmail inbound background sync is not available: %s", exc)
            return
        stop_event = threading.Event()
        thread = threading.Thread(
            target=run_gmail_inbound_sync_loop,
            args=(
                repo,
                runtime_value,
                gmail_connector,
                settings.email_inbound_sync_limit,
                settings.gmail_inbound_sync_interval_seconds,
            ),
            kwargs={"stop_event": stop_event},
            name="gmail-inbound-sync",
            daemon=True,
        )
        app.state.gmail_sync_stop_event = stop_event
        app.state.gmail_sync_thread = thread
        thread.start()
        logger.info(
            "Started Gmail inbound background sync: interval=%s limit=%s",
            settings.gmail_inbound_sync_interval_seconds,
            settings.email_inbound_sync_limit,
        )

    @app.on_event("shutdown")
    def stop_gmail_inbound_sync_loop():
        stop_event = app.state.gmail_sync_stop_event
        if stop_event is not None:
            stop_event.set()

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "appEnv": settings.app_env,
            "workerRequired": True,
        }

    @app.post("/api/search-requests", status_code=status.HTTP_201_CREATED)
    def create_search_request(payload: CreateSearchRequestPayload, background_tasks: BackgroundTasks):
        try:
            request = SearchRequest.create(payload.queryText, max_results=payload.maxResults)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        task = AgentTask.create(
            AgentTaskType.PRODUCT_SEARCH,
            {
                "searchRequestId": str(request.id),
                "queryText": request.query_text,
                "maxResults": request.max_results,
            },
        )
        request.agent_task_id = task.id
        repo.add_agent_task(task)
        repo.add_search_request(request)
        if settings.auto_process_search_tasks:
            background_tasks.add_task(
                process_product_search,
                repo,
                _runtime(),
                task.id,
                settings.allow_products_without_contacts,
            )
        return serialize_search_request(request, repo)

    @app.get("/api/search-requests")
    def list_search_requests():
        return {
            "items": [serialize_search_request(request, repo) for request in repo.list_search_requests()]
        }

    @app.get("/api/search-requests/{request_id}")
    def get_search_request(request_id: UUID):
        request = repo.get_search_request(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="search request not found")
        return serialize_search_request(request, repo)

    @app.get("/api/search-requests/{request_id}/products")
    def list_request_products(request_id: UUID):
        if repo.get_search_request(request_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="search request not found")
        products = repo.list_products_for_request(request_id)
        return {"items": [serialize_product_card(product, repo) for product in products], "total": len(products)}

    @app.get("/api/products/{product_id}")
    def get_product(product_id: UUID):
        product = repo.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        return serialize_product_detail(product, repo)

    @app.post("/api/products/{product_id}/contact-supplier", status_code=status.HTTP_201_CREATED)
    def contact_supplier(
        product_id: UUID,
        background_tasks: BackgroundTasks,
        payload: ContactSupplierPayload | None = None,
    ):
        product = repo.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")

        attempts = repo.list_attempts_for_product(product_id)
        if ContactAttempt.has_active(attempts):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="active contact attempt already exists for this product",
            )

        contacts = repo.list_contacts_for_product(product_id)
        if not contacts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="product has no supplier contact available",
            )

        selected = select_contact(contacts, payload.supplierContactId if payload else None)
        language = normalize_message_language(payload.language if payload else None)
        style_value = normalize_message_style(payload.style if payload else None)
        attempt = ContactAttempt.create(product.id, selected.id, selected.contact_type, "pending")
        task = AgentTask.create(
            AgentTaskType.SUPPLIER_CONTACT,
            {
                "productId": str(product.id),
                "supplierContactId": str(selected.id),
                "contactAttemptId": str(attempt.id),
                "channel": selected.contact_type.value,
                "language": language,
                "style": style_value,
            },
        )
        attempt.agent_task_id = task.id
        repo.add_agent_task(task)
        repo.add_contact_attempt(attempt)
        if settings.auto_process_supplier_contact_tasks:
            background_tasks.add_task(process_supplier_contact, repo, _runtime(), task.id)
        return serialize_contact_attempt(attempt)

    @app.post("/api/products/{product_id}/conversation-messages", status_code=status.HTTP_201_CREATED)
    def record_inbound_message(product_id: UUID, payload: RecordInboundMessagePayload):
        product = repo.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        contact = get_product_contact(repo, product_id, payload.supplierContactId)
        attempt = repo.contact_attempts.get(payload.contactAttemptId)
        if attempt is None or attempt.product_id != product_id or attempt.supplier_contact_id != contact.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="contact attempt not found")
        try:
            message = ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=payload.channel,
                subject=payload.subject,
                body=payload.body,
            from_address=payload.fromAddress or contact.contact_value,
            to_address=payload.toAddress,
            external_message_id=payload.externalMessageId,
            provider_timestamp=payload.providerTimestamp,
        )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        repo.add_conversation_message(message)
        if attempt.status == ContactAttemptStatus.SENT:
            attempt.transition_to(ContactAttemptStatus.RESPONDED)
        return serialize_conversation_message(message)

    @app.post("/api/products/{product_id}/conversation-reply", status_code=status.HTTP_201_CREATED)
    def request_agent_reply(product_id: UUID, payload: AgentReplyPayload, background_tasks: BackgroundTasks):
        product = repo.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        attempts = repo.list_attempts_for_product(product_id)
        if ContactAttempt.has_active(attempts):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="active contact attempt already exists for this product",
            )
        contact = get_product_contact(repo, product_id, payload.supplierContactId)
        if payload.replyToMessageId is not None and payload.replyToMessageId not in repo.conversation_messages:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation message not found")
        attempt = ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending")
        task = AgentTask.create(
            AgentTaskType.SUPPLIER_CONTACT,
            {
                "productId": str(product.id),
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(attempt.id),
                "channel": contact.contact_type.value,
                "conversationMode": "reply",
                "replyToMessageId": str(payload.replyToMessageId) if payload.replyToMessageId else None,
                "language": normalize_message_language(payload.language),
                "style": normalize_message_style(payload.style),
            },
        )
        attempt.agent_task_id = task.id
        repo.add_agent_task(task)
        repo.add_contact_attempt(attempt)
        if settings.auto_process_supplier_contact_tasks:
            background_tasks.add_task(process_supplier_contact, repo, _runtime(), task.id)
        return serialize_contact_attempt(attempt)

    @app.post("/api/conversations/sync-gmail")
    def sync_gmail(payload: GmailSyncPayload | None = None):
        try:
            connector = _runtime().tool_registry.require("gmail_inbound")
            return sync_gmail_inbound_messages(
                repo,
                connector,
                settings.email_inbound_sync_limit,
                _runtime(),
                require_ai_reply_approval=payload.requireAiReplyApproval if payload else False,
            )
        except KeyError:
            return {"messagesCreated": 0, "messagesSkipped": 0, "autoRepliesSent": 0}
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    def _runtime() -> AgentRuntime:
        if app.state.runtime is None:
            app.state.runtime = build_runtime(settings)
        return app.state.runtime

    return app


def select_contact(contacts: list[SupplierContact], contact_id: UUID | None) -> SupplierContact:
    if contact_id is None:
        return contacts[0]
    for contact in contacts:
        if contact.id == contact_id:
            return contact
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="supplier contact not found")


def get_product_contact(repo: InMemoryRepository, product_id: UUID, contact_id: UUID) -> SupplierContact:
    for contact in repo.list_contacts_for_product(product_id):
        if contact.id == contact_id:
            return contact
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="supplier contact not found")


def serialize_search_request(request: SearchRequest, repo: InMemoryRepository) -> dict[str, Any]:
    products = repo.list_products_for_request(request.id)
    awaiting_replies = 0
    received_replies = 0
    for product in products:
        attempts = repo.list_attempts_for_product(product.id)
        if any(attempt.status == ContactAttemptStatus.SENT for attempt in attempts):
            awaiting_replies += 1
        if any(message.direction.value == "inbound" for message in repo.list_conversation_messages_for_product(product.id)):
            received_replies += 1
    return {
        "id": str(request.id),
        "queryText": request.query_text,
        "maxResults": request.max_results,
        "status": request.status.value,
        "agentTaskId": str(request.agent_task_id) if request.agent_task_id else None,
        "errorMessage": request.error_message,
        "createdAt": request.created_at.isoformat(),
        "updatedAt": request.updated_at.isoformat(),
        "startedAt": request.started_at.isoformat() if request.started_at else None,
        "completedAt": request.completed_at.isoformat() if request.completed_at else None,
        "durationSeconds": search_duration_seconds(request),
        "productsCount": len(products),
        "awaitingRepliesCount": awaiting_replies,
        "receivedRepliesCount": received_replies,
    }


def serialize_product_card(product: Product, repo: InMemoryRepository | None = None) -> dict[str, Any]:
    card = {
        "id": str(product.id),
        "searchRequestId": str(product.search_request_id) if product.search_request_id else None,
        "title": product.title,
        "description": product.description,
        "price": serialize_decimal(product.price),
        "currency": product.currency,
        "productUrl": product.product_url,
        "supplierName": product.supplier_name,
        "sourceDomain": product.source_domain,
        "images": product.images,
        "attributes": product.attributes,
    }
    if repo is not None:
        card["contacts"] = [
            {
                "id": str(contact.id),
                "contactType": contact.contact_type.value,
                "contactValue": contact.contact_value,
                "isPrimary": contact.is_primary,
            }
            for contact in repo.list_contacts_for_product(product.id)
        ]
    return card


def serialize_product_detail(product: Product, repo: InMemoryRepository) -> dict[str, Any]:
    detail = serialize_product_card(product)
    detail["contacts"] = [
        {
            "id": str(contact.id),
            "contactType": contact.contact_type.value,
            "contactValue": contact.contact_value,
            "isPrimary": contact.is_primary,
        }
        for contact in repo.list_contacts_for_product(product.id)
    ]
    detail["contactAttempts"] = [
        serialize_contact_attempt(attempt) for attempt in repo.list_attempts_for_product(product.id)
    ]
    detail["conversationMessages"] = [
        serialize_conversation_message(message)
        for message in repo.list_conversation_messages_for_product(product.id)
    ]
    return detail


def serialize_conversation_message(message: ConversationMessage) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "productId": str(message.product_id),
        "supplierContactId": str(message.supplier_contact_id),
        "contactAttemptId": str(message.contact_attempt_id),
        "direction": message.direction.value,
        "channel": message.channel.value,
        "subject": message.subject,
        "body": message.body,
        "fromAddress": message.from_address,
        "toAddress": message.to_address,
        "status": message.status.value,
        "externalMessageId": message.external_message_id,
        "providerTimestamp": message.provider_timestamp.isoformat() if message.provider_timestamp else None,
        "errorMessage": message.error_message,
        "requiresUserApproval": message.requires_user_approval,
        "approvalReason": message.approval_reason,
        "createdAt": message.created_at.isoformat(),
        "updatedAt": message.updated_at.isoformat(),
        "sentAt": message.sent_at.isoformat() if message.sent_at else None,
    }


def serialize_contact_attempt(attempt: ContactAttempt) -> dict[str, Any]:
    return {
        "id": str(attempt.id),
        "productId": str(attempt.product_id),
        "supplierContactId": str(attempt.supplier_contact_id),
        "agentTaskId": str(attempt.agent_task_id) if attempt.agent_task_id else None,
        "channel": attempt.channel.value,
        "status": attempt.status.value,
        "messageText": attempt.message_text,
        "externalMessageId": attempt.external_message_id,
        "errorMessage": attempt.error_message,
        "createdAt": attempt.created_at.isoformat(),
        "updatedAt": attempt.updated_at.isoformat(),
        "sentAt": attempt.sent_at.isoformat() if attempt.sent_at else None,
        "completedAt": attempt.completed_at.isoformat() if attempt.completed_at else None,
    }


def serialize_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def search_duration_seconds(request: SearchRequest) -> int | None:
    start = request.started_at
    if start is None:
        return None
    end = request.completed_at or datetime.now(timezone.utc)
    return max(0, int((end - start).total_seconds()))


app = create_app()
