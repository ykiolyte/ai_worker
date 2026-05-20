from __future__ import annotations

from datetime import datetime
import re
import threading
import time
from uuid import UUID
from email.utils import parseaddr
from urllib.parse import urlparse

from .agent import (
    AgentRuntime,
    ConnectorResult,
    SafeMessagePolicy,
    analyze_supplier_reply,
    generate_contract_draft,
    generate_supplier_message,
    generate_supplier_reply,
    validate_agent_product_output,
)
from .domain import (
    AgentTaskStatus,
    ContactAttempt,
    ContactAttemptStatus,
    ContactType,
    ContractDraftStatus,
    ConversationMessage,
    Product,
    SearchRequestStatus,
    SupplierContact,
)
from .repositories import InMemoryRepository


_gmail_sync_lock = threading.Lock()


def process_product_search(
    repo: InMemoryRepository,
    runtime: AgentRuntime,
    task_id: UUID,
    allow_products_without_contacts: bool = False,
) -> None:
    task = repo.get_agent_task(task_id)
    if task is None:
        raise ValueError(f"agent task not found: {task_id}")

    request_id = UUID(task.input_payload["searchRequestId"])
    request = repo.get_search_request(request_id)
    if request is None:
        _fail_task_only(task, f"search request not found: {request_id}")
        return

    try:
        task.transition_to(AgentTaskStatus.RUNNING)
        request.transition_to(SearchRequestStatus.RUNNING)

        browser = runtime.tool_registry.require("browser_mcp")
        max_results = _task_max_results(task.input_payload)
        try:
            connector_result = browser.research(request.query_text, max_results=max_results)
        except TypeError:
            connector_result = browser.research(request.query_text)
        if not connector_result.success:
            raise RuntimeError(connector_result.error_message or "browser research failed")

        output = validate_agent_product_output(
            connector_result.payload or {},
            allow_products_without_contacts=allow_products_without_contacts,
        )
        existing_products = repo.list_products_for_request(request.id)
        existing_urls = {product.product_url for product in existing_products}
        existing_supplier_keys = {
            key
            for product in existing_products
            for key in [_supplier_dedupe_key(product)]
            if key
        }
        duplicate_errors = []
        limit_errors = []
        created_count = 0
        for product in output.products:
            product.search_request_id = request.id
            if product.product_url in existing_urls:
                duplicate_errors.append(
                    {
                        "index": None,
                        "errors": ["duplicate productUrl for search request"],
                        "raw": product.raw_agent_payload,
                    }
                )
                continue
            if created_count >= max_results:
                limit_errors.append(
                    {
                        "index": None,
                        "errors": ["maxResults limit reached"],
                        "raw": product.raw_agent_payload,
                    }
                )
                continue
            supplier_key = _supplier_dedupe_key(product)
            if supplier_key and supplier_key in existing_supplier_keys:
                duplicate_errors.append(
                    {
                        "index": None,
                        "errors": ["duplicate supplier for search request"],
                        "raw": product.raw_agent_payload,
                    }
                )
                continue
            existing_urls.add(product.product_url)
            if supplier_key:
                existing_supplier_keys.add(supplier_key)
            repo.add_product(product)
            created_count += 1
        demo_created = _ensure_demo_product(repo, request.id, existing_urls)

        skipped = output.skipped + duplicate_errors + limit_errors
        task.output_payload = {
            "productsCreated": created_count,
            "demoProductsCreated": 1 if demo_created else 0,
            "productsSkipped": len(skipped),
            "errors": skipped,
        }
        task.transition_to(AgentTaskStatus.COMPLETED)
        request.transition_to(SearchRequestStatus.COMPLETED)
    except Exception as exc:
        message = str(exc)
        task.error_message = message
        request.error_message = message
        if task.status == AgentTaskStatus.QUEUED:
            task.transition_to(AgentTaskStatus.RUNNING)
        if request.status == SearchRequestStatus.QUEUED:
            request.transition_to(SearchRequestStatus.RUNNING)
        if task.status == AgentTaskStatus.RUNNING:
            task.transition_to(AgentTaskStatus.FAILED)
        if request.status == SearchRequestStatus.RUNNING:
            request.transition_to(SearchRequestStatus.FAILED)


