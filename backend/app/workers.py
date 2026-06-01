from __future__ import annotations

from datetime import datetime
import os
import re
import threading
import time
from uuid import UUID
from email.utils import parseaddr
from urllib.parse import urlparse

from .agent import (
    AgentProductOutput,
    AgentRuntime,
    ConnectorResult,
    SafeMessagePolicy,
    analyze_supplier_reply,
    generate_contract_draft,
    generate_supplier_message,
    generate_supplier_reply,
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
    validate_product_payload,
)
from .repositories import InMemoryRepository
from .sourcing import ProductFitEvaluator, ProductNormalizer, SourcingSearchOutputSchema


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
        _fail_task_only(repo, task, f"search request not found: {request_id}")
        return

    try:
        task.transition_to(AgentTaskStatus.RUNNING)
        request.transition_to(SearchRequestStatus.RUNNING)
        _persist_agent_task(repo, task)
        _persist_search_request(repo, request)

        max_results = _task_max_results(task.input_payload)
        payload_products: list[dict] = []
        search_context: dict = _empty_search_context(request)
        connector_errors: list[dict[str, str]] = []
        browser_succeeded = False

        made_in_china = runtime.tool_registry.tools.get("made_in_china")
        provider_router = runtime.tool_registry.tools.get("search_provider_router")
        if provider_router is not None:
            try:
                provider_result = provider_router.search(request.query_text, max_results=max_results)
                if provider_result.success:
                    provider_context = {
                        "normalizedIntent": provider_result.normalized_intent,
                        "commonFilters": provider_result.common_filters,
                        "productAttributes": provider_result.product_attributes,
                        "sourcingGuidance": provider_result.sourcing_guidance,
                    }
                    search_context = _merge_search_context(search_context, provider_context)
                    normalized_products = []
                    normalizer = ProductNormalizer()
                    evaluator = ProductFitEvaluator()
                    intent = search_context.get("normalizedIntent") or {}
                    for candidate in provider_result.candidates:
                        normalized = normalizer.normalize(candidate)
                        normalized.update(evaluator.evaluate(intent, normalized))
                        raw_provenance = normalized.pop("rawProvenance", {})
                        attributes = normalized.setdefault("attributes", {})
                        attributes["provider"] = provider_result.provider
                        if raw_provenance:
                            normalized["rawAgentPayload"] = {"provenance": raw_provenance}
                        normalized_products.append(normalized)
                    payload_products.extend(normalized_products)
                else:
                    connector_errors.append({"source": "search_provider_router", "error": provider_result.error_message or "provider router returned no products"})
            except Exception as exc:
                connector_errors.append({"source": "search_provider_router", "error": str(exc)})
        if made_in_china is not None:
            try:
                try:
                    made_result = made_in_china.research(request.query_text, max_results=max_results)
                except TypeError:
                    made_result = made_in_china.research(request.query_text)
                if made_result.success:
                    made_context, made_products = _extract_search_context_and_products(made_result.payload or {}, request)
                    search_context = _merge_search_context(search_context, made_context)
                    payload_products.extend(made_products)
                else:
                    connector_errors.append(
                        {"source": "made_in_china", "error": made_result.error_message or "Made-in-China discovery failed"}
                    )
            except Exception as exc:
                connector_errors.append({"source": "made_in_china", "error": str(exc)})

        browser = runtime.tool_registry.require("browser_mcp")
        if not payload_products:
            try:
                try:
                    connector_result = browser.research(request.query_text, max_results=max_results)
                except TypeError:
                    connector_result = browser.research(request.query_text)
                if connector_result.success:
                    browser_succeeded = True
                    browser_context, browser_products = _extract_search_context_and_products(connector_result.payload or {}, request)
                    search_context = _merge_search_context(search_context, browser_context)
                    payload_products.extend(browser_products)
                else:
                    connector_errors.append(
                        {"source": "browser_mcp", "error": connector_result.error_message or "browser research failed"}
                    )
            except Exception as exc:
                connector_errors.append({"source": "browser_mcp", "error": str(exc)})

        if not browser_succeeded and not payload_products:
            error = "; ".join(item["error"] for item in connector_errors) or "browser research failed"
            raise RuntimeError(error)

        output = _validate_product_search_payloads(payload_products, allow_products_without_contacts)
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
        demo_created = False if _demo_injection_disabled() or created_count > 0 else _ensure_demo_product(repo, request.id, existing_urls)

        _apply_search_context(request, search_context, repo.list_products_for_request(request.id))

        skipped = output.skipped + duplicate_errors + limit_errors
        task.output_payload = {
            "productsCreated": created_count,
            "demoProductsCreated": 1 if demo_created else 0,
            "productsSkipped": len(skipped),
            "errors": skipped,
        }
        if connector_errors:
            task.output_payload["connectorErrors"] = connector_errors
        task.transition_to(AgentTaskStatus.COMPLETED)
        request.transition_to(SearchRequestStatus.COMPLETED)
        _persist_agent_task(repo, task)
        _persist_search_request(repo, request)
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
        _persist_agent_task(repo, task)
        _persist_search_request(repo, request)


