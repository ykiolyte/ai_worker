import unittest

from backend.app.agent import AgentRuntime, ConnectorResult, ToolRegistry
from backend.app.domain import AgentTaskType
from backend.app.main import create_app
from backend.app.repositories import InMemoryRepository
from backend.app.workers import process_product_search, process_supplier_contact
from tests.asgi_client import request_json


class FakeModelProvider:
    name = "fake-model"

    def complete(self, prompt: str, tools=None):
        return {
            "reply": (
                "Hello. I represent the purchasing department of AlphaLogisticService LLC.\n"
                "Product: E2E UAV Flight Controller FC-100\n"
                "Product link: https://supplier.test/products/fc-100\n"
                "Please share the current price, availability, MOQ/minimum order quantity, "
                "lead time, payment terms, and delivery/shipping terms."
            )
        }


class BrowserConnector:
    def __init__(self, payload):
        self.payload = payload

    def research(self, query_text: str):
        return ConnectorResult(success=True, payload=self.payload)


class SendConnector:
    def __init__(self, external_id):
        self.external_id = external_id

    def send(self, *args):
        return ConnectorResult(success=True, external_id=self.external_id)


def runtime(browser_payload):
    registry = ToolRegistry()
    registry.register("browser_mcp", BrowserConnector(browser_payload))
    registry.register("email", SendConnector("email-smoke-1"))
    registry.register("telegram", SendConnector("telegram-smoke-1"))
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


class SmokeFlowTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()
        self.app = create_app(self.repo)

    def create_and_process_search(self, products):
        status, created = request_json(
            self.app,
            "POST",
            "/api/search-requests",
            {"queryText": "E2E UAV Flight Controller FC-100"},
        )
        self.assertEqual(201, status)
        task = next(task for task in self.repo.agent_tasks.values() if task.task_type == AgentTaskType.PRODUCT_SEARCH)
        process_product_search(self.repo, runtime({"products": products}), task.id)
        return created

    def test_full_search_request_smoke_flow(self):
        created = self.create_and_process_search(
            [
                {
                    "title": "E2E UAV Flight Controller FC-100",
                    "productUrl": "https://supplier.test/products/fc-100",
                    "price": "120.00",
                    "currency": "USD",
                    "contacts": [{"type": "email", "value": "supplier@example.test"}],
                }
            ]
        )

        status, products = request_json(self.app, "GET", f"/api/search-requests/{created['id']}/products")

        self.assertEqual(200, status)
        self.assertEqual(1, products["total"])
        self.assertEqual("E2E UAV Flight Controller FC-100", products["items"][0]["title"])

    def test_supplier_contact_smoke_flow(self):
        self.create_and_process_search(
            [
                {
                    "title": "E2E UAV Flight Controller FC-100",
                    "productUrl": "https://supplier.test/products/fc-100",
                    "contacts": [{"type": "email", "value": "supplier@example.test"}],
                }
            ]
        )
        product = next(iter(self.repo.products.values()))
        status, attempt = request_json(self.app, "POST", f"/api/products/{product.id}/contact-supplier")
        self.assertEqual(201, status)

        task = next(task for task in self.repo.agent_tasks.values() if task.task_type == AgentTaskType.SUPPLIER_CONTACT)
        process_supplier_contact(self.repo, runtime({"products": []}), task.id)

        status, detail = request_json(self.app, "GET", f"/api/products/{product.id}")
        self.assertEqual(200, status)
        self.assertEqual("sent", detail["contactAttempts"][0]["status"])
        self.assertEqual("email", detail["contactAttempts"][0]["channel"])
        self.assertEqual(1, len(detail["conversationMessages"]))
        self.assertEqual("sent", detail["conversationMessages"][0]["status"])
        self.assertIn("E2E UAV Flight Controller FC-100", detail["conversationMessages"][0]["body"])

    def test_nullable_price_and_invalid_product_smoke(self):
        self.create_and_process_search(
            [
                {
                    "title": "E2E Rack Workstation RW-500",
                    "productUrl": "https://supplier.test/products/rw-500",
                    "price": None,
                    "contacts": [{"type": "email", "value": "supplier@example.test"}],
                },
                {
                    "title": "",
                    "productUrl": "not-a-url",
                    "contacts": [{"type": "email", "value": "not-an-email"}],
                },
            ]
        )

        product = next(iter(self.repo.products.values()))
        task = next(task for task in self.repo.agent_tasks.values() if task.task_type == AgentTaskType.PRODUCT_SEARCH)

        self.assertIsNone(product.price)
        self.assertEqual(1, len(self.repo.products))
        self.assertEqual(1, task.output_payload["productsSkipped"])

    def test_no_active_work_after_smoke_completion(self):
        self.test_supplier_contact_smoke_flow()
        active_tasks = [
            task for task in self.repo.agent_tasks.values() if task.status.value in {"queued", "running"}
        ]
        active_attempts = [
            attempt for attempt in self.repo.contact_attempts.values() if attempt.status.value in {"queued", "running"}
        ]

        self.assertEqual([], active_tasks)
        self.assertEqual([], active_attempts)


if __name__ == "__main__":
    unittest.main()
