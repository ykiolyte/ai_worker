import unittest

from backend.app.agent import AgentRuntime, ConnectorResult, ToolRegistry
from backend.app.domain import (
    AgentTask,
    AgentTaskStatus,
    AgentTaskType,
    ContactType,
    SearchRequest,
    SearchRequestStatus,
)
from backend.app.repositories import InMemoryRepository
from backend.app.workers import process_product_search


class FakeModelProvider:
    name = "fake-model"

    def complete(self, prompt: str, tools=None):
        return {"text": "ok"}


class BrowserConnector:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def research(self, query_text: str):
        self.queries.append(query_text)
        return self.result


class MaxResultsAwareBrowserConnector(BrowserConnector):
    def __init__(self, result):
        super().__init__(result)
        self.max_results = []

    def research(self, query_text: str, max_results=None):
        self.queries.append(query_text)
        self.max_results.append(max_results)
        return self.result


class MadeInChinaConnector:
    def __init__(self, result):
        self.result = result
        self.queries = []
        self.max_results = []

    def research(self, query_text: str, max_results=None):
        self.queries.append(query_text)
        self.max_results.append(max_results)
        return self.result


def runtime_with_browser(browser, made_in_china=None):
    registry = ToolRegistry()
    registry.register("browser_mcp", browser)
    if made_in_china is not None:
        registry.register("made_in_china", made_in_china)
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


class ProductSearchWorkerContractTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()

    def create_search_task(self, query_text="E2E UAV Flight Controller FC-100", max_results=5):
        request = self.repo.add_search_request(SearchRequest.create(query_text, max_results=max_results))
        task = AgentTask.create(
            AgentTaskType.PRODUCT_SEARCH,
            {
                "searchRequestId": str(request.id),
                "queryText": request.query_text,
                "maxResults": request.max_results,
            },
        )
        request.agent_task_id = task.id
        self.repo.add_agent_task(task)
        return request, task

    def test_product_search_happy_path(self):
        request, task = self.create_search_task()
        browser = BrowserConnector(
            ConnectorResult(
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
        )

        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        self.assertEqual([request.query_text], browser.queries)
        self.assertEqual(SearchRequestStatus.COMPLETED, request.status)
        self.assertEqual(AgentTaskStatus.COMPLETED, task.status)
        products = self.repo.list_products_for_request(request.id)
        self.assertEqual(2, len(products))
        demo = next(product for product in products if "Демо" in product.title)
        contacts = self.repo.list_contacts_for_product(demo.id)
        self.assertNotIn("demo.local", demo.product_url)
        self.assertTrue(demo.product_url.startswith("http://localhost:5173/"))
        self.assertEqual(2, len(self.repo.supplier_contacts))
        self.assertEqual(ContactType.EMAIL, contacts[0].contact_type)
        self.assertEqual("ezmmr4us@gmail.com", contacts[0].contact_value)
        self.assertEqual(
            {"productsCreated": 1, "demoProductsCreated": 1, "productsSkipped": 0, "errors": []},
            task.output_payload,
        )

    def test_product_search_browser_failure_is_persisted(self):
        request, task = self.create_search_task("E2E Browser MCP failure")
        browser = BrowserConnector(ConnectorResult(success=False, error_message="browser unavailable"))

        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        self.assertEqual(SearchRequestStatus.FAILED, request.status)
        self.assertEqual(AgentTaskStatus.FAILED, task.status)
        self.assertEqual("browser unavailable", request.error_message)
        self.assertEqual("browser unavailable", task.error_message)

    def test_product_search_partial_valid_output(self):
        request, task = self.create_search_task()
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "E2E UAV Flight Controller FC-100",
                            "productUrl": "https://supplier.test/products/fc-100",
                            "contacts": [{"type": "email", "value": "supplier@example.test"}],
                        },
                        {
                            "title": "",
                            "productUrl": "not-a-url",
                            "contacts": [{"type": "email", "value": "not-an-email"}],
                        },
                    ]
                },
            )
        )

        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        self.assertEqual(SearchRequestStatus.COMPLETED, request.status)
        self.assertEqual(AgentTaskStatus.COMPLETED, task.status)
        self.assertEqual(2, len(self.repo.products))
        self.assertEqual(1, task.output_payload["productsCreated"])
        self.assertEqual(1, task.output_payload["demoProductsCreated"])
        self.assertEqual(1, task.output_payload["productsSkipped"])
        self.assertIn("title is required", task.output_payload["errors"][0]["errors"])

    def test_product_search_can_persist_contactless_product_when_enabled(self):
        request, task = self.create_search_task("Industrial CNC Controller IC-200")
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "Industrial CNC Controller IC-200",
                            "productUrl": "https://supplier-public.example/products/ic-200",
                            "price": "840.00",
                            "currency": "USD",
                            "contacts": [],
                        }
                    ]
                },
            )
        )

        process_product_search(
            self.repo,
            runtime_with_browser(browser),
            task.id,
            allow_products_without_contacts=True,
        )

        self.assertEqual(SearchRequestStatus.COMPLETED, request.status)
        self.assertEqual(AgentTaskStatus.COMPLETED, task.status)
        self.assertEqual(2, len(self.repo.products))
        self.assertEqual(1, len(self.repo.supplier_contacts))
        self.assertEqual(0, task.output_payload["productsSkipped"])

    def test_product_search_respects_request_max_results(self):
        request, task = self.create_search_task(max_results=1)
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "E2E UAV Flight Controller FC-100",
                            "productUrl": "https://supplier.test/products/fc-100",
                            "contacts": [{"type": "email", "value": "supplier@example.test"}],
                        },
                        {
                            "title": "E2E UAV Flight Controller FC-200",
                            "productUrl": "https://supplier.test/products/fc-200",
                            "contacts": [{"type": "email", "value": "sales@example.test"}],
                        },
                    ]
                },
            )
        )

        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        products = self.repo.list_products_for_request(request.id)
        self.assertEqual(2, len(products))
        self.assertEqual("E2E UAV Flight Controller FC-100", products[0].title)
        self.assertEqual("Демо-карточка для презентации", products[1].title)
        self.assertEqual(1, task.output_payload["productsCreated"])
        self.assertEqual(1, task.output_payload["demoProductsCreated"])
        self.assertEqual(1, task.output_payload["productsSkipped"])
        self.assertEqual(["maxResults limit reached"], task.output_payload["errors"][0]["errors"])

    def test_product_search_deduplicates_supplier_domain(self):
        request, task = self.create_search_task(max_results=5)
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "Supplier A Product One",
                            "productUrl": "https://supplier-a.test/products/one",
                            "contacts": [{"type": "email", "value": "sales@supplier-a.test"}],
                        },
                        {
                            "title": "Supplier A Product Two",
                            "productUrl": "https://supplier-a.test/products/two",
                            "contacts": [{"type": "email", "value": "info@supplier-a.test"}],
                        },
                        {
                            "title": "Supplier B Product",
                            "productUrl": "https://supplier-b.test/products/one",
                            "contacts": [{"type": "email", "value": "sales@supplier-b.test"}],
                        },
                    ]
                },
            )
        )

        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        products = [
            product for product in self.repo.list_products_for_request(request.id)
            if product.attributes.get("demo") != "true"
        ]
        self.assertEqual(["supplier-a.test", "supplier-b.test"], [product.source_domain for product in products])
        self.assertEqual(2, task.output_payload["productsCreated"])
        self.assertEqual(1, task.output_payload["productsSkipped"])
        self.assertEqual(["duplicate supplier for search request"], task.output_payload["errors"][0]["errors"])

    def test_product_search_does_not_duplicate_demo_card_on_retry(self):
        request, task = self.create_search_task()
        browser = BrowserConnector(ConnectorResult(success=True, payload={"products": []}))

        process_product_search(self.repo, runtime_with_browser(browser), task.id)
        task.status = AgentTaskStatus.QUEUED
        request.status = SearchRequestStatus.QUEUED
        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        products = self.repo.list_products_for_request(request.id)
        self.assertEqual(1, len(products))
        self.assertEqual("Демо-карточка для презентации", products[0].title)

    def test_product_search_passes_max_results_to_browser_when_supported(self):
        request, task = self.create_search_task("iphone 16", max_results=8)
        browser = MaxResultsAwareBrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "iPhone 16",
                            "productUrl": "https://supplier.test/products/iphone-16",
                            "contacts": [{"type": "email", "value": "sales@example.test"}],
                        },
                    ]
                },
            )
        )

        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        self.assertEqual([request.query_text], browser.queries)
        self.assertEqual([8], browser.max_results)

    def test_product_search_merges_made_in_china_candidates_when_enabled(self):
        request, task = self.create_search_task("industrial cnc controller", max_results=5)
        browser = BrowserConnector(ConnectorResult(success=True, payload={"products": []}))
        made_in_china = MadeInChinaConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "Industrial CNC Controller IC-200",
                            "productUrl": "https://cnc.en.made-in-china.com/product/ic200.html",
                            "price": "840.00",
                            "currency": "USD",
                            "supplierName": "Shenzhen CNC Factory",
                            "contacts": [],
                            "attributes": {"sourcePlatform": "made-in-china", "moq": "10 Pieces"},
                        }
                    ],
                    "source": {"provider": "made_in_china"},
                },
            )
        )

        process_product_search(
            self.repo,
            runtime_with_browser(browser, made_in_china),
            task.id,
            allow_products_without_contacts=True,
        )

        self.assertEqual([request.query_text], made_in_china.queries)
        self.assertEqual([5], made_in_china.max_results)
        products = [
            product for product in self.repo.list_products_for_request(request.id)
            if product.attributes.get("demo") != "true"
        ]
        self.assertEqual(1, len(products))
        self.assertEqual("Industrial CNC Controller IC-200", products[0].title)
        self.assertEqual("made-in-china", products[0].attributes["sourcePlatform"])
        self.assertEqual(1, task.output_payload["productsCreated"])

    def test_product_search_keeps_working_when_made_in_china_fails(self):
        request, task = self.create_search_task("rack workstation", max_results=5)
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "Rack Workstation RW-500",
                            "productUrl": "https://supplier.test/products/rw-500",
                            "contacts": [{"type": "email", "value": "sales@supplier.test"}],
                        }
                    ]
                },
            )
        )
        made_in_china = MadeInChinaConnector(ConnectorResult(success=False, error_message="Made-in-China captcha detected"))

        process_product_search(self.repo, runtime_with_browser(browser, made_in_china), task.id)

        self.assertEqual(SearchRequestStatus.COMPLETED, request.status)
        self.assertEqual(AgentTaskStatus.COMPLETED, task.status)
        self.assertEqual(1, task.output_payload["productsCreated"])
        self.assertEqual(
            {"source": "made_in_china", "error": "Made-in-China captcha detected"},
            task.output_payload["connectorErrors"][0],
        )


if __name__ == "__main__":
    unittest.main()