def _fail_task_only(repo: InMemoryRepository, task, message: str) -> None:
    task.error_message = message
    if task.status == AgentTaskStatus.QUEUED:
        task.transition_to(AgentTaskStatus.RUNNING)
    if task.status == AgentTaskStatus.RUNNING:
        task.transition_to(AgentTaskStatus.FAILED)
    _persist_agent_task(repo, task)


def _persist_agent_task(repo: InMemoryRepository, task) -> None:
    repo.add_agent_task(task)


def _persist_search_request(repo: InMemoryRepository, request) -> None:
    repo.add_search_request(request)


def _persist_contact_attempt(repo: InMemoryRepository, attempt) -> None:
    repo.add_contact_attempt(attempt)


def _persist_contract_draft(repo: InMemoryRepository, draft) -> None:
    repo.contracts.add_contract_draft(draft)


def _task_max_results(payload: dict) -> int:
    try:
        value = int(payload.get("maxResults", 5))
    except (TypeError, ValueError):
        return 5
    return max(1, min(value, 50))


def _validate_product_search_payloads(
    payload_products: list[dict],
    allow_products_without_contacts: bool,
) -> AgentProductOutput:
    products: list[Product] = []
    skipped: list[dict] = []
    for index, item in enumerate(payload_products):
        allow_contactless = allow_products_without_contacts or _is_made_in_china_product_payload(item)
        result = validate_product_payload(item, allow_without_contacts=allow_contactless)
        if result.product is None:
            skipped.append({"index": index, "errors": result.errors, "raw": item})
            continue
        products.append(result.product)
    return AgentProductOutput(products=products, skipped=skipped)


def _empty_search_context(request) -> dict:
    return {
        "normalizedIntent": {
            "rawQuery": request.query_text,
            **({"targetMarket": request.target_market} if getattr(request, "target_market", None) else {}),
            **({"quantity": request.quantity} if getattr(request, "quantity", None) else {}),
            **({"budget": request.budget} if getattr(request, "budget", None) else {}),
            **({"certifications": request.certifications} if getattr(request, "certifications", None) else {}),
            **({"supplierPreference": request.supplier_preference} if getattr(request, "supplier_preference", None) else {}),
        },
        "missingFields": [],
        "clarifyingQuestions": [],
        "commonFilters": [],
        "productAttributes": [],
        "sourcingGuidance": {},
    }


def _extract_search_context_and_products(payload: dict, request) -> tuple[dict, list[dict]]:
    try:
        parsed = SourcingSearchOutputSchema.from_agent_payload(payload)
    except Exception:
        return _empty_search_context(request), list(payload.get("products") or [])
    context = {
        "normalizedIntent": parsed.normalized_intent.model_dump(by_alias=True, exclude_none=True),
        "missingFields": parsed.missing_fields,
        "clarifyingQuestions": parsed.clarifying_questions,
        "commonFilters": parsed.common_filters,
        "productAttributes": [item.model_dump(by_alias=True) for item in parsed.product_attributes],
        "sourcingGuidance": parsed.sourcing_guidance.model_dump(by_alias=True, exclude_defaults=True),
    }
    products = [item.model_dump(by_alias=True, exclude_none=True) for item in parsed.products]
    return context, products