def _fail_task_only(task, message: str) -> None:
    task.error_message = message
    if task.status == AgentTaskStatus.QUEUED:
        task.transition_to(AgentTaskStatus.RUNNING)
    if task.status == AgentTaskStatus.RUNNING:
        task.transition_to(AgentTaskStatus.FAILED)


def _task_max_results(payload: dict) -> int:
    try:
        value = int(payload.get("maxResults", 5))
    except (TypeError, ValueError):
        return 5
    return max(1, min(value, 50))


def _supplier_dedupe_key(product: Product) -> str:
    if product.attributes.get("demo") == "true":
        return f"demo:{product.product_url}"
    domain = (product.source_domain or urlparse(product.product_url).hostname or "").lower().strip()
    if domain:
        return f"domain:{_normalize_supplier_domain(domain)}"
    for contact in product.contacts:
        if contact.contact_type == ContactType.EMAIL:
            _local, _sep, contact_domain = contact.contact_value.lower().partition("@")
            if contact_domain:
                return f"domain:{_normalize_supplier_domain(contact_domain)}"
        if contact.contact_type == ContactType.TELEGRAM:
            return f"telegram:{contact.contact_value.lower().removeprefix('https://t.me/').removeprefix('@')}"
    supplier_name = (product.supplier_name or "").strip().lower()
    if supplier_name:
        return f"name:{supplier_name}"
    return ""


def _normalize_supplier_domain(domain: str) -> str:
    normalized = domain.lower().strip().removeprefix("www.")
    return normalized.split(":", 1)[0]


def _ensure_demo_product(repo: InMemoryRepository, search_request_id: UUID, existing_urls: set[str]) -> bool:
    product_url = f"http://localhost:5173/demo/product-sourcing-demo/{search_request_id}"
    if product_url in existing_urls:
        return False
    if any(product.product_url == product_url for product in repo.list_products_for_request(search_request_id)):
        return False
    contact = SupplierContact.create(ContactType.EMAIL, "ezmmr4us@gmail.com")
    product = Product(
        search_request_id=search_request_id,
        title="Демо-карточка для презентации",
        product_url=product_url,
        description="Контролируемая карточка для демонстрации переписки с поставщиком через Gmail.",
        price=None,
        currency=None,
        contacts=[contact],
        supplier_name="Demo Supplier",
        attributes={"demo": "true", "purpose": "stakeholder-presentation"},
        raw_agent_payload={
            "source": "demo-supplier-product-card",
            "contactEmail": "ezmmr4us@gmail.com",
        },
    )
    contact.product_id = product.id
    repo.add_product(product)
    existing_urls.add(product_url)
    return True


