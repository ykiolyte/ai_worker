import unittest
from unittest.mock import patch

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


class FailingIfCalledBrowserConnector(BrowserConnector):
    def __init__(self):
        super().__init__(ConnectorResult(success=False, error_message="browser should not be called"))

    def research(self, query_text: str):
        raise AssertionError("browser should not be called when Made-in-China already satisfies maxResults")


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
        self.assertEqual(1, len(products))
        self.assertEqual(1, len(self.repo.supplier_contacts))
        self.assertEqual(
            {"productsCreated": 1, "demoProductsCreated": 0, "productsSkipped": 0, "errors": []},
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
        self.assertEqual(1, len(self.repo.products))
        self.assertEqual(1, task.output_payload["productsCreated"])
        self.assertEqual(0, task.output_payload["demoProductsCreated"])
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
        self.assertEqual(1, len(self.repo.products))
        self.assertEqual(0, len(self.repo.supplier_contacts))
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
        self.assertEqual(1, len(products))
        self.assertEqual("E2E UAV Flight Controller FC-100", products[0].title)
        self.assertEqual(1, task.output_payload["productsCreated"])
        self.assertEqual(0, task.output_payload["demoProductsCreated"])
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

    def test_product_search_does_not_collapse_made_in_china_products_by_marketplace_domain(self):
        request, task = self.create_search_task("USB 3.0 camera", max_results=5)
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "USB Camera Supplier One",
                            "productUrl": "https://www.made-in-china.com/product/one.html",
                            "supplierName": "Supplier One",
                            "contacts": [],
                            "attributes": {
                                "sourcePlatform": "made-in-china",
                                "supplierUrl": "https://supplier-one.en.made-in-china.com",
                            },
                        },
                        {
                            "title": "USB Camera Supplier Two",
                            "productUrl": "https://www.made-in-china.com/product/two.html",
                            "supplierName": "Supplier Two",
                            "contacts": [],
                            "attributes": {
                                "sourcePlatform": "made-in-china",
                                "supplierUrl": "https://supplier-two.en.made-in-china.com",
                            },
                        },
                        {
                            "title": "USB Camera Supplier Three",
                            "productUrl": "https://www.made-in-china.com/product/three.html",
                            "supplierName": "Supplier Three",
                            "contacts": [],
                            "attributes": {
                                "sourcePlatform": "made-in-china",
                                "supplierUrl": "https://supplier-three.en.made-in-china.com",
                            },
                        },
                        {
                            "title": "USB Camera Supplier Four",
                            "productUrl": "https://www.made-in-china.com/product/four.html",
                            "supplierName": "Supplier Four",
                            "contacts": [],
                            "attributes": {
                                "sourcePlatform": "made-in-china",
                                "supplierUrl": "https://supplier-four.en.made-in-china.com",
                            },
                        },
                    ]
                },
            )
        )

        with patch.dict("os.environ", {"DISABLE_DEMO_PRODUCT_INJECTION": "true"}, clear=False):
            process_product_search(self.repo, runtime_with_browser(browser), task.id)

        products = self.repo.list_products_for_request(request.id)
        self.assertEqual(4, len(products))
        self.assertEqual(4, task.output_payload["productsCreated"])
        self.assertEqual(0, task.output_payload["productsSkipped"])

    def test_product_search_keeps_multiple_made_in_china_products_from_same_supplier(self):
        request, task = self.create_search_task("USB 3.0 camera", max_results=5)
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "USB Camera Model A",
                            "productUrl": "https://supplier-one.en.made-in-china.com/product/a.html",
                            "supplierName": "Supplier One",
                            "contacts": [],
                            "attributes": {"sourcePlatform": "made-in-china", "supplierUrl": "https://world-port.made-in-china.com/viewVR?comId=one"},
                        },
                        {
                            "title": "USB Camera Model B",
                            "productUrl": "https://supplier-one.en.made-in-china.com/product/b.html",
                            "supplierName": "Supplier One",
                            "contacts": [],
                            "attributes": {"sourcePlatform": "made-in-china", "supplierUrl": "https://world-port.made-in-china.com/viewVR?comId=one"},
                        },
                    ]
                },
            )
        )

        with patch.dict("os.environ", {"DISABLE_DEMO_PRODUCT_INJECTION": "true"}, clear=False):
            process_product_search(self.repo, runtime_with_browser(browser), task.id)

        products = self.repo.list_products_for_request(request.id)
        self.assertEqual(["USB Camera Model A", "USB Camera Model B"], [product.title for product in products])
        self.assertEqual(2, task.output_payload["productsCreated"])
        self.assertEqual(0, task.output_payload["productsSkipped"])

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

    def test_product_search_persists_made_in_china_inquiry_only_candidates(self):
        request, task = self.create_search_task("industrial cnc controller", max_results=5)
        browser = BrowserConnector(ConnectorResult(success=True, payload={"products": []}))
        made_in_china = MadeInChinaConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "Made-in-China CNC Motion Controller",
                            "productUrl": "https://cnc.en.made-in-china.com/product/cnc-controller.html",
                            "price": "560.00",
                            "currency": "USD",
                            "supplierName": "Chongqing SiyueEr Technology Co., Ltd.",
                            "contacts": [],
                            "attributes": {
                                "sourcePlatform": "made-in-china",
                                "supplierUrl": "https://cnc.en.made-in-china.com",
                                "inquiryUrl": "https://www.made-in-china.com/sendInquiry/prod_cnc.html",
                                "moq": "1 Piece (MOQ)",
                            },
                        }
                    ],
                    "source": {"provider": "made_in_china"},
                },
            )
        )

        process_product_search(self.repo, runtime_with_browser(browser, made_in_china), task.id)

        products = [
            product for product in self.repo.list_products_for_request(request.id)
            if product.attributes.get("demo") != "true"
        ]
        self.assertEqual(1, len(products))
        self.assertEqual("Made-in-China CNC Motion Controller", products[0].title)
        self.assertEqual("made-in-china", products[0].attributes["sourcePlatform"])
        self.assertEqual("https://www.made-in-china.com/sendInquiry/prod_cnc.html", products[0].attributes["inquiryUrl"])
        self.assertEqual(0, len(self.repo.list_contacts_for_product(products[0].id)))
        self.assertEqual(1, task.output_payload["productsCreated"])
        self.assertEqual(0, task.output_payload["productsSkipped"])

    def test_product_search_uses_made_in_china_first_without_browser_dobor(self):
        request, task = self.create_search_task("industrial cnc controller", max_results=5)
        made_in_china = MadeInChinaConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "Made-in-China CNC Motion Controller",
                            "productUrl": "https://cnc.en.made-in-china.com/product/cnc-controller.html",
                            "supplierName": "Chongqing SiyueEr Technology Co., Ltd.",
                            "contacts": [],
                            "attributes": {
                                "sourcePlatform": "made-in-china",
                                "supplierUrl": "https://cnc.en.made-in-china.com",
                                "inquiryUrl": "https://www.made-in-china.com/sendInquiry/prod_cnc.html",
                            },
                        }
                    ],
                    "source": {"provider": "made_in_china"},
                },
            )
        )

        process_product_search(self.repo, runtime_with_browser(FailingIfCalledBrowserConnector(), made_in_china), task.id)

        self.assertEqual(SearchRequestStatus.COMPLETED, request.status)
        products = [
            product for product in self.repo.list_products_for_request(request.id)
            if product.attributes.get("demo") != "true"
        ]
        self.assertEqual(["Made-in-China CNC Motion Controller"], [product.title for product in products])
        self.assertEqual([request.query_text], made_in_china.queries)
        self.assertNotIn("connectorErrors", task.output_payload)

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

    def test_product_search_persists_sourcingai_metadata_and_extended_product_fields(self):
        request, task = self.create_search_task("ПК, вычислительные компьютеры, ноутбуки", max_results=5)
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "normalizedIntent": {
                        "rawQuery": request.query_text,
                        "productCategory": "computers and computing equipment",
                        "supplierPreference": "manufacturer_first",
                    },
                    "missingFields": ["quantity"],
                    "clarifyingQuestions": ["Какой объём закупки планируется?"],
                    "commonFilters": ["Manufacturer", "Audited Supplier"],
                    "productAttributes": [{"name": "Processor", "values": ["Intel", "AMD"]}],
                    "sourcingGuidance": {"riskWarnings": ["Verify supplier identity"]},
                    "products": [
                        {
                            "title": "Industrial Fanless Mini PC",
                            "productUrl": "https://supplier.test/products/mini-pc",
                            "priceRange": "Negotiable",
                            "moq": "10 Pieces",
                            "supplierName": "Example Technology Co., Ltd.",
                            "supplierBadges": ["Manufacturer"],
                            "fitScore": 0.86,
                            "fitSummary": "Matches industrial computing request.",
                            "matchedRequirements": [
                                {"requirement": "computer supplier", "evidence": "Title mentions Mini PC"}
                            ],
                            "missingRequirements": ["No certification evidence found"],
                            "contacts": [{"type": "email", "value": "supplier@example.test"}],
                        }
                    ],
                },
            )
        )

        process_product_search(self.repo, runtime_with_browser(browser), task.id)

        self.assertEqual({"rawQuery": request.query_text, "productCategory": "computers and computing equipment", "supplierPreference": "manufacturer_first"}, request.normalized_intent)
        self.assertEqual(["quantity"], request.missing_fields)
        self.assertEqual(["Manufacturer", "Audited Supplier"], request.common_filters)
        self.assertEqual(1, request.suppliers_count)
        product = next(product for product in self.repo.list_products_for_request(request.id) if product.attributes.get("demo") != "true")
        self.assertEqual("Negotiable", product.price_range)
        self.assertEqual("10 Pieces", product.moq)
        self.assertEqual("Manufacturer", product.supplier_badges[0])
        self.assertEqual("computer supplier", product.matched_requirements[0]["requirement"])

    def test_product_search_disables_demo_in_acceptance_mode(self):
        request, task = self.create_search_task("industrial mini pc")
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "Industrial Mini PC",
                            "productUrl": "https://supplier.test/products/mini-pc",
                            "contacts": [{"type": "email", "value": "supplier@example.test"}],
                        }
                    ]
                },
            )
        )

        with patch.dict("os.environ", {"DISABLE_DEMO_PRODUCT_INJECTION": "true"}, clear=False):
            process_product_search(self.repo, runtime_with_browser(browser), task.id)

        products = self.repo.list_products_for_request(request.id)
        self.assertEqual(["Industrial Mini PC"], [product.title for product in products])

    def test_product_search_derives_filter_facets_from_product_attributes(self):
        request, task = self.create_search_task("USB 3.0 camera")
        browser = BrowserConnector(
            ConnectorResult(
                success=True,
                payload={
                    "products": [
                        {
                            "title": "USB 3.0 Industrial Camera",
                            "productUrl": "https://www.made-in-china.com/product/example.html",
                            "supplierName": "Camera Supplier",
                            "priceRange": "US$120-150",
                            "supportsCustomization": True,
                            "sampleAvailable": True,
                            "contacts": [],
                            "attributes": {
                                "sourcePlatform": "made-in-china",
                                "resolution": "12.0 MP",
                                "sensorSize": "CMOS Global Shutter",
                                "frameRate": "60 FPS",
                            },
                        }
                    ]
                },
            )
        )

        with patch.dict("os.environ", {"DISABLE_DEMO_PRODUCT_INJECTION": "true"}, clear=False):
            process_product_search(self.repo, runtime_with_browser(browser), task.id)

        facets = {facet["name"]: facet["values"] for facet in request.product_attributes}
        self.assertIn("Price range", request.common_filters)
        self.assertIn("Customization Available", request.common_filters)
        self.assertIn("Sample Available", request.common_filters)
        self.assertEqual(["USB 3.0"], facets["Interface"])
        self.assertEqual(["12.0 MP"], facets["Resolution"])
        self.assertEqual(["CMOS Global Shutter"], facets["Sensor Type"])
        self.assertEqual(["60 FPS"], facets["Frame Rate"])


if __name__ == "__main__":
    unittest.main()