def _merge_search_context(current: dict, incoming: dict) -> dict:
    merged = dict(current)
    if incoming.get("normalizedIntent"):
        merged["normalizedIntent"] = {**(merged.get("normalizedIntent") or {}), **incoming["normalizedIntent"]}
    for key in ("missingFields", "clarifyingQuestions", "commonFilters", "productAttributes"):
        values = merged.setdefault(key, [])
        for item in incoming.get(key) or []:
            if item not in values:
                values.append(item)
    if incoming.get("sourcingGuidance"):
        merged["sourcingGuidance"] = {**(merged.get("sourcingGuidance") or {}), **incoming["sourcingGuidance"]}
    return merged


def _apply_search_context(request, context: dict, products: list[Product]) -> None:
    request.normalized_intent = dict(context.get("normalizedIntent") or {})
    request.missing_fields = [str(value) for value in context.get("missingFields") or []]
    request.clarifying_questions = [str(value) for value in context.get("clarifyingQuestions") or []]
    request.common_filters = [str(value) for value in context.get("commonFilters") or []] or _derive_common_filters(products)
    request.product_attributes = list(context.get("productAttributes") or []) or _derive_product_attribute_facets(products)
    request.sourcing_guidance = dict(context.get("sourcingGuidance") or {})
    supplier_keys = {_supplier_dedupe_key(product) for product in products if product.attributes.get("demo") != "true"}
    request.suppliers_count = len({key for key in supplier_keys if key})


def _derive_common_filters(products: list[Product]) -> list[str]:
    filters = []
    if any(product.price is not None or product.price_range or product.attributes.get("madeInChinaPriceText") for product in products):
        filters.append("Price range")
    if any(product.supports_customization or _product_has_text(product, "custom") for product in products):
        filters.append("Customization Available")
    if any(product.sample_available or _product_has_text(product, "sample available") for product in products):
        filters.append("Sample Available")
    if any(_product_has_text(product, "manufacturer") or _product_has_text(product, "factory") for product in products):
        filters.append("Manufacturer First")
    return filters


def _derive_product_attribute_facets(products: list[Product]) -> list[dict]:
    preferred = [
        ("interface", "Interface"),
        ("sensorType", "Sensor Type"),
        ("sensorSize", "Sensor Type"),
        ("resolution", "Resolution"),
        ("frameRate", "Frame Rate"),
        ("magapixel", "Resolution"),
        ("megapixel", "Resolution"),
        ("origin", "Origin"),
        ("protectionRating", "Protection Rating"),
        ("cooling", "Cooling"),
    ]
    values_by_name: dict[str, list[str]] = {}
    for product in products:
        if product.attributes.get("demo") == "true":
            continue
        for key, label in preferred:
            value = product.attributes.get(key)
            if isinstance(value, str) and value.strip():
                values_by_name.setdefault(label, [])
                if value.strip() not in values_by_name[label]:
                    values_by_name[label].append(value.strip())
        title = product.title.lower()
        if "usb 3.0" in title or "usb3" in title or "usb 3" in title:
            values_by_name.setdefault("Interface", [])
            if "USB 3.0" not in values_by_name["Interface"]:
                values_by_name["Interface"].append("USB 3.0")
    return [{"name": name, "values": values[:12]} for name, values in values_by_name.items() if values]


def _product_has_text(product: Product, needle: str) -> bool:
    text = " ".join(
        [
            product.title,
            product.description or "",
            product.supplier_name or "",
            " ".join(product.supplier_badges),
            " ".join(str(value) for value in product.attributes.values()),
        ]
    ).lower()
    return needle.lower() in text


