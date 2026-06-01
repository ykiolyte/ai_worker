import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.app.agent import AgentRuntime, ConnectorResult, ToolRegistry
from backend.app.domain import AgentTask, AgentTaskType, ContactAttempt, ContactType, Product, SearchRequest, SupplierContact
from backend.app.postgres_repository import SqlAlchemyRepository
from backend.app.repositories import InMemoryRepository
from backend.app.worker import run_worker_loop, run_worker_tick


class FakeModelProvider:
    name = "fake-model"

    def complete(self, prompt: str, tools=None):
        return {
            "reply": (
                "Hello. I represent the purchasing department of AlphaLogisticService LLC.\n"
                "Product: Fast Search Product\n"
                "Product link: https://supplier.test/products/fast\n"
                "Please share the current price, availability, MOQ/minimum order quantity, "
                "lead time, payment terms, and delivery/shipping terms."
            )
        }


class BrowserConnector:
    def research(self, query_text: str, max_results=None):
        return ConnectorResult(
            success=True,
            payload={
                "products": [
                    {
                        "title": "Fast Search Product",
                        "productUrl": "https://supplier.test/products/fast",
                        "contacts": [{"type": "email", "value": "sales@supplier.test"}],
                    }
                ]
            },
        )


class EmailConnector:
    from_address = "agent@example.test"
    password = "worker-secret"

    def __init__(self):
        self.calls = []

    def send(self, destination: str, subject: str, body: str):
        self.calls.append((destination, subject, body))
        return ConnectorResult(success=True, external_id="worker-email-1")


def runtime_with_browser():
    registry = ToolRegistry()
    registry.register("browser_mcp", BrowserConnector())
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


def runtime_with_email(email: EmailConnector):
    registry = ToolRegistry()
    registry.register("email", email)
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


class WorkerRuntimeContractTest(unittest.TestCase):
    def test_worker_tick_processes_queued_product_search(self):
        repo = InMemoryRepository()
        request = repo.add_search_request(SearchRequest.create("Fast Search Product"))
        task = repo.add_agent_task(
            AgentTask.create(
                AgentTaskType.PRODUCT_SEARCH,
                {"searchRequestId": str(request.id), "queryText": request.query_text, "maxResults": 1},
            )
        )
        request.agent_task_id = task.id

        processed = run_worker_tick(repo, runtime_with_browser())

        self.assertEqual(1, processed)
        self.assertEqual("completed", task.status.value)
        self.assertEqual("completed", request.status.value)
        products = repo.list_products_for_request(request.id)
        self.assertGreaterEqual(len(products), 1)
        self.assertTrue(any(product.title == "Fast Search Product" for product in products))

    def test_worker_tick_processes_queued_supplier_contact(self):
        repo, _, _, attempt, task = create_supplier_contact_task()
        email = EmailConnector()

        processed = run_worker_tick(repo, runtime_with_email(email))

        self.assertEqual(1, processed)
        self.assertEqual(1, len(email.calls))
        self.assertEqual("sales@supplier.test", email.calls[0][0])
        self.assertEqual("sent", attempt.status.value)
        self.assertEqual("completed", task.status.value)
        messages = repo.list_conversation_messages_for_product(attempt.product_id)
        self.assertEqual(1, len(messages))
        self.assertEqual("sent", messages[0].status.value)
        self.assertEqual("worker-email-1", messages[0].external_message_id)

    def test_worker_loop_processes_queued_supplier_contact_instead_of_idling(self):
        repo, _, _, attempt, task = create_supplier_contact_task()
        email = EmailConnector()

        processed = run_worker_loop(
            repo,
            runtime_with_email(email),
            poll_interval_seconds=0,
            max_ticks=1,
        )

        self.assertEqual(1, processed)
        self.assertEqual(1, len(email.calls))
        self.assertEqual("sent", attempt.status.value)
        self.assertEqual("completed", task.status.value)

    def test_worker_tick_processes_durable_queued_product_search(self):
        with TemporaryDirectory() as directory:
            database_url = f"sqlite:///{Path(directory) / 'worker.db'}"
            worker_repo = SqlAlchemyRepository(database_url, create_schema=True)
            reader_repo = SqlAlchemyRepository(database_url, create_schema=True)
            request = SearchRequest.create("Fast Search Product", max_results=1)
            task = AgentTask.create(
                AgentTaskType.PRODUCT_SEARCH,
                {"searchRequestId": str(request.id), "queryText": request.query_text, "maxResults": 1},
            )
            request.agent_task_id = task.id
            worker_repo.add_search_request(request)
            worker_repo.add_agent_task(task)

            processed = run_worker_tick(worker_repo, runtime_with_browser(), max_tasks=1)

            loaded_request = reader_repo.get_search_request(request.id)
            loaded_task = reader_repo.get_agent_task(task.id)
            self.assertEqual(1, processed)
            self.assertEqual("completed", loaded_task.status.value)
            self.assertEqual("completed", loaded_request.status.value)
            products = reader_repo.list_products_for_request(request.id)
            self.assertTrue(any(product.title == "Fast Search Product" for product in products))


def create_supplier_contact_task():
    repo = InMemoryRepository()
    request = repo.add_search_request(SearchRequest.create("Fast Search Product"))
    contact = SupplierContact.create(ContactType.EMAIL, "sales@supplier.test")
    product = Product(
        search_request_id=request.id,
        title="Fast Search Product",
        product_url="https://supplier.test/products/fast",
        contacts=[contact],
    )
    contact.product_id = product.id
    repo.add_product(product)
    attempt = repo.add_contact_attempt(ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending"))
    task = repo.add_agent_task(
        AgentTask.create(
            AgentTaskType.SUPPLIER_CONTACT,
            {
                "productId": str(product.id),
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(attempt.id),
                "channel": contact.contact_type.value,
                "language": "en",
                "style": "formal",
            },
        )
    )
    attempt.agent_task_id = task.id
    return repo, product, contact, attempt, task


if __name__ == "__main__":
    unittest.main()