def process_supplier_contact(repo: InMemoryRepository, runtime: AgentRuntime, task_id: UUID) -> None:
    task = repo.get_agent_task(task_id)
    if task is None:
        raise ValueError(f"agent task not found: {task_id}")

    product = repo.get_product(UUID(task.input_payload["productId"]))
    contact = repo.supplier_contacts.get(UUID(task.input_payload["supplierContactId"]))
    attempt = repo.contact_attempts.get(UUID(task.input_payload["contactAttemptId"]))

    if product is None:
        _fail_task_only(task, "product not found")
        return
    if contact is None:
        _fail_task_only(task, "supplier contact not found")
        return
    if attempt is None:
        _fail_task_only(task, "contact attempt not found")
        return

    conversation_message: ConversationMessage | None = None
    connector = None

    try:
        task.transition_to(AgentTaskStatus.RUNNING)
        attempt.transition_to(ContactAttemptStatus.RUNNING)

        if task.input_payload.get("conversationMode") == "reply":
            history = repo.list_conversation_messages_for_product(product.id)
            message = generate_supplier_reply(
                runtime.model_provider,
                product,
                history,
                language=_task_message_language(task.input_payload, history),
                style=str(task.input_payload.get("style") or "formal"),
            )
        else:
            message = generate_supplier_message(
                runtime.model_provider,
                product.title,
                product.product_url,
                language=str(task.input_payload.get("language") or "en"),
                style=str(task.input_payload.get("style") or "formal"),
            )
        if task.input_payload.get("conversationMode") == "reply":
            policy_errors = SafeMessagePolicy.validate_follow_up(message)
        else:
            policy_errors = SafeMessagePolicy.validate(message)
        if policy_errors:
            raise RuntimeError("; ".join(policy_errors))
        attempt.message_text = message

        if contact.contact_type == ContactType.EMAIL:
            connector = runtime.tool_registry.require("email")
            subject = f"Запрос по товару: {product.title}"
            conversation_message = ConversationMessage.create_outbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=contact.contact_type,
                subject=subject,
                body=message,
                from_address=getattr(connector, "from_address", None),
                to_address=contact.contact_value,
            )
            result = connector.send(contact.contact_value, subject, message)
        elif contact.contact_type == ContactType.TELEGRAM:
            connector = runtime.tool_registry.require("telegram")
            conversation_message = ConversationMessage.create_outbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=contact.contact_type,
                subject=None,
                body=message,
                from_address=getattr(connector, "default_chat_id", None),
                to_address=contact.contact_value,
            )
            result = connector.send(contact.contact_value, message)
        else:
            raise RuntimeError(f"unsupported contact type: {contact.contact_type}")

        if not result.success:
            raise RuntimeError(_redact_connector_error(result.error_message or "supplier contact connector failed", connector))

        attempt.external_message_id = result.external_id
        conversation_message.mark_sent(result.external_id, provider_timestamp=_connector_provider_timestamp(result))
        repo.add_conversation_message(conversation_message)
        attempt.transition_to(ContactAttemptStatus.SENT)
        task.output_payload = {
            "contactAttemptId": str(attempt.id),
            "conversationMessageId": str(conversation_message.id),
            "channel": attempt.channel.value,
            "externalMessageId": result.external_id,
        }
        task.transition_to(AgentTaskStatus.COMPLETED)
    except Exception as exc:
        message = _redact_connector_error(str(exc), connector)
        if conversation_message is not None and conversation_message.id not in repo.conversation_messages:
            conversation_message.mark_failed(message)
            repo.add_conversation_message(conversation_message)
        attempt.error_message = message
        task.error_message = message
        if attempt.status == ContactAttemptStatus.QUEUED:
            attempt.transition_to(ContactAttemptStatus.RUNNING)
        if task.status == AgentTaskStatus.QUEUED:
            task.transition_to(AgentTaskStatus.RUNNING)
        if attempt.status == ContactAttemptStatus.RUNNING:
            attempt.transition_to(ContactAttemptStatus.FAILED)
        if task.status == AgentTaskStatus.RUNNING:
            task.transition_to(AgentTaskStatus.FAILED)


def process_contract_draft(repo: InMemoryRepository, runtime: AgentRuntime, task_id: UUID) -> None:
    task = repo.get_agent_task(task_id)
    if task is None:
        raise ValueError(f"agent task not found: {task_id}")
    draft = repo.contracts.get_contract_draft(UUID(task.input_payload["contractDraftId"]))
    if draft is None:
        _fail_task_only(task, "contract draft not found")
        return
    product = repo.get_product(draft.product_id)
    if product is None:
        draft.mark_failed("product not found")
        _fail_task_only(task, "product not found")
        return
    try:
        task.transition_to(AgentTaskStatus.RUNNING)
        draft.transition_to(ContractDraftStatus.RUNNING)
        output = generate_contract_draft(
            runtime.model_provider,
            product,
            repo.list_conversation_messages_for_product(product.id),
        )
        draft.mark_ready(output["draftText"], output["extractedData"], title=output["title"])
        task.output_payload = {"contractDraftId": str(draft.id), "status": draft.status.value}
        task.transition_to(AgentTaskStatus.COMPLETED)
    except Exception as exc:
        message = str(exc)
        draft.mark_failed(message)
        task.error_message = message
        if task.status == AgentTaskStatus.QUEUED:
            task.transition_to(AgentTaskStatus.RUNNING)
        if task.status == AgentTaskStatus.RUNNING:
            task.transition_to(AgentTaskStatus.FAILED)


def _redact_connector_error(message: str, connector) -> str:
    redacted = message
    for secret in _connector_secret_values(connector):
        redacted = redacted.replace(secret, "***REDACTED***")
    return redacted


def _connector_secret_values(connector) -> list[str]:
    if connector is None:
        return []
    values = []
    for name in ("password", "bot_token", "api_key", "token"):
        value = getattr(connector, name, None)
        if isinstance(value, str) and value:
            values.append(value)
    return values


def _task_message_language(payload: dict, history: list[ConversationMessage]) -> str:
    explicit = str(payload.get("language") or "").strip().lower()
    if explicit:
        return explicit
    for message in reversed(history):
        if message.direction.value == "inbound" and re.search(r"[А-Яа-яЁё]", message.body or ""):
            return "ru"
    return "en"


