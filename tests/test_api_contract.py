import time
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from backend.app.agent import AgentRuntime, ConnectorResult, ToolRegistry
from backend.app.domain import (
    ContactAttempt,
    ContactAttemptStatus,
    ContactType,
    ContractDraft,
    ConversationDirection,
    ConversationMessage,
    Product,
    SearchRequest,
    SupplierContact,
)
from backend.app.main import create_app
from backend.app.repositories import InMemoryRepository
from tests.asgi_client import request_json
from backend.app.connectors import InboundEmailMessage


def valid_initial_message(
    product_title="E2E UAV Flight Controller FC-100",
    product_url="https://supplier.test/products/fc-100",
):
    return (
        "Hello. I represent the purchasing department of AlphaLogisticService LLC.\n"
        f"Product: {product_title}\n"
        f"Product link: {product_url}\n"
        "Please share the current price, availability, MOQ/minimum order quantity, "
        "lead time, payment terms, and delivery/shipping terms."
    )


class FakeModelProvider:
    name = "local-demo-model"

    def complete(self, prompt: str, tools=None):
        if "Conversation history:" in prompt:
            return {
                "reply": (
                    "Hello. I represent the purchasing department of AlphaLogisticService LLC. "
                    "Thank you for the supplier update. Please share any remaining details needed to prepare the offer for the referenced product."
                )
            }
        return {"reply": valid_initial_message()}


class SupplierAnalysisModelProvider(FakeModelProvider):
    def complete(self, prompt: str, tools=None):
        if "Analyze the latest supplier reply" in prompt:
            return {
                "summary": "Supplier confirmed stock and commercial terms.",
                "price": "120",
                "currency": "USD",
                "moq": "10",
                "leadTime": "5 days",
                "availability": "in stock",
                "paymentTerms": "bank transfer",
                "deliveryTerms": "EXW",
                "nextStep": "compare offer",
                "communicationScore": "88",
            }
        return super().complete(prompt, tools)


class InternalAssistantModelProvider(FakeModelProvider):
    def complete(self, prompt: str, tools=None):
        if "internal AI assistant" in prompt:
            return "Ask the supplier for missing MOQ and delivery terms before comparing offers."
        return super().complete(prompt, tools)


class JsonInternalAssistantModelProvider(FakeModelProvider):
    def complete(self, prompt: str, tools=None):
        if "internal AI assistant" in prompt:
            return {
                "riskLevel": "Low",
                "reasons": [
                    "Supplier is a demo supplier, no real transaction history available.",
                    "No price information provided for assessment.",
                ],
                "nextSteps": [
                    "Request detailed pricing and terms from the supplier.",
                    "Verify supplier reliability through additional communication.",
                ],
            }
        return super().complete(prompt, tools)


class ContractDraftModelProvider(FakeModelProvider):
    def complete(self, prompt: str, tools=None):
        if "contract draft" in prompt.lower():
            return {
                "title": "Draft contract for FC-100 supply",
                "extractedData": {
                    "product": "E2E UAV Flight Controller FC-100",
                    "price": "120 USD",
                    "moq": "10",
                    "deliveryTerms": "EXW",
                    "paymentTerms": "bank transfer after invoice",
                    "missingFields": ["legal signatory", "delivery address"],
                },
                "draftText": (
                    "DRAFT CONTRACT - NOT SIGNED AND NOT BINDING\n"
                    "Supplier: Supplier Test\n"
                    "Product: E2E UAV Flight Controller FC-100\n"
                    "Commercial terms are taken from supplier correspondence for review only."
                ),
            }
        return super().complete(prompt, tools)


class FailingContractDraftModelProvider(FakeModelProvider):
    def complete(self, prompt: str, tools=None):
        if "contract draft" in prompt.lower():
            raise RuntimeError("HTTP Error 404: Not Found")
        return super().complete(prompt, tools)


