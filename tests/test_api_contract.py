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


if __name__ == "__main__":
    unittest.main()
