import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.app.agent import AgentRuntime, ConnectorResult, ToolRegistry
from backend.app.domain import AgentTask, AgentTaskType, ContactType, ContractDraft, Product, SearchRequest, SupplierContact
from backend.app.postgres_repository import SqlAlchemyRepository
from backend.app.workers import process_product_search


class FakeModelProvider:
    name = "fake-model"

    def complete(self, prompt: str, tools=None):
        return {"text": "ok"}


class BrowserConnector:
    def research(self, query_text: str, max_results=None):
        return ConnectorResult(
            success=True,
            payload={
                "normalizedIntent": {"rawQuery": query_text, "product": "industrial mini pc"},
                "products": [
                    {
                        "title": "Industrial Mini PC i5",
                        "productUrl": "https://supplier.test/products/mini-pc-i5",
                        "priceRange": "$120-150",
                        "moq": "10 pieces",
                        "contacts": [{"type": "email", "value": "sales@supplier.test"}],
                    }
                ],
            },
        )


def runtime_with_browser():
    registry = ToolRegistry()
    registry.register("browser_mcp", BrowserConnector())
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


class DurableRepositoryContractTest(unittest.TestCase):
    def test_two_repository_instances_share_search_request_and_task_state(self):
        with TemporaryDirectory() as directory:
            database_url = f"sqlite:///{Path(directory) / 'repo.db'}"
            first = SqlAlchemyRepository(database_url)
            second = SqlAlchemyRepository(database_url)
            first.create_schema()
            second.create_schema()

            request = SearchRequest.create("ПК, вычислительные компьютеры, ноутбуки", max_results=7)
            task = AgentTask.create(
                AgentTaskType.PRODUCT_SEARCH,
                {"searchRequestId": str(request.id), "queryText": request.query_text, "maxResults": request.max_results},
            )
            request.agent_task_id = task.id
            first.add_agent_task(task)
            first.add_search_request(request)

            loaded_request = second.get_search_request(request.id)
            loaded_task = second.get_agent_task(task.id)

            self.assertIsNotNone(loaded_request)
            self.assertIsNotNone(loaded_task)
            self.assertEqual("ПК, вычислительные компьютеры, ноутбуки", loaded_request.query_text)
            self.assertEqual(7, loaded_request.max_results)
            self.assertEqual("queued", loaded_task.status.value)

    def test_list_queued_agent_tasks_is_durable(self):
        with TemporaryDirectory() as directory:
            database_url = f"sqlite:///{Path(directory) / 'repo.db'}"
            first = SqlAlchemyRepository(database_url)
            second = SqlAlchemyRepository(database_url)
            first.create_schema()
            second.create_schema()

            request = SearchRequest.create("industrial mini pc")
            task = AgentTask.create(AgentTaskType.PRODUCT_SEARCH, {"searchRequestId": str(request.id)})
            first.add_search_request(request)
            first.add_agent_task(task)

            queued = second.list_queued_agent_tasks(limit=10)

            self.assertEqual([task.id], [item.id for item in queued])

    def test_product_search_worker_persists_status_and_products_for_other_instances(self):
        with TemporaryDirectory() as directory:
            database_url = f"sqlite:///{Path(directory) / 'repo.db'}"
            worker_repo = SqlAlchemyRepository(database_url)
            reader_repo = SqlAlchemyRepository(database_url)
            worker_repo.create_schema()
            reader_repo.create_schema()

            request = SearchRequest.create("industrial mini pc", max_results=3)
            task = AgentTask.create(
                AgentTaskType.PRODUCT_SEARCH,
                {"searchRequestId": str(request.id), "queryText": request.query_text, "maxResults": request.max_results},
            )
            request.agent_task_id = task.id
            worker_repo.add_search_request(request)
            worker_repo.add_agent_task(task)

            with patch.dict("os.environ", {"DISABLE_DEMO_PRODUCT_INJECTION": "true"}):
                process_product_search(worker_repo, runtime_with_browser(), task.id)

            loaded_request = reader_repo.get_search_request(request.id)
            loaded_task = reader_repo.get_agent_task(task.id)
            products = reader_repo.list_products_for_request(request.id)

            self.assertEqual("completed", loaded_request.status.value)
            self.assertEqual("completed", loaded_task.status.value)
            self.assertEqual({"productsCreated": 1, "demoProductsCreated": 0, "productsSkipped": 0, "errors": []}, loaded_task.output_payload)
            self.assertEqual(1, len(products))
            self.assertEqual("Industrial Mini PC i5", products[0].title)
            self.assertEqual("$120-150", products[0].price_range)
            self.assertEqual("10 pieces", products[0].moq)

    def test_contract_drafts_are_durable(self):
        with TemporaryDirectory() as directory:
            database_url = f"sqlite:///{Path(directory) / 'repo.db'}"
            first = SqlAlchemyRepository(database_url)
            second = SqlAlchemyRepository(database_url)
            first.create_schema()
            second.create_schema()

            contact = SupplierContact.create(ContactType.EMAIL, "contracts@supplier.test")
            product = Product(
                title="Industrial Mini PC i5",
                product_url="https://supplier.test/products/mini-pc-i5",
                contacts=[contact],
                supplier_name="Supplier Test",
            )
            contact.product_id = product.id
            first.add_product(product)
            draft = ContractDraft.create(product.id, contact.id, product.supplier_name)
            first.contracts.add_contract_draft(draft)

            loaded = second.contracts.get_contract_draft(draft.id)
            listed = second.contracts.list_contract_drafts_for_product(product.id)

            self.assertEqual(draft.id, loaded.id)
            self.assertEqual("Supplier Test", loaded.supplier_name)
            self.assertEqual([draft.id], [item.id for item in listed])


if __name__ == "__main__":
    unittest.main()