class BrowserConnector:
    def __init__(self):
        self.queries = []

    def research(self, query_text: str):
        self.queries.append(query_text)
        return ConnectorResult(
            success=True,
            payload={
                "products": [
                    {
                        "title": "E2E UAV Flight Controller FC-100",
                        "productUrl": "https://supplier.test/products/fc-100",
                        "price": "120.00",
                        "currency": "USD",
                        "contacts": [{"type": "email", "value": "supplier@example.test"}],
                    }
                ]
            },
        )


class EmailConnector:
    from_address = "agent@example.test"
    password = ""

    def __init__(self):
        self.calls = []

    def send(self, destination: str, subject: str, body: str):
        self.calls.append((destination, subject, body))
        return ConnectorResult(success=True, external_id="gmail-live-1")


class GmailInboundConnector:
    def __init__(self):
        self.calls = []

    def fetch_unseen(self, limit=20):
        self.calls.append(limit)
        return ConnectorResult(
            success=True,
            payload={
                "messages": [
                    InboundEmailMessage(
                        external_id="<gmail-inbound-1@example.test>",
                        subject="Re: Product request",
                        body="We have stock. MOQ is 10 units.",
                        from_address="supplier@example.test",
                        to_address="agent@example.test",
                    )
                ]
            },
        )


def runtime_with_browser(browser):
    registry = ToolRegistry()
    registry.register("browser_mcp", browser)
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


def runtime_with_email(email):
    registry = ToolRegistry()
    registry.register("email", email)
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


def runtime_with_gmail_inbound(connector):
    registry = ToolRegistry()
    registry.register("gmail_inbound", connector)
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


def runtime_with_gmail_inbound_and_email(connector, email):
    registry = ToolRegistry()
    registry.register("gmail_inbound", connector)
    registry.register("email", email)
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


def runtime_with_model(model):
    registry = ToolRegistry()
    return AgentRuntime(model_provider=model, tool_registry=registry)


class ReplyModelProvider:
    name = "reply-model"

    def complete(self, prompt: str, tools=None):
        return (
            "Hello. Thank you for the stock and MOQ update. Please share the unit price and whether the proposed delivery timing is still available for this product."
        )


class ApiContractTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()
        self.app = create_app(self.repo)

    def test_post_search_requests_creates_request_and_agent_task(self):
        started = time.perf_counter()
        status, body = request_json(
            self.app,
            "POST",
            "/api/search-requests",
            {"queryText": "E2E UAV Flight Controller FC-100"},
        )
        elapsed_ms = (time.perf_counter() - started) * 1000

        self.assertLess(elapsed_ms, 500)
        self.assertEqual(201, status)
        self.assertEqual("queued", body["status"])
        self.assertEqual("E2E UAV Flight Controller FC-100", body["queryText"])
        self.assertEqual(5, body["maxResults"])
        self.assertIsNotNone(body["agentTaskId"])
        self.assertEqual(1, len(self.repo.search_requests))
        self.assertEqual(1, len(self.repo.agent_tasks))

    def test_post_search_requests_accepts_max_results(self):
        status, body = request_json(
            self.app,
            "POST",
            "/api/search-requests",
            {"queryText": "E2E UAV Flight Controller FC-100", "maxResults": 7},
        )

        self.assertEqual(201, status)
        self.assertEqual(7, body["maxResults"])
        request = next(iter(self.repo.search_requests.values()))
        task = next(iter(self.repo.agent_tasks.values()))
        self.assertEqual(7, request.max_results)
        self.assertEqual(7, task.input_payload["maxResults"])

    def test_post_search_requests_can_auto_process_local_demo_task(self):
        browser = BrowserConnector()
        with patch.dict("os.environ", {"AUTO_PROCESS_SEARCH_TASKS": "true"}, clear=False):
            app = create_app(self.repo, runtime=runtime_with_browser(browser))

        status, body = request_json(
            app,
            "POST",
            "/api/search-requests",
            {"queryText": "E2E UAV Flight Controller FC-100"},
        )

        self.assertEqual(201, status)
        self.assertEqual("queued", body["status"])
        self.assertEqual(["E2E UAV Flight Controller FC-100"], browser.queries)
        request = next(iter(self.repo.search_requests.values()))
        task = next(iter(self.repo.agent_tasks.values()))
        self.assertEqual("completed", request.status.value)
        self.assertEqual("completed", task.status.value)
        self.assertEqual(2, len(self.repo.products))

    def test_post_search_requests_validates_query(self):
        invalid_payloads = [
            {"queryText": ""},
            {"queryText": "ab"},
            {"queryText": "x" * 1001},
            {"queryText": "E2E UAV Flight Controller FC-100", "maxResults": 0},
            {"queryText": "E2E UAV Flight Controller FC-100", "maxResults": 51},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                status, body = request_json(self.app, "POST", "/api/search-requests", payload)
                self.assertEqual(422, status)
                self.assertIn("detail", body)

    def test_get_search_requests_and_detail(self):
        status, created = request_json(
            self.app,
            "POST",
            "/api/search-requests",
            {"queryText": "E2E Industrial CNC Controller IC-200"},
        )
        self.assertEqual(201, status)
        self.assertEqual(5, created["maxResults"])

        status, listing = request_json(self.app, "GET", "/api/search-requests")
        self.assertEqual(200, status)
        self.assertEqual(1, len(listing["items"]))
        self.assertEqual(0, listing["items"][0]["productsCount"])
        self.assertEqual(5, listing["items"][0]["maxResults"])

        status, detail = request_json(self.app, "GET", f"/api/search-requests/{created['id']}")
        self.assertEqual(200, status)
        self.assertEqual(created["id"], detail["id"])
        self.assertEqual(5, detail["maxResults"])

    def test_cors_preflight_allows_webui_origin(self):
        status, body = request_json(
            self.app,
            "OPTIONS",
            "/api/search-requests",
            headers={
                "origin": "http://localhost:5173",
                "access-control-request-method": "POST",
            },
        )

        self.assertEqual(200, status)
        self.assertEqual("OK", body)

    def test_cors_preflight_allows_docker_host_webui_origin(self):
        status, body = request_json(
            self.app,
            "OPTIONS",
            "/api/search-requests",
            headers={
                "origin": "http://host.docker.internal:5173",
                "access-control-request-method": "GET",
            },
        )

        self.assertEqual(200, status)
        self.assertEqual("OK", body)

    def test_get_request_products_and_product_detail(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E Rack Workstation RW-500"))
        request.started_at = datetime(2026, 5, 2, 15, 0, 0, tzinfo=timezone.utc)
        request.completed_at = request.started_at + timedelta(seconds=42)
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E Rack Workstation RW-500",
            product_url="https://supplier.test/products/rw-500",
            price=None,
            currency=None,
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending")
        )
        message = ConversationMessage.create_outbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=attempt.id,
            channel=ContactType.EMAIL,
            subject="Запрос по товару: E2E Rack Workstation RW-500",
            body="Здравствуйте, уточните условия поставки.",
            from_address="agent@example.test",
            to_address="supplier@example.test",
        )
        message.mark_sent("gmail-message-id", provider_timestamp=datetime(2026, 5, 2, 15, 1, 2, tzinfo=timezone.utc))
        self.repo.add_conversation_message(message)

        status, request_body = request_json(self.app, "GET", f"/api/search-requests/{request.id}")
        self.assertEqual(200, status)
        self.assertEqual(42, request_body["durationSeconds"])

        status, products = request_json(self.app, "GET", f"/api/search-requests/{request.id}/products")
        self.assertEqual(200, status)
        self.assertEqual(1, len(products["items"]))
        self.assertIsNone(products["items"][0]["price"])
        self.assertEqual("supplier@example.test", products["items"][0]["contacts"][0]["contactValue"])

        status, detail = request_json(self.app, "GET", f"/api/products/{product.id}")
        self.assertEqual(200, status)
        self.assertEqual("E2E Rack Workstation RW-500", detail["title"])
        self.assertEqual("supplier@example.test", detail["contacts"][0]["contactValue"])
        self.assertEqual(1, len(detail["conversationMessages"]))
        self.assertEqual("sent", detail["conversationMessages"][0]["status"])
        self.assertEqual("outbound", detail["conversationMessages"][0]["direction"])
        self.assertEqual("gmail-message-id", detail["conversationMessages"][0]["externalMessageId"])
        self.assertEqual("2026-05-02T15:01:02+00:00", detail["conversationMessages"][0]["providerTimestamp"])
        self.assertEqual("Здравствуйте, уточните условия поставки.", detail["conversationMessages"][0]["body"])

    def test_products_include_supplier_comparison_rating(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier comparison"))
        email = SupplierContact.create(ContactType.EMAIL, "best@example.test")
        best = Product(
            search_request_id=request.id,
            title="Best priced controller",
            product_url="https://supplier.test/products/best",
            price="100.00",
            currency="USD",
            contacts=[email],
            supplier_name="Best Supplier",
            description="In stock controller with documented shipping terms.",
            images=["https://supplier.test/images/best.jpg"],
        )
        email.product_id = best.id
        self.repo.add_product(best)

        telegram = SupplierContact.create(ContactType.TELEGRAM, "@second_supplier")
        second = Product(
            search_request_id=request.id,
            title="Higher priced controller",
            product_url="https://supplier.test/products/second",
            price="150.00",
            currency="USD",
            contacts=[telegram],
            supplier_name="Second Supplier",
        )
        telegram.product_id = second.id
        self.repo.add_product(second)

        attempt = self.repo.add_contact_attempt(ContactAttempt.create(best.id, email.id, email.contact_type, "initial"))
        attempt.transition_to(ContactAttemptStatus.RUNNING)
        attempt.transition_to(ContactAttemptStatus.SENT)
        self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=best.id,
                supplier_contact_id=email.id,
                contact_attempt_id=attempt.id,
                channel=ContactType.EMAIL,
                subject="Re: request",
                body="We can ship this week.",
                from_address="best@example.test",
                to_address="agent@example.test",
            )
        )

        status, products = request_json(self.app, "GET", f"/api/search-requests/{request.id}/products")

        self.assertEqual(200, status)
        by_title = {item["title"]: item for item in products["items"]}
        best_rating = by_title["Best priced controller"]["supplierComparison"]
        second_rating = by_title["Higher priced controller"]["supplierComparison"]
        self.assertEqual(1, best_rating["priceRank"])
        self.assertEqual(2, second_rating["priceRank"])
        self.assertEqual(0, best_rating["priceDeltaPercent"])
        self.assertGreater(second_rating["priceDeltaPercent"], 0)
        self.assertGreater(best_rating["overallRating"], second_rating["overallRating"])
        for key in [
            "priceScore",
            "contactabilityScore",
            "responseScore",
            "dataCompletenessScore",
            "sourceTraceabilityScore",
        ]:
            self.assertIn(key, best_rating["metrics"])

    def test_post_contact_supplier_creates_contact_attempt_and_task(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E UAV Flight Controller FC-100"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)

        status, body = request_json(self.app, "POST", f"/api/products/{product.id}/contact-supplier")

        self.assertEqual(201, status)
        self.assertEqual("queued", body["status"])
        self.assertEqual("email", body["channel"])
        self.assertIsNotNone(body["agentTaskId"])
        self.assertEqual(1, len(self.repo.contact_attempts))
        self.assertEqual(0, len(self.repo.conversation_messages))

        status, duplicate = request_json(self.app, "POST", f"/api/products/{product.id}/contact-supplier")
        self.assertEqual(409, status)
        self.assertIn("active contact attempt", duplicate["detail"])

    def test_post_contact_supplier_accepts_message_preferences(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E UAV Flight Controller FC-100"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)

        status, body = request_json(
            self.app,
            "POST",
            f"/api/products/{product.id}/contact-supplier",
            {"language": "en", "style": "concise"},
        )

        self.assertEqual(201, status)
        self.assertEqual("pending", body["messageText"])
        task = self.repo.get_agent_task(next(reversed(self.repo.agent_tasks)))
        self.assertEqual("en", task.input_payload["language"])
        self.assertEqual("concise", task.input_payload["style"])

    def test_post_contact_supplier_can_schedule_background_send(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E UAV Flight Controller FC-100"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        email = EmailConnector()
        with patch.dict("os.environ", {"AUTO_PROCESS_SUPPLIER_CONTACT_TASKS": "true"}, clear=False):
            app = create_app(self.repo, runtime=runtime_with_email(email))

        status, body = request_json(app, "POST", f"/api/products/{product.id}/contact-supplier")

        self.assertEqual(201, status)
        self.assertEqual("queued", body["status"])
        self.assertEqual(1, len(email.calls))
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(1, len(messages))
        self.assertEqual("sent", messages[0].status.value)
        self.assertIn(product.title, messages[0].body)
        updated_attempt = next(iter(self.repo.contact_attempts.values()))
        self.assertEqual(ContactAttemptStatus.SENT, updated_attempt.status)

    def test_post_contact_supplier_requires_contact(self):
        request = self.repo.add_search_request(SearchRequest.create("No contact product"))
        product = Product(
            search_request_id=request.id,
            title="No Contact Product",
            product_url="https://supplier.test/products/no-contact",
            contacts=[],
        )
        self.repo.add_product(product)

        status, body = request_json(self.app, "POST", f"/api/products/{product.id}/contact-supplier")

        self.assertEqual(409, status)
        self.assertIn("no supplier contact", body["detail"])

    def test_post_conversation_inbound_message_records_supplier_reply(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier dialogue"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "initial")
        )

        status, body = request_json(
            self.app,
            "POST",
            f"/api/products/{product.id}/conversation-messages",
            {
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(attempt.id),
                "channel": "email",
                "subject": "Re: request",
                "body": "We have stock. MOQ is 10.",
                "fromAddress": "supplier@example.test",
                "toAddress": "agent@example.test",
                "externalMessageId": "gmail-inbound-1",
            },
        )

        self.assertEqual(201, status)
        self.assertEqual("inbound", body["direction"])
        self.assertEqual("received", body["status"])
        self.assertEqual("We have stock. MOQ is 10.", body["body"])
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(1, len(messages))
        self.assertEqual(ConversationDirection.INBOUND, messages[0].direction)

    def test_post_conversation_inbound_message_saves_ai_supplier_analysis(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier dialogue"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "initial")
        )
        app = create_app(self.repo, runtime=runtime_with_model(SupplierAnalysisModelProvider()))

        status, _ = request_json(
            app,
            "POST",
            f"/api/products/{product.id}/conversation-messages",
            {
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(attempt.id),
                "channel": "email",
                "subject": "Re: request",
                "body": "Price is 120 USD. MOQ is 10. Lead time is 5 days.",
                "fromAddress": "supplier@example.test",
            },
        )

        self.assertEqual(201, status)
        self.assertEqual("88", product.attributes["communicationScore"])
        self.assertEqual("10", product.attributes["supplierMoq"])
        self.assertEqual("5 days", product.attributes["supplierLeadTime"])
        self.assertEqual("compare offer", product.attributes["supplierReplyNextStep"])

    def test_post_conversation_reply_creates_agent_reply_task(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier dialogue"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "initial")
        )
        attempt.transition_to(ContactAttemptStatus.RUNNING)
        attempt.transition_to(ContactAttemptStatus.SENT)
        inbound = self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=ContactType.EMAIL,
                subject="Re: request",
                body="We have stock. MOQ is 10.",
                from_address="supplier@example.test",
                to_address="agent@example.test",
            )
        )

        status, body = request_json(
            self.app,
            "POST",
            f"/api/products/{product.id}/conversation-reply",
            {"supplierContactId": str(contact.id), "replyToMessageId": str(inbound.id)},
        )

        self.assertEqual(201, status)
        self.assertEqual("queued", body["status"])
        self.assertEqual("email", body["channel"])
        self.assertIsNotNone(body["agentTaskId"])
        reply_task = self.repo.get_agent_task(next(reversed(self.repo.agent_tasks)))
        self.assertEqual("reply", reply_task.input_payload["conversationMode"])
        self.assertEqual(str(inbound.id), reply_task.input_payload["replyToMessageId"])

    def test_post_conversation_reply_accepts_message_preferences(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier dialogue"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)

        status, _ = request_json(
            self.app,
            "POST",
            f"/api/products/{product.id}/conversation-reply",
            {"supplierContactId": str(contact.id), "language": "zh", "style": "formal"},
        )

        self.assertEqual(201, status)
        reply_task = self.repo.get_agent_task(next(reversed(self.repo.agent_tasks)))
        self.assertEqual("zh", reply_task.input_payload["language"])
        self.assertEqual("formal", reply_task.input_payload["style"])

    def test_post_conversation_reply_can_auto_process_agent_response(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier dialogue"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "initial")
        )
        attempt.transition_to(ContactAttemptStatus.RUNNING)
        attempt.transition_to(ContactAttemptStatus.SENT)
        inbound = self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=ContactType.EMAIL,
                subject="Re: request",
                body="We have stock. MOQ is 10.",
                from_address="supplier@example.test",
                to_address="agent@example.test",
            )
        )
        email = EmailConnector()
        registry = ToolRegistry()
        registry.register("email", email)
        runtime = AgentRuntime(model_provider=ReplyModelProvider(), tool_registry=registry)
        with patch.dict("os.environ", {"AUTO_PROCESS_SUPPLIER_CONTACT_TASKS": "true"}, clear=False):
            app = create_app(self.repo, runtime=runtime)

        status, body = request_json(
            app,
            "POST",
            f"/api/products/{product.id}/conversation-reply",
            {"supplierContactId": str(contact.id), "replyToMessageId": str(inbound.id)},
        )

        self.assertEqual(201, status)
        self.assertEqual("queued", body["status"])
        reply_attempt = next(attempt for attempt in self.repo.contact_attempts.values() if attempt.id != inbound.contact_attempt_id)
        self.assertEqual(ContactAttemptStatus.SENT, reply_attempt.status)
        self.assertEqual(1, len(email.calls))
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(["inbound", "outbound"], [message.direction.value for message in messages])

    def test_post_sync_gmail_records_matching_supplier_reply(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E Gmail inbound"))
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "initial")
        )
        attempt.transition_to(ContactAttemptStatus.RUNNING)
        attempt.transition_to(ContactAttemptStatus.SENT)
        connector = GmailInboundConnector()
        email = EmailConnector()
        app = create_app(self.repo, runtime=runtime_with_gmail_inbound_and_email(connector, email))

        status, body = request_json(app, "POST", "/api/conversations/sync-gmail")

        self.assertEqual(200, status)
        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 1}, body)
        self.assertEqual(1, len(email.calls))
        self.assertEqual([20], connector.calls)
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(2, len(messages))
        self.assertEqual("received", messages[0].status.value)
        self.assertEqual("sent", messages[1].status.value)

    def test_contact_supplier_selects_best_ai_ranked_contact_by_default(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E contact quality"))
        info = SupplierContact.create(ContactType.EMAIL, "info@gmail.com")
        sales = SupplierContact.create(ContactType.EMAIL, "sales@supplier.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[info, sales],
            source_domain="supplier.test",
        )
        for contact in product.contacts:
            contact.product_id = product.id
        self.repo.add_product(product)

        status, body = request_json(self.app, "POST", f"/api/products/{product.id}/contact-supplier")

        self.assertEqual(201, status)
        attempt = next(iter(self.repo.contact_attempts.values()))
        self.assertEqual(sales.id, attempt.supplier_contact_id)
        detail_status, detail = request_json(self.app, "GET", f"/api/products/{product.id}")
        self.assertEqual(200, detail_status)
        preferred = [contact for contact in detail["contacts"] if contact["isPreferred"]]
        self.assertEqual(["sales@supplier.test"], [contact["contactValue"] for contact in preferred])
        self.assertIn("contactQualityScore", detail["supplierComparison"]["metrics"])

    def test_product_export_returns_excel_compatible_supplier_summary(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E export"))
        contact = SupplierContact.create(ContactType.EMAIL, "sales@supplier.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
            supplier_name="Supplier Test",
            attributes={
                "supplierReplyAnalysis": {
                    "summary": "Supplier confirmed stock.",
                    "price": "120",
                    "currency": "USD",
                    "moq": "10",
                    "leadTime": "5 days",
                    "nextStep": "compare offer",
                    "communicationScore": "88",
                }
            },
        )
        contact.product_id = product.id
        self.repo.add_product(product)

        status, body = request_json(self.app, "GET", f"/api/products/{product.id}/export.xlsx")

        self.assertEqual(200, status)
        self.assertIn("Product and supplier information", body)
        self.assertIn("Supplier confirmed stock", body)
        self.assertIn("sales@supplier.test", body)

    def test_product_internal_assistant_answers_without_saving_supplier_message(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E assistant"))
        contact = SupplierContact.create(ContactType.EMAIL, "sales@supplier.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
            supplier_name="Supplier Test",
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        app = create_app(self.repo, runtime=runtime_with_model(InternalAssistantModelProvider()))

        status, body = request_json(
            app,
            "POST",
            f"/api/products/{product.id}/assistant-chat",
            {"message": "Что спросить дальше?"},
        )

        self.assertEqual(200, status)
        self.assertIn("MOQ", body["reply"])
        self.assertEqual(2, len(body["messages"]))
        self.assertEqual("user", body["messages"][0]["role"])
        self.assertEqual("assistant", body["messages"][1]["role"])
        self.assertEqual(0, len(self.repo.conversation_messages))

        detail_status, detail = request_json(app, "GET", f"/api/products/{product.id}")
        self.assertEqual(200, detail_status)
        self.assertEqual(body["messages"], detail["assistantMessages"])

    def test_product_internal_assistant_humanizes_json_like_answers(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E assistant json"))
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[],
            supplier_name="Supplier Test",
        )
        self.repo.add_product(product)
        app = create_app(self.repo, runtime=runtime_with_model(JsonInternalAssistantModelProvider()))

        status, body = request_json(
            app,
            "POST",
            f"/api/products/{product.id}/assistant-chat",
            {"message": "Оцени риски"},
        )

        self.assertEqual(200, status)
        self.assertFalse(body["reply"].lstrip().startswith("{"))
        self.assertIn("Уровень риска: Low", body["reply"])
        self.assertIn("Причины:", body["reply"])
        self.assertIn("Следующие шаги:", body["reply"])


    def test_contract_draft_api_creates_lists_and_downloads_ready_draft(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E contract draft"))
        contact = SupplierContact.create(ContactType.EMAIL, "sales@supplier.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
            supplier_name="Supplier Test",
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(ContactAttempt.create(product.id, contact.id, contact.contact_type, "initial"))
        self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=ContactType.EMAIL,
                subject="Terms",
                body="Price is 120 USD. MOQ is 10. Delivery EXW. Payment by bank transfer after invoice.",
                from_address="sales@supplier.test",
                to_address="agent@example.test",
            )
        )
        app = create_app(self.repo, runtime=runtime_with_model(ContractDraftModelProvider()))

        status, created = request_json(app, "POST", f"/api/products/{product.id}/contracts")

        self.assertEqual(201, status)
        self.assertEqual("queued", created["status"])
        self.assertEqual(1, len(self.repo.contracts.contract_drafts))
        draft = next(iter(self.repo.contracts.contract_drafts.values()))
        from backend.app.workers import process_contract_draft

        process_contract_draft(self.repo, runtime_with_model(ContractDraftModelProvider()), draft.agent_task_id)

        status, listing = request_json(app, "GET", f"/api/products/{product.id}/contracts")
        self.assertEqual(200, status)
        self.assertEqual(1, len(listing["items"]))
        self.assertEqual("ready", listing["items"][0]["status"])
        self.assertIn("legal signatory", listing["items"][0]["missingFields"])

        status, detail = request_json(app, "GET", f"/api/contracts/{draft.id}")
        self.assertEqual(200, status)
        self.assertIn("DRAFT CONTRACT", detail["draftText"])

        status, download = request_json(app, "GET", f"/api/contracts/{draft.id}/download")
        self.assertEqual(200, status)
        self.assertIn("NOT SIGNED AND NOT BINDING", download)

    def test_contract_download_rejects_unfinished_draft(self):
        draft = ContractDraft.create(product_id=uuid4(), supplier_contact_id=uuid4(), supplier_name="Supplier Test")
        self.repo.contracts.add_contract_draft(draft)

        status, body = request_json(self.app, "GET", f"/api/contracts/{draft.id}/download")

        self.assertEqual(409, status)
        self.assertIn("not ready", body["detail"])

    def test_contract_draft_falls_back_and_downloads_when_model_returns_404(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E contract draft fallback"))
        contact = SupplierContact.create(ContactType.EMAIL, "sales@supplier.test")
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
            supplier_name="Supplier Test",
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(ContactAttempt.create(product.id, contact.id, contact.contact_type, "initial"))
        self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=attempt.id,
                channel=ContactType.EMAIL,
                subject="Terms",
                body="Price is 120 USD. MOQ is 10. Delivery EXW. Payment by bank transfer after invoice.",
                from_address="sales@supplier.test",
                to_address="agent@example.test",
            )
        )
        app = create_app(self.repo, runtime=runtime_with_model(FailingContractDraftModelProvider()))

        status, created = request_json(app, "POST", f"/api/products/{product.id}/contracts")

        self.assertEqual(201, status)
        draft = next(iter(self.repo.contracts.contract_drafts.values()))
        from backend.app.workers import process_contract_draft

        process_contract_draft(self.repo, runtime_with_model(FailingContractDraftModelProvider()), draft.agent_task_id)

        self.assertEqual("ready", draft.status.value)
        self.assertIn("modelProviderError", draft.extracted_data)
        status, download = request_json(app, "GET", f"/api/contracts/{draft.id}/download")
        self.assertEqual(200, status)
        self.assertIn("DRAFT CONTRACT", download)
        self.assertIn("NOT SIGNED AND NOT BINDING", download)

    def test_request_products_returns_duplicate_supplier_candidates_separately(self):
        from backend.app.domain import AgentTask, AgentTaskType

        request = self.repo.add_search_request(SearchRequest.create("duplicate suppliers"))
        primary = Product(
            search_request_id=request.id,
            title="Supplier A Product One",
            product_url="https://supplier-a.test/products/one",
            contacts=[],
            supplier_name="Supplier A",
        )
        self.repo.add_product(primary)
        task = self.repo.add_agent_task(
            AgentTask.create(
                AgentTaskType.PRODUCT_SEARCH,
                {"searchRequestId": str(request.id), "queryText": request.query_text, "maxResults": 5},
            )
        )
        request.agent_task_id = task.id
        task.output_payload = {
            "productsCreated": 1,
            "productsSkipped": 1,
            "errors": [
                {
                    "index": None,
                    "errors": ["duplicate supplier for search request"],
                    "raw": {
                        "title": "Supplier A Product Two",
                        "productUrl": "https://supplier-a.test/products/two",
                        "supplierName": "Supplier A",
                        "contacts": [{"type": "email", "value": "info@supplier-a.test"}],
                    },
                }
            ],
        }

        status, body = request_json(self.app, "GET", f"/api/search-requests/{request.id}/products")

        self.assertEqual(200, status)
        self.assertEqual(1, len(body["items"]))
        self.assertEqual(1, len(body["duplicates"]))
        self.assertEqual("Supplier A Product Two", body["duplicates"][0]["title"])
        self.assertEqual("duplicate supplier for search request", body["duplicates"][0]["duplicateReason"])


if __name__ == "__main__":
    unittest.main()