def sync_gmail_inbound_messages(
    repo: InMemoryRepository,
    gmail_connector,
    limit: int = 20,
    runtime: AgentRuntime | None = None,
    require_ai_reply_approval: bool = False,
) -> dict[str, int]:
    if not _gmail_sync_lock.acquire(blocking=False):
        return {"messagesCreated": 0, "messagesSkipped": 0, "autoRepliesSent": 0}
    try:
        return _sync_gmail_inbound_messages_unlocked(
            repo,
            gmail_connector,
            limit=limit,
            runtime=runtime,
            require_ai_reply_approval=require_ai_reply_approval,
        )
    finally:
        _gmail_sync_lock.release()


def _sync_gmail_inbound_messages_unlocked(
    repo: InMemoryRepository,
    gmail_connector,
    limit: int = 20,
    runtime: AgentRuntime | None = None,
    require_ai_reply_approval: bool = False,
) -> dict[str, int]:
    result = gmail_connector.fetch_unseen(limit=limit)
    if not result.success:
        raise RuntimeError(result.error_message or "Gmail inbound sync failed")

    created = 0
    skipped = 0
    auto_replies_sent = 0
    existing_external_ids = {
        message.external_message_id
        for message in repo.conversation_messages.values()
        if message.external_message_id
    }
    for inbound in (result.payload or {}).get("messages", []):
        if inbound.external_id in existing_external_ids:
            skipped += 1
            continue
        matches = _match_email_contacts(repo, inbound.from_address)
        header_match = _match_reply_headers(repo, inbound)
        if header_match is not None:
            matches = [header_match[1]]
        if not matches:
            skipped += 1
            continue
        for contact in matches:
            if header_match is not None:
                product = header_match[0]
                attempt = header_match[2]
            else:
                product = repo.get_product(contact.product_id) if contact.product_id else None
                attempt = _latest_attempt_for_contact(repo, product.id, contact.id) if product is not None else None
            if product is None:
                skipped += 1
                continue
            if attempt is None:
                skipped += 1
                continue
            message = ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=ContactType.EMAIL,
                subject=inbound.subject,
                body=inbound.body,
                from_address=inbound.from_address,
                to_address=inbound.to_address,
                external_message_id=inbound.external_id,
                provider_timestamp=getattr(inbound, "provider_timestamp", None),
            )
            repo.add_conversation_message(message)
            _apply_supplier_reply_analysis(repo, runtime, product, message)
            existing_external_ids.add(inbound.external_id)
            if attempt.status == ContactAttemptStatus.SENT:
                attempt.transition_to(ContactAttemptStatus.RESPONDED)
            created += 1
            if runtime is None:
                message.mark_requires_user_approval("Supplier question requires user approval before continuing")
            else:
                if _send_auto_agent_reply(repo, runtime, product, contact):
                    auto_replies_sent += 1
    return {"messagesCreated": created, "messagesSkipped": skipped, "autoRepliesSent": auto_replies_sent}


def _apply_supplier_reply_analysis(
    repo: InMemoryRepository,
    runtime: AgentRuntime | None,
    product: Product,
    message: ConversationMessage,
) -> None:
    analysis = analyze_supplier_reply(runtime.model_provider if runtime else None, product, message)
    product.attributes["supplierReplyAnalysis"] = analysis
    product.attributes["supplierReplySummary"] = analysis.get("summary", "")
    product.attributes["supplierReplyNextStep"] = analysis.get("nextStep", "")
    product.attributes["communicationScore"] = analysis.get("communicationScore", "45")
    for product_field, analysis_key in (
        ("price", "price"),
        ("currency", "currency"),
        ("supplierMoq", "moq"),
        ("supplierLeadTime", "leadTime"),
        ("supplierAvailability", "availability"),
        ("supplierPaymentTerms", "paymentTerms"),
        ("supplierDeliveryTerms", "deliveryTerms"),
        ("supplierRiskFlags", "riskFlags"),
    ):
        value = str(analysis.get(analysis_key) or "").strip()
        if value:
            product.attributes[product_field] = value


