import unittest

from backend.app.agent import AgentRuntime, ConnectorResult, ToolRegistry
from backend.app.domain import (
    AgentTask,
    AgentTaskStatus,
    AgentTaskType,
    ContactAttempt,
    ContactAttemptStatus,
    ContactType,
    ConversationDirection,
    ConversationMessage,
    ConversationMessageStatus,
    Product,
    SearchRequest,
    SupplierContact,
)
from backend.app.repositories import InMemoryRepository
from backend.app.workers import process_supplier_contact


class FakeModelProvider:
    name = "fake-model"

    def __init__(self):
        self.prompts = []

    def complete(self, prompt: str, tools=None):
        self.prompts.append(prompt)
        return {
            "reply": valid_initial_message(
                "E2E UAV Flight Controller FC-100",
                "https://supplier.test/products/fc-100",
            )
        }


def valid_initial_message(product_title: str, product_url: str) -> str:
    return (
        "Hello. I represent the purchasing department of AlphaLogisticService LLC.\n"
        f"Product: {product_title}\n"
        f"Product link: {product_url}\n"
        "Please share the current price, availability, MOQ/minimum order quantity, "
        "lead time, payment terms, and delivery/shipping terms."
    )


class ReplyModelProvider:
    name = "reply-model"

    def __init__(self, response):
        self.responses = list(response) if isinstance(response, list) else [response]
        self.prompts = []

    def complete(self, prompt: str, tools=None):
        self.prompts.append(prompt)
        if not self.responses:
            return ""
        return self.responses.pop(0)


class RecordingConnector:
    def __init__(self, result, from_address="", password=""):
        self.result = result
        self.calls = []
        self.from_address = from_address
        self.password = password

    def send(self, destination: str, *args):
        self.calls.append((destination, args))
        return self.result


def runtime_with_connectors(email_result, telegram_result):
    registry = ToolRegistry()
    registry.register(
        "email",
        RecordingConnector(
            email_result,
            from_address="agent@example.test",
            password="gmail-app-password",
        ),
    )
    registry.register("telegram", RecordingConnector(telegram_result))
    return AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)


def runtime_with_model_and_email(model, email_result):
    registry = ToolRegistry()
    registry.register(
        "email",
        RecordingConnector(
            email_result,
            from_address="agent@example.test",
            password="gmail-app-password",
        ),
    )
    return AgentRuntime(model_provider=model, tool_registry=registry)


class SupplierContactWorkerContractTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()

    def create_contact_task(self, contact_type=ContactType.EMAIL, contact_value="supplier@example.test"):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier contact"))
        contact = SupplierContact.create(contact_type, contact_value)
        product = Product(
            search_request_id=request.id,
            title="E2E UAV Flight Controller FC-100",
            product_url="https://supplier.test/products/fc-100",
            contacts=[contact],
        )
        contact.product_id = product.id
        self.repo.add_product(product)
        attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending")
        )
        task = AgentTask.create(
            AgentTaskType.SUPPLIER_CONTACT,
            {
                "productId": str(product.id),
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(attempt.id),
                "channel": contact.contact_type.value,
            },
        )
        attempt.agent_task_id = task.id
        self.repo.add_agent_task(task)
        return product, contact, attempt, task

    def test_email_success(self):
        product, contact, attempt, task = self.create_contact_task()
        runtime = runtime_with_connectors(
            ConnectorResult(success=True, external_id="email-1"),
            ConnectorResult(success=True, external_id="telegram-1"),
        )

        process_supplier_contact(self.repo, runtime, task.id)

        email_connector = runtime.tool_registry.require("email")
        self.assertEqual(1, len(email_connector.calls))
        self.assertEqual(contact.contact_value, email_connector.calls[0][0])
        self.assertIn(product.title, attempt.message_text)
        self.assertEqual("email-1", attempt.external_message_id)
        self.assertEqual(ContactAttemptStatus.SENT, attempt.status)
        self.assertEqual(AgentTaskStatus.COMPLETED, task.status)
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(1, len(messages))
        self.assertEqual(ConversationDirection.OUTBOUND, messages[0].direction)
        self.assertEqual(ConversationMessageStatus.SENT, messages[0].status)
        self.assertEqual(ContactType.EMAIL, messages[0].channel)
        self.assertIn(product.title, messages[0].subject)
        self.assertEqual(attempt.message_text, messages[0].body)
        self.assertEqual("agent@example.test", messages[0].from_address)
        self.assertEqual(contact.contact_value, messages[0].to_address)
        self.assertEqual("email-1", messages[0].external_message_id)
        self.assertEqual(1, len(runtime.model_provider.prompts))
        self.assertIn(product.title, runtime.model_provider.prompts[0])
        self.assertIn(product.product_url, runtime.model_provider.prompts[0])

    def test_telegram_success(self):
        _, contact, attempt, task = self.create_contact_task(ContactType.TELEGRAM, "@supplier_e2e_test")
        runtime = runtime_with_connectors(
            ConnectorResult(success=True, external_id="email-1"),
            ConnectorResult(success=True, external_id="telegram-1"),
        )

        process_supplier_contact(self.repo, runtime, task.id)

        telegram_connector = runtime.tool_registry.require("telegram")
        self.assertEqual(1, len(telegram_connector.calls))
        self.assertEqual(contact.contact_value, telegram_connector.calls[0][0])
        self.assertEqual("telegram-1", attempt.external_message_id)
        self.assertEqual(ContactAttemptStatus.SENT, attempt.status)

    def test_email_failure_is_persisted(self):
        product, _, attempt, task = self.create_contact_task()
        runtime = runtime_with_connectors(
            ConnectorResult(success=False, error_message="SMTP auth failed for gmail-app-password"),
            ConnectorResult(success=True, external_id="telegram-1"),
        )

        process_supplier_contact(self.repo, runtime, task.id)

        self.assertEqual(ContactAttemptStatus.FAILED, attempt.status)
        self.assertEqual(AgentTaskStatus.FAILED, task.status)
        self.assertNotIn("gmail-app-password", attempt.error_message)
        self.assertIn("***REDACTED***", attempt.error_message)
        self.assertEqual(attempt.error_message, task.error_message)
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(1, len(messages))
        self.assertEqual(ConversationMessageStatus.FAILED, messages[0].status)
        self.assertEqual(attempt.error_message, messages[0].error_message)

    def test_telegram_failure_is_persisted(self):
        _, _, attempt, task = self.create_contact_task(ContactType.TELEGRAM, "@supplier_e2e_test")
        runtime = runtime_with_connectors(
            ConnectorResult(success=True, external_id="email-1"),
            ConnectorResult(success=False, error_message="telegram unavailable"),
        )

        process_supplier_contact(self.repo, runtime, task.id)

        self.assertEqual(ContactAttemptStatus.FAILED, attempt.status)
        self.assertEqual(AgentTaskStatus.FAILED, task.status)
        self.assertEqual("telegram unavailable", attempt.error_message)

    def test_agent_conversation_reply_uses_history_and_persists_outbound_message(self):
        product, contact, first_attempt, _ = self.create_contact_task()
        inbound = self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=first_attempt.id,
                channel=ContactType.EMAIL,
                subject="Re: request",
                body="We have stock. MOQ is 10. Delivery is 7 days.",
                from_address=contact.contact_value,
                to_address="agent@example.test",
                external_message_id="gmail-inbound-1",
            )
        )
        reply_attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending")
        )
        task = AgentTask.create(
            AgentTaskType.SUPPLIER_CONTACT,
            {
                "productId": str(product.id),
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(reply_attempt.id),
                "channel": contact.contact_type.value,
                "conversationMode": "reply",
                "replyToMessageId": str(inbound.id),
            },
        )
        reply_attempt.agent_task_id = task.id
        self.repo.add_agent_task(task)
        model = ReplyModelProvider(
            f"Hello. Thank you for the stock update for {product.title}. Please share the unit price and whether the stated 7-day delivery timing is still available."
        )
        runtime = runtime_with_model_and_email(model, ConnectorResult(success=True, external_id="gmail-reply-1"))

        process_supplier_contact(self.repo, runtime, task.id)

        email_connector = runtime.tool_registry.require("email")
        self.assertEqual(1, len(email_connector.calls))
        self.assertIn(product.title, email_connector.calls[0][1][1])
        self.assertEqual(ContactAttemptStatus.SENT, reply_attempt.status)
        self.assertEqual(AgentTaskStatus.COMPLETED, task.status)
        self.assertEqual("gmail-reply-1", reply_attempt.external_message_id)
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual([ConversationDirection.INBOUND, ConversationDirection.OUTBOUND], [m.direction for m in messages])
        self.assertEqual("gmail-reply-1", messages[-1].external_message_id)
        self.assertIn("We have stock", model.prompts[0])

    def test_agent_conversation_reply_replaces_unsafe_model_output_with_second_ai_reply(self):
        product, contact, first_attempt, _ = self.create_contact_task()
        inbound = self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=first_attempt.id,
                channel=ContactType.EMAIL,
                subject="Re: request",
                body="We can ship tomorrow.",
                from_address=contact.contact_value,
                to_address="agent@example.test",
            )
        )
        reply_attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending")
        )
        task = AgentTask.create(
            AgentTaskType.SUPPLIER_CONTACT,
            {
                "productId": str(product.id),
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(reply_attempt.id),
                "channel": contact.contact_type.value,
                "conversationMode": "reply",
                "replyToMessageId": str(inbound.id),
            },
        )
        reply_attempt.agent_task_id = task.id
        self.repo.add_agent_task(task)
        model = ReplyModelProvider(
            [
                "confirmed order, we will pay today",
                (
                    "Hello. I represent the purchasing department of AlphaLogisticService LLC. "
                    f"We are reviewing preliminary terms for {product.title}; any order or payment decision requires internal approval."
                ),
            ]
        )
        runtime = runtime_with_model_and_email(model, ConnectorResult(success=True, external_id="gmail-reply-1"))

        process_supplier_contact(self.repo, runtime, task.id)

        email_connector = runtime.tool_registry.require("email")
        self.assertEqual(1, len(email_connector.calls))
        self.assertIn(product.title, email_connector.calls[0][1][1])
        self.assertIn("AlphaLogisticService LLC", email_connector.calls[0][1][1])
        self.assertNotIn("confirmed order", email_connector.calls[0][1][1].lower())
        self.assertNotIn("we will pay", email_connector.calls[0][1][1].lower())
        self.assertEqual(ContactAttemptStatus.SENT, reply_attempt.status)
        self.assertEqual(AgentTaskStatus.COMPLETED, task.status)
        self.assertEqual(2, len(model.prompts))

    def test_agent_conversation_reply_answers_supplier_company_question_contextually(self):
        product, contact, first_attempt, _ = self.create_contact_task()
        inbound = self.repo.add_conversation_message(
            ConversationMessage.create_inbound(
                product_id=product.id,
                supplier_contact_id=contact.id,
                contact_attempt_id=first_attempt.id,
                channel=ContactType.EMAIL,
                subject="Re: request",
                body="Здравствуйте, какую компанию вы представляете?",
                from_address=contact.contact_value,
                to_address="agent@example.test",
            )
        )
        reply_attempt = self.repo.add_contact_attempt(
            ContactAttempt.create(product.id, contact.id, contact.contact_type, "pending")
        )
        task = AgentTask.create(
            AgentTaskType.SUPPLIER_CONTACT,
            {
                "productId": str(product.id),
                "supplierContactId": str(contact.id),
                "contactAttemptId": str(reply_attempt.id),
                "channel": contact.contact_type.value,
                "conversationMode": "reply",
                "replyToMessageId": str(inbound.id),
            },
        )
        reply_attempt.agent_task_id = task.id
        self.repo.add_agent_task(task)
        model = ReplyModelProvider("Здравствуйте. Я представляю отдел закупок нашей компании. Уточняю условия поставки по указанному товару.")
        runtime = runtime_with_model_and_email(model, ConnectorResult(success=True, external_id="gmail-reply-1"))

        process_supplier_contact(self.repo, runtime, task.id)

        self.assertEqual(ContactAttemptStatus.SENT, reply_attempt.status)
        email_connector = runtime.tool_registry.require("email")
        self.assertIn("отдел закупок", email_connector.calls[0][1][1].lower())
        self.assertNotIn("актуальную цену", email_connector.calls[0][1][1].lower())


if __name__ == "__main__":
    unittest.main()
