from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from html import escape
import threading
import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import AgentRuntime, answer_internal_product_assistant, normalize_message_language, normalize_message_style
from .config import Settings
from .connectors import build_tool_registry
from .domain import (
    AgentTask,
    AgentTaskType,
    ContactAttempt,
    ContactAttemptStatus,
    ContactType,
    ContractDraft,
    ContractDraftStatus,
    ConversationMessage,
    Product,
    SearchRequest,
    SupplierContact,
)
from .model_providers import LocalDemoModelProvider, OllamaModelProvider
from .repositories import InMemoryRepository
from .workers import (
    _apply_supplier_reply_analysis,
    process_contract_draft,
    process_product_search,
    process_supplier_contact,
    run_gmail_inbound_sync_loop,
    sync_gmail_inbound_messages,
)


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


class ProductAssistantPayload(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


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
        request = repo.get_search_request(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="search request not found")
        products = repo.list_products_for_request(request_id)
        duplicates = list_duplicate_supplier_candidates(request, repo)
        return {
            "items": [serialize_product_card(product, repo) for product in products],
            "duplicates": duplicates,
            "total": len(products),
            "duplicatesTotal": len(duplicates),
        }

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

        selected = select_contact(contacts, payload.supplierContactId if payload else None, product=product)
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
        _apply_supplier_reply_analysis(repo, _runtime(), product, message)
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

    @app.post("/api/products/{product_id}/assistant-chat")
    def product_assistant_chat(product_id: UUID, payload: ProductAssistantPayload):
        product = repo.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        user_message = create_internal_assistant_message("user", payload.message)
        assistant_messages = list_internal_assistant_messages(product)
        assistant_messages.append(user_message)
        try:
            answer = answer_internal_product_assistant(
                _runtime().model_provider,
                product,
                repo.list_contacts_for_product(product.id),
                repo.list_conversation_messages_for_product(product.id),
                payload.message,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        assistant_messages.append(create_internal_assistant_message("assistant", answer))
        save_internal_assistant_messages(product, assistant_messages)
        return {"reply": answer, "messages": assistant_messages}

    @app.post("/api/products/{product_id}/contracts", status_code=status.HTTP_201_CREATED)
    def create_contract_draft(product_id: UUID, background_tasks: BackgroundTasks):
        product = repo.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        contacts = repo.list_contacts_for_product(product_id)
        if not contacts:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product has no supplier contact available")
        selected = select_best_contact(contacts, product)
        draft = ContractDraft.create(product.id, selected.id, product.supplier_name)
        task = AgentTask.create(
            AgentTaskType.CONTRACT_DRAFT,
            {
                "productId": str(product.id),
                "supplierContactId": str(selected.id),
                "contractDraftId": str(draft.id),
            },
        )
        draft.agent_task_id = task.id
        repo.add_agent_task(task)
        repo.contracts.add_contract_draft(draft)
        if settings.auto_process_contract_tasks:
            background_tasks.add_task(process_contract_draft, repo, _runtime(), task.id)
        return serialize_contract_draft(draft, include_text=False)

    @app.get("/api/products/{product_id}/contracts")
    def list_contract_drafts(product_id: UUID):
        if repo.get_product(product_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        return {
            "items": [
                serialize_contract_draft(draft, include_text=False)
                for draft in repo.contracts.list_contract_drafts_for_product(product_id)
            ]
        }

    @app.get("/api/contracts/{contract_id}")
    def get_contract_draft(contract_id: UUID):
        draft = repo.contracts.get_contract_draft(contract_id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="contract draft not found")
        return serialize_contract_draft(draft, include_text=True)

    @app.get("/api/contracts/{contract_id}/download")
    def download_contract_draft(contract_id: UUID):
        draft = repo.contracts.get_contract_draft(contract_id)
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="contract draft not found")
        if not draft.is_downloadable():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="contract draft is not ready for download")
        return Response(
            content=draft.draft_text or "",
            media_type=draft.content_type,
            headers={"Content-Disposition": f'attachment; filename="{draft.file_name}"'},
        )

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

    @app.get("/api/products/{product_id}/export.xlsx")
    def export_product(product_id: UUID):
        product = repo.get_product(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        content = build_product_excel_html(product, repo)
        filename = f"product-supplier-{product.id}.xls"
        return Response(
            content=content,
            media_type="application/vnd.ms-excel; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def _runtime() -> AgentRuntime:
        if app.state.runtime is None:
            app.state.runtime = build_runtime(settings)
        return app.state.runtime

    return app


def select_contact(contacts: list[SupplierContact], contact_id: UUID | None, product: Product | None = None) -> SupplierContact:
    if contact_id is None:
        return select_best_contact(contacts, product)
    for contact in contacts:
        if contact.id == contact_id:
            return contact
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="supplier contact not found")


def select_best_contact(contacts: list[SupplierContact], product: Product | None = None) -> SupplierContact:
    ranked = sorted(contacts, key=lambda contact: (-contact_quality_score(contact, product), contact.contact_value.lower()))
    return ranked[0]


def contact_quality_score(contact: SupplierContact, product: Product | None = None) -> int:
    score = 40
    value = contact.contact_value.lower()
    if contact.is_primary:
        score += 20
    if contact.contact_type == ContactType.EMAIL:
        score += 25
        local, _, domain = value.partition("@")
        if local in {"sales", "b2b", "wholesale", "orders", "business", "export"}:
            score += 25
        elif local in {"info", "contact", "support", "hello"}:
            score += 12
        if product and product.source_domain and domain and product.source_domain.lower().endswith(domain):
            score += 18
        if domain in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com"}:
            score -= 12
    elif contact.contact_type == ContactType.TELEGRAM:
        score += 15
    try:
        score += int(contact.metadata.get("confidence", 0))
    except (TypeError, ValueError):
        pass
    return max(0, min(100, score))


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


def list_duplicate_supplier_candidates(request: SearchRequest, repo: InMemoryRepository) -> list[dict[str, Any]]:
    if request.agent_task_id is None:
        return []
    task = repo.get_agent_task(request.agent_task_id)
    if task is None:
        return []
    duplicates = []
    for index, error in enumerate((task.output_payload or {}).get("errors") or []):
        if not isinstance(error, dict):
            continue
        reasons = [str(reason) for reason in error.get("errors") or []]
        if "duplicate supplier for search request" not in reasons:
            continue
        raw = error.get("raw") or {}
        if not isinstance(raw, dict):
            raw = {}
        duplicates.append(serialize_duplicate_supplier_candidate(raw, request.id, index, reasons))
    return duplicates


def serialize_duplicate_supplier_candidate(
    raw: dict[str, Any],
    search_request_id: UUID,
    index: int,
    reasons: list[str],
) -> dict[str, Any]:
    product_url = str(raw.get("productUrl") or raw.get("product_url") or "")
    contacts = []
    for contact in raw.get("contacts") or []:
        if not isinstance(contact, dict):
            continue
        contact_type = str(contact.get("type") or contact.get("contactType") or "").strip().lower()
        contact_value = str(contact.get("value") or contact.get("contactValue") or "").strip()
        if not contact_type or not contact_value:
            continue
        contacts.append(
            {
                "id": f"duplicate-{index}-contact-{len(contacts)}",
                "contactType": contact_type,
                "contactValue": contact_value,
                "isPrimary": len(contacts) == 0,
                "isPreferred": len(contacts) == 0,
            }
        )
    return {
        "id": f"duplicate-{search_request_id}-{index}",
        "searchRequestId": str(search_request_id),
        "title": str(raw.get("title") or "Duplicate supplier candidate"),
        "description": raw.get("description"),
        "price": serialize_decimal(raw.get("price")),
        "currency": raw.get("currency"),
        "productUrl": product_url,
        "supplierName": raw.get("supplierName") or raw.get("supplier_name"),
        "sourceDomain": raw.get("sourceDomain") or raw.get("source_domain"),
        "images": list(raw.get("images") or []),
        "attributes": dict(raw.get("attributes") or {}),
        "contacts": contacts,
        "duplicateReason": "; ".join(reasons),
        "isDuplicate": True,
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
                "qualityScore": contact_quality_score(contact, product),
                "isPreferred": contact.id == select_best_contact(repo.list_contacts_for_product(product.id), product).id,
            }
            for contact in repo.list_contacts_for_product(product.id)
        ]
        card["supplierComparison"] = calculate_supplier_comparison(product, repo)
    return card


def serialize_product_detail(product: Product, repo: InMemoryRepository) -> dict[str, Any]:
    detail = serialize_product_card(product, repo)
    detail["contacts"] = [
        {
            "id": str(contact.id),
            "contactType": contact.contact_type.value,
            "contactValue": contact.contact_value,
            "isPrimary": contact.is_primary,
            "qualityScore": contact_quality_score(contact, product),
            "isPreferred": contact.id == select_best_contact(repo.list_contacts_for_product(product.id), product).id,
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
    detail["assistantMessages"] = list_internal_assistant_messages(product)
    return detail


def create_internal_assistant_message(role: str, body: str) -> dict[str, str]:
    return {
        "id": str(uuid4()),
        "role": role,
        "body": body.strip(),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def list_internal_assistant_messages(product: Product) -> list[dict[str, str]]:
    raw_messages = product.attributes.get("internalAssistantMessages")
    if not isinstance(raw_messages, list):
        return []
    messages: list[dict[str, str]] = []
    for raw_message in raw_messages:
        if not isinstance(raw_message, dict):
            continue
        role = str(raw_message.get("role") or "").strip()
        body = str(raw_message.get("body") or "").strip()
        if role not in {"user", "assistant"} or not body:
            continue
        messages.append(
            {
                "id": str(raw_message.get("id") or uuid4()),
                "role": role,
                "body": body,
                "createdAt": str(raw_message.get("createdAt") or ""),
            }
        )
    return messages


def save_internal_assistant_messages(product: Product, messages: list[dict[str, str]]) -> None:
    product.attributes["internalAssistantMessages"] = messages[-80:]


def calculate_supplier_comparison(product: Product, repo: InMemoryRepository) -> dict[str, Any]:
    contacts = repo.list_contacts_for_product(product.id)
    attempts = repo.list_attempts_for_product(product.id)
    messages = repo.list_conversation_messages_for_product(product.id)
    comparable_products = [
        candidate
        for candidate in repo.list_products_for_request(product.search_request_id)
        if (
            product.search_request_id is not None
            and candidate.price is not None
            and product.currency
            and candidate.currency == product.currency
            and Decimal(candidate.price) > 0
        )
    ]
    min_price = min((Decimal(candidate.price) for candidate in comparable_products), default=None)
    price_score = score_price(product, min_price)
    contact_score = score_contactability(contacts)
    response_score = score_supplier_response(attempts, messages)
    completeness_score = score_data_completeness(product, contacts)
    source_score = score_source_traceability(product)
    communication_score = score_communication(product, messages)
    contact_quality_score_value = max((contact_quality_score(contact, product) for contact in contacts), default=20)
    overall = round(
        price_score * 0.25
        + contact_score * 0.15
        + contact_quality_score_value * 0.15
        + response_score * 0.15
        + communication_score * 0.15
        + completeness_score * 0.10
        + source_score * 0.05
    )
    return {
        "overallRating": overall,
        "ratingLabel": supplier_rating_label(overall),
        "metrics": {
            "priceScore": price_score,
            "contactabilityScore": contact_score,
            "responseScore": response_score,
            "communicationScore": communication_score,
            "contactQualityScore": contact_quality_score_value,
            "dataCompletenessScore": completeness_score,
            "sourceTraceabilityScore": source_score,
        },
        "priceRank": price_rank(product, comparable_products),
        "priceDeltaPercent": price_delta_percent(product, min_price),
        "comparedProductsCount": len(comparable_products),
    }


def score_price(product: Product, min_price: Decimal | None) -> int:
    if product.price is None or min_price is None or Decimal(product.price) <= 0:
        return 45
    return int(max(0, min(100, round((min_price / Decimal(product.price)) * 100))))


def score_contactability(contacts: list[SupplierContact]) -> int:
    types = {contact.contact_type for contact in contacts}
    if ContactType.EMAIL in types and ContactType.TELEGRAM in types:
        return 100
    if ContactType.EMAIL in types:
        return 85
    if ContactType.TELEGRAM in types:
        return 75
    return 20


def score_supplier_response(attempts: list[ContactAttempt], messages: list[ConversationMessage]) -> int:
    if any(message.direction.value == "inbound" for message in messages):
        return 100
    statuses = {attempt.status for attempt in attempts}
    if ContactAttemptStatus.RESPONDED in statuses:
        return 95
    if ContactAttemptStatus.SENT in statuses:
        return 80
    if statuses & {ContactAttemptStatus.QUEUED, ContactAttemptStatus.RUNNING}:
        return 55
    if ContactAttemptStatus.FAILED in statuses:
        return 20
    return 40


def score_communication(product: Product, messages: list[ConversationMessage]) -> int:
    raw = product.attributes.get("communicationScore")
    if raw is not None:
        try:
            return max(0, min(100, int(float(str(raw)))))
        except (TypeError, ValueError):
            pass
    inbound_count = sum(1 for message in messages if message.direction.value == "inbound")
    outbound_count = sum(1 for message in messages if message.direction.value == "outbound")
    if inbound_count >= 2:
        return 85
    if inbound_count == 1 and outbound_count >= 1:
        return 75
    if inbound_count == 1:
        return 65
    return 40


def score_data_completeness(product: Product, contacts: list[SupplierContact]) -> int:
    checks = [
        bool(product.title),
        bool(product.product_url),
        product.price is not None,
        bool(product.currency),
        bool(product.supplier_name),
        bool(product.description),
        bool(product.images),
        bool(contacts),
    ]
    return round(sum(1 for value in checks if value) / len(checks) * 100)


def score_source_traceability(product: Product) -> int:
    if product.product_url.startswith("https://") and product.source_domain:
        return 100
    if product.product_url.startswith("http://") and product.source_domain:
        return 80
    if product.product_url:
        return 55
    return 20


def build_product_excel_html(product: Product, repo: InMemoryRepository) -> str:
    detail = serialize_product_detail(product, repo)
    comparison = detail.get("supplierComparison") or {}
    metrics = comparison.get("metrics") or {}
    analysis = product.attributes.get("supplierReplyAnalysis")
    if not isinstance(analysis, dict):
        analysis = {}
    rows = [
        ("Product", product.title),
        ("Product URL", product.product_url),
        ("Supplier", product.supplier_name or ""),
        ("Source domain", product.source_domain or ""),
        ("Price", f"{serialize_decimal(product.price) or ''} {product.currency or ''}".strip()),
        ("Overall rating", str(comparison.get("overallRating", ""))),
        ("Rating label", str(comparison.get("ratingLabel", ""))),
        ("Contact score", str(metrics.get("contactabilityScore", ""))),
        ("Contact quality score", str(metrics.get("contactQualityScore", ""))),
        ("Communication score", str(metrics.get("communicationScore", ""))),
        ("Response score", str(metrics.get("responseScore", ""))),
        ("AI reply summary", str(analysis.get("summary") or product.attributes.get("supplierReplySummary") or "")),
        ("AI next step", str(analysis.get("nextStep") or product.attributes.get("supplierReplyNextStep") or "")),
        ("Extracted price", str(analysis.get("price") or product.attributes.get("price") or "")),
        ("Extracted currency", str(analysis.get("currency") or product.attributes.get("currency") or "")),
        ("Extracted MOQ", str(analysis.get("moq") or product.attributes.get("supplierMoq") or "")),
        ("Extracted lead time", str(analysis.get("leadTime") or product.attributes.get("supplierLeadTime") or "")),
        ("Availability", str(analysis.get("availability") or product.attributes.get("supplierAvailability") or "")),
        ("Payment terms", str(analysis.get("paymentTerms") or product.attributes.get("supplierPaymentTerms") or "")),
        ("Delivery terms", str(analysis.get("deliveryTerms") or product.attributes.get("supplierDeliveryTerms") or "")),
        ("Risk flags", str(analysis.get("riskFlags") or product.attributes.get("supplierRiskFlags") or "")),
    ]
    contact_rows = [
        (
            f"{contact['contactType']} contact",
            f"{contact['contactValue']} | preferred={contact.get('isPreferred')} | quality={contact.get('qualityScore')}",
        )
        for contact in detail.get("contacts", [])
    ]
    message_rows = [
        (
            f"{message['direction']} {message['status']}",
            f"{message.get('subject') or ''}\n{message.get('body') or ''}",
        )
        for message in detail.get("conversationMessages", [])
    ]
    html_rows = "\n".join(
        f"<tr><th>{escape(str(label))}</th><td>{escape(str(value))}</td></tr>"
        for label, value in rows + contact_rows + message_rows
    )
    return (
        "<html><head><meta charset=\"utf-8\"></head><body>"
        "<table>"
        "<tr><th colspan=\"2\">Product and supplier information</th></tr>"
        f"{html_rows}"
        "</table>"
        "</body></html>"
    )


def price_rank(product: Product, comparable_products: list[Product]) -> int | None:
    if product.price is None or not comparable_products:
        return None
    ordered_prices = sorted({Decimal(candidate.price) for candidate in comparable_products if candidate.price is not None})
    try:
        return ordered_prices.index(Decimal(product.price)) + 1
    except ValueError:
        return None


def price_delta_percent(product: Product, min_price: Decimal | None) -> int | None:
    if product.price is None or min_price is None or min_price <= 0:
        return None
    return int(round(((Decimal(product.price) - min_price) / min_price) * 100))


def supplier_rating_label(score: int) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "strong"
    if score >= 55:
        return "average"
    return "weak"


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


def serialize_contract_draft(draft: ContractDraft, include_text: bool = False) -> dict[str, Any]:
    missing_fields = draft.extracted_data.get("missingFields") or draft.extracted_data.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = [str(missing_fields)]
    payload = {
        "id": str(draft.id),
        "productId": str(draft.product_id),
        "supplierContactId": str(draft.supplier_contact_id),
        "agentTaskId": str(draft.agent_task_id) if draft.agent_task_id else None,
        "supplierName": draft.supplier_name,
        "status": draft.status.value,
        "title": draft.title,
        "extractedData": draft.extracted_data,
        "missingFields": [str(value) for value in missing_fields],
        "fileName": draft.file_name,
        "contentType": draft.content_type,
        "errorMessage": draft.error_message,
        "createdAt": draft.created_at.isoformat(),
        "updatedAt": draft.updated_at.isoformat(),
        "completedAt": draft.completed_at.isoformat() if draft.completed_at else None,
    }
    if include_text:
        payload["draftText"] = draft.draft_text
    return payload


def serialize_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def search_duration_seconds(request: SearchRequest) -> int | None:
    start = request.started_at
    if start is None:
        return None
    end = request.completed_at or datetime.now(timezone.utc)
    return max(0, int((end - start).total_seconds()))


app = create_app()