def run_gmail_inbound_sync_loop(
    repo: InMemoryRepository,
    runtime: AgentRuntime,
    gmail_connector,
    limit: int,
    poll_interval_seconds: float,
    max_ticks: int | None = None,
    stop_event: threading.Event | None = None,
) -> int:
    ticks = 0
    while max_ticks is None or ticks < max_ticks:
        if stop_event is not None and stop_event.is_set():
            break
        ticks += 1
        try:
            sync_gmail_inbound_messages(
                repo,
                gmail_connector,
                limit=limit,
                runtime=runtime,
                require_ai_reply_approval=False,
            )
        except Exception:
            # The next tick should keep running even if IMAP, model, or SMTP is temporarily unavailable.
            pass
        if poll_interval_seconds > 0:
            if stop_event is not None and stop_event.wait(poll_interval_seconds):
                break
            if stop_event is None:
                time.sleep(poll_interval_seconds)
    return ticks


def _match_email_contacts(repo: InMemoryRepository, from_address: str):
    email = _normalize_email_address(from_address)
    return [
        contact
        for contact in repo.supplier_contacts.values()
        if contact.contact_type == ContactType.EMAIL and contact.contact_value.lower() == email
    ]


def _latest_attempt_for_contact(repo: InMemoryRepository, product_id, contact_id):
    attempts = [
        attempt
        for attempt in repo.list_attempts_for_product(product_id)
        if attempt.supplier_contact_id == contact_id
    ]
    if not attempts:
        return None
    return sorted(attempts, key=lambda attempt: attempt.created_at)[-1]


def _match_reply_headers(repo: InMemoryRepository, inbound):
    header_text = f"{getattr(inbound, 'in_reply_to', '')} {getattr(inbound, 'references', '')}"
    if not header_text.strip():
        return None
    for message in repo.conversation_messages.values():
        if not message.external_message_id or message.external_message_id not in header_text:
            continue
        product = repo.get_product(message.product_id)
        contact = repo.supplier_contacts.get(message.supplier_contact_id)
        attempt = repo.contact_attempts.get(message.contact_attempt_id)
        if product is not None and contact is not None and attempt is not None:
            return product, contact, attempt
    return None


def _normalize_email_address(value: str) -> str:
    return (parseaddr(value)[1] or value).strip().lower()


def _send_auto_agent_reply(
    repo: InMemoryRepository,
    runtime: AgentRuntime,
    product,
    contact,
) -> bool:
    try:
        connector = runtime.tool_registry.require("email")
    except KeyError:
        return False
    attempt = repo.add_contact_attempt(ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending"))
    attempt.transition_to(ContactAttemptStatus.RUNNING)
    conversation_message = None
    try:
        message_text = generate_supplier_reply(
            runtime.model_provider,
            product,
            repo.list_conversation_messages_for_product(product.id),
            language="ru",
            style="formal",
        )
        policy_errors = SafeMessagePolicy.validate_follow_up(message_text)
        if policy_errors:
            raise RuntimeError("; ".join(policy_errors))
        subject = f"Re: Product request: {product.title}"
        attempt.message_text = message_text
        conversation_message = ConversationMessage.create_outbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=attempt.id,
            channel=ContactType.EMAIL,
            subject=subject,
            body=message_text,
            from_address=getattr(connector, "from_address", None),
            to_address=contact.contact_value,
        )
        result: ConnectorResult = connector.send(contact.contact_value, subject, message_text)
        if not result.success:
            raise RuntimeError(result.error_message or "auto reply failed")
        conversation_message.mark_sent(result.external_id, provider_timestamp=_connector_provider_timestamp(result))
        repo.add_conversation_message(conversation_message)
        attempt.transition_to(ContactAttemptStatus.SENT)
        attempt.external_message_id = result.external_id
        return True
    except Exception as exc:
        message = _redact_connector_error(str(exc), connector)
        if conversation_message is not None and conversation_message.id not in repo.conversation_messages:
            conversation_message.mark_failed(message)
            repo.add_conversation_message(conversation_message)
        attempt.error_message = message
        if attempt.status == ContactAttemptStatus.QUEUED:
            attempt.transition_to(ContactAttemptStatus.RUNNING)
        if attempt.status == ContactAttemptStatus.RUNNING:
            attempt.transition_to(ContactAttemptStatus.FAILED)
        return False


def _connector_provider_timestamp(result: ConnectorResult):
    payload = result.payload or {}
    raw = payload.get("providerTimestamp")
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.strip())
        except ValueError:
            return None
    return None