def _demo_injection_disabled() -> bool:
    return os.getenv("DISABLE_DEMO_PRODUCT_INJECTION", "").lower() in {"1", "true", "yes", "on"} or os.getenv("APP_ENV", "").lower() in {"e2e", "production"}


def _is_made_in_china_product_payload(payload: dict) -> bool:
    attributes = payload.get("attributes") if isinstance(payload.get("attributes"), dict) else {}
    source_platform = str(attributes.get("sourcePlatform") or "").strip().lower()
    product_url = str(payload.get("productUrl") or payload.get("product_url") or "")
    supplier_url = str(attributes.get("supplierUrl") or "")
    inquiry_url = str(attributes.get("inquiryUrl") or "")
    urls = " ".join([product_url, supplier_url, inquiry_url]).lower()
    has_made_in_china_source = source_platform == "made-in-china" or "made-in-china.com" in urls
    has_supplier_path = bool(supplier_url or inquiry_url or product_url)
    return has_made_in_china_source and has_supplier_path


def _supplier_dedupe_key(product: Product) -> str:
    if product.attributes.get("demo") == "true":
        return f"demo:{product.product_url}"
    if product.attributes.get("sourcePlatform") == "made-in-china":
        # Made-in-China search can expose several products from the same supplier,
        # and some public detail pages expose generic VR/inquiry helper URLs as
        # supplier links. Product URL dedupe is enough for this source.
        return f"made-in-china-product:{product.product_url}"
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
        _fail_task_only(repo, task, "product not found")
        return
    if contact is None:
        _fail_task_only(repo, task, "supplier contact not found")
        return
    if attempt is None:
        _fail_task_only(repo, task, "contact attempt not found")
        return

    conversation_message: ConversationMessage | None = None
    connector = None

    try:
        task.transition_to(AgentTaskStatus.RUNNING)
        attempt.transition_to(ContactAttemptStatus.RUNNING)
        _persist_agent_task(repo, task)
        _persist_contact_attempt(repo, attempt)

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
        _persist_agent_task(repo, task)
        _persist_contact_attempt(repo, attempt)
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
        _persist_agent_task(repo, task)
        _persist_contact_attempt(repo, attempt)


def process_contract_draft(repo: InMemoryRepository, runtime: AgentRuntime, task_id: UUID) -> None:
    task = repo.get_agent_task(task_id)
    if task is None:
        raise ValueError(f"agent task not found: {task_id}")
    draft = repo.contracts.get_contract_draft(UUID(task.input_payload["contractDraftId"]))
    if draft is None:
        _fail_task_only(repo, task, "contract draft not found")
        return
    product = repo.get_product(draft.product_id)
    if product is None:
        draft.mark_failed("product not found")
        _persist_contract_draft(repo, draft)
        _fail_task_only(repo, task, "product not found")
        return
    try:
        task.transition_to(AgentTaskStatus.RUNNING)
        draft.transition_to(ContractDraftStatus.RUNNING)
        _persist_agent_task(repo, task)
        _persist_contract_draft(repo, draft)
        output = generate_contract_draft(
            runtime.model_provider,
            product,
            repo.list_conversation_messages_for_product(product.id),
        )
        draft.mark_ready(output["draftText"], output["extractedData"], title=output["title"])
        task.output_payload = {"contractDraftId": str(draft.id), "status": draft.status.value}
        task.transition_to(AgentTaskStatus.COMPLETED)
        _persist_agent_task(repo, task)
        _persist_contract_draft(repo, draft)
    except Exception as exc:
        message = str(exc)
        draft.mark_failed(message)
        task.error_message = message
        if task.status == AgentTaskStatus.QUEUED:
            task.transition_to(AgentTaskStatus.RUNNING)
        if task.status == AgentTaskStatus.RUNNING:
            task.transition_to(AgentTaskStatus.FAILED)
        _persist_agent_task(repo, task)
        _persist_contract_draft(repo, draft)


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
    _persist_contact_attempt(repo, attempt)
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
        _persist_contact_attempt(repo, attempt)
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
        _persist_contact_attempt(repo, attempt)
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
