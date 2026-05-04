import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

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
    ProductValidationError,
    SearchRequest,
    SearchRequestStatus,
    SupplierContact,
    validate_product_payload,
)
from backend.app.repositories import InMemoryRepository


class SearchRequestValidationTest(unittest.TestCase):
    def test_search_query_validation(self):
        with self.assertRaises(ValueError):
            SearchRequest.create("")
        with self.assertRaises(ValueError):
            SearchRequest.create("ab")
        with self.assertRaises(ValueError):
            SearchRequest.create("x" * 1001)

        request = SearchRequest.create("E2E UAV Flight Controller")
        self.assertEqual("E2E UAV Flight Controller", request.query_text)
        self.assertEqual(SearchRequestStatus.QUEUED, request.status)
        self.assertEqual(5, request.max_results)

    def test_search_result_limit_validation(self):
        self.assertEqual(12, SearchRequest.create("E2E UAV Flight Controller", max_results=12).max_results)

        for value in [0, 51]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    SearchRequest.create("E2E UAV Flight Controller", max_results=value)

    def test_invalid_terminal_transition_is_rejected(self):
        request = SearchRequest.create("E2E UAV Flight Controller")
        request.transition_to(SearchRequestStatus.RUNNING)
        request.transition_to(SearchRequestStatus.COMPLETED)

        with self.assertRaises(ValueError):
            request.transition_to(SearchRequestStatus.RUNNING)


class ProductValidationTest(unittest.TestCase):
    def test_valid_product_with_nullable_price(self):
        result = validate_product_payload(
            {
                "title": "E2E Rack Workstation RW-500",
                "productUrl": "https://supplier.test/products/rw-500",
                "price": None,
                "currency": None,
                "contacts": [{"type": "email", "value": "supplier@example.test"}],
            }
        )

        self.assertIsNone(result.product.price)
        self.assertIsNone(result.product.currency)
        self.assertEqual([], result.errors)

    def test_invalid_product_is_skipped_with_reason(self):
        result = validate_product_payload(
            {
                "title": "",
                "productUrl": "not-a-url",
                "contacts": [{"type": "email", "value": "not-an-email"}],
            }
        )

        self.assertIsNone(result.product)
        self.assertIn("title is required", result.errors)
        self.assertIn("productUrl must be a valid URL", result.errors)
        self.assertIn("contact[0]: email contact must be valid", result.errors)


class SupplierContactValidationTest(unittest.TestCase):
    def test_email_and_telegram_contacts(self):
        email = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        telegram_handle = SupplierContact.create(ContactType.TELEGRAM, "@supplier_e2e_test")
        telegram_url = SupplierContact.create(ContactType.TELEGRAM, "https://t.me/supplier_e2e_test")

        self.assertEqual("supplier@example.test", email.contact_value)
        self.assertEqual("@supplier_e2e_test", telegram_handle.contact_value)
        self.assertEqual("https://t.me/supplier_e2e_test", telegram_url.contact_value)

    def test_invalid_contacts_are_rejected(self):
        with self.assertRaises(ValueError):
            SupplierContact.create(ContactType.EMAIL, "not-an-email")
        with self.assertRaises(ValueError):
            SupplierContact.create(ContactType.TELEGRAM, "supplier without marker")


class ContactAttemptPolicyTest(unittest.TestCase):
    def test_active_attempt_policy(self):
        product_id = uuid4()
        contact_id = uuid4()
        active = ContactAttempt.create(product_id, contact_id, ContactType.EMAIL, "message")
        sent = ContactAttempt.create(product_id, contact_id, ContactType.EMAIL, "message")
        sent.transition_to(ContactAttemptStatus.RUNNING)
        sent.transition_to(ContactAttemptStatus.SENT)

        self.assertTrue(ContactAttempt.has_active([active, sent]))
        active.transition_to(ContactAttemptStatus.RUNNING)
        active.transition_to(ContactAttemptStatus.FAILED)
        self.assertFalse(ContactAttempt.has_active([active, sent]))


class ConversationMessageContractTest(unittest.TestCase):
    def test_outbound_message_defaults_to_queued(self):
        product_id = uuid4()
        contact_id = uuid4()
        attempt_id = uuid4()

        message = ConversationMessage.create_outbound(
            product_id=product_id,
            supplier_contact_id=contact_id,
            contact_attempt_id=attempt_id,
            channel=ContactType.EMAIL,
            subject="Запрос по товару",
            body="Здравствуйте, уточните условия поставки.",
            from_address="agent@example.test",
            to_address="supplier@example.test",
        )

        self.assertEqual(product_id, message.product_id)
        self.assertEqual(contact_id, message.supplier_contact_id)
        self.assertEqual(attempt_id, message.contact_attempt_id)
        self.assertEqual(ConversationDirection.OUTBOUND, message.direction)
        self.assertEqual(ConversationMessageStatus.QUEUED, message.status)
        self.assertEqual(ContactType.EMAIL, message.channel)
        self.assertEqual("supplier@example.test", message.to_address)

    def test_message_can_be_marked_sent_or_failed(self):
        message = ConversationMessage.create_outbound(
            product_id=uuid4(),
            supplier_contact_id=uuid4(),
            contact_attempt_id=uuid4(),
            channel="email",
            subject="Запрос",
            body="Текст запроса",
            from_address="agent@example.test",
            to_address="supplier@example.test",
        )

        provider_timestamp = datetime(2026, 5, 2, 15, 55, 53, tzinfo=timezone.utc)
        message.mark_sent("gmail-message-id", provider_timestamp=provider_timestamp)
        self.assertEqual(ConversationMessageStatus.SENT, message.status)
        self.assertEqual("gmail-message-id", message.external_message_id)
        self.assertIsNotNone(message.sent_at)
        self.assertEqual(provider_timestamp, message.provider_timestamp)

        failed = ConversationMessage.create_outbound(
            product_id=uuid4(),
            supplier_contact_id=uuid4(),
            contact_attempt_id=uuid4(),
            channel="email",
            subject="Запрос",
            body="Текст запроса",
            from_address="agent@example.test",
            to_address="supplier@example.test",
        )
        failed.mark_failed("smtp unavailable")
        self.assertEqual(ConversationMessageStatus.FAILED, failed.status)
        self.assertEqual("smtp unavailable", failed.error_message)

    def test_inbound_message_defaults_to_received(self):
        product_id = uuid4()
        contact_id = uuid4()
        attempt_id = uuid4()

        message = ConversationMessage.create_inbound(
            product_id=product_id,
            supplier_contact_id=contact_id,
            contact_attempt_id=attempt_id,
            channel=ContactType.EMAIL,
            subject="Re: Product request",
            body="We have stock. MOQ is 10 units.",
            from_address="supplier@example.test",
            to_address="agent@example.test",
            external_message_id="gmail-inbound-1",
            provider_timestamp=datetime(2026, 5, 2, 15, 55, 53, tzinfo=timezone.utc),
        )

        self.assertEqual(product_id, message.product_id)
        self.assertEqual(contact_id, message.supplier_contact_id)
        self.assertEqual(attempt_id, message.contact_attempt_id)
        self.assertEqual(ConversationDirection.INBOUND, message.direction)
        self.assertEqual(ConversationMessageStatus.RECEIVED, message.status)
        self.assertEqual(ContactType.EMAIL, message.channel)
        self.assertEqual("supplier@example.test", message.from_address)
        self.assertEqual("gmail-inbound-1", message.external_message_id)
        self.assertEqual("2026-05-02T15:55:53+00:00", message.provider_timestamp.isoformat())
        self.assertFalse(message.requires_user_approval)

        message.mark_requires_user_approval("Supplier asks for order approval")
        self.assertTrue(message.requires_user_approval)
        self.assertEqual("Supplier asks for order approval", message.approval_reason)

    def test_empty_body_is_rejected(self):
        with self.assertRaises(ValueError):
            ConversationMessage.create_outbound(
                product_id=uuid4(),
                supplier_contact_id=uuid4(),
                contact_attempt_id=uuid4(),
                channel=ContactType.EMAIL,
                subject="Запрос",
                body=" ",
                from_address="agent@example.test",
                to_address="supplier@example.test",
            )


class AgentTaskValidationTest(unittest.TestCase):
    def test_agent_task_status_transitions(self):
        task = AgentTask.create(AgentTaskType.PRODUCT_SEARCH, {"queryText": "E2E"})
        self.assertEqual(AgentTaskStatus.QUEUED, task.status)

        task.transition_to(AgentTaskStatus.RUNNING)
        task.transition_to(AgentTaskStatus.COMPLETED)

        with self.assertRaises(ValueError):
            task.transition_to(AgentTaskStatus.RUNNING)


class RepositoryContractTest(unittest.TestCase):
    def test_repository_stores_and_retrieves_entities(self):
        repo = InMemoryRepository()
        request = repo.add_search_request(SearchRequest.create("E2E UAV Flight Controller"))
        task = repo.add_agent_task(AgentTask.create(AgentTaskType.PRODUCT_SEARCH, {"searchRequestId": str(request.id)}))

        self.assertEqual(request, repo.get_search_request(request.id))
        self.assertEqual(task, repo.get_agent_task(task.id))
        self.assertEqual([request], repo.list_search_requests())

    def test_repository_stores_conversation_messages_by_product(self):
        repo = InMemoryRepository()
        product_id = uuid4()
        contact_id = uuid4()
        attempt_id = uuid4()
        first = ConversationMessage.create_outbound(
            product_id=product_id,
            supplier_contact_id=contact_id,
            contact_attempt_id=attempt_id,
            channel=ContactType.EMAIL,
            subject="Первое письмо",
            body="Первое сообщение",
            from_address="agent@example.test",
            to_address="supplier@example.test",
        )
        second = ConversationMessage.create_outbound(
            product_id=product_id,
            supplier_contact_id=contact_id,
            contact_attempt_id=attempt_id,
            channel=ContactType.EMAIL,
            subject="Второе письмо",
            body="Второе сообщение",
            from_address="agent@example.test",
            to_address="supplier@example.test",
        )
        second.created_at = first.created_at + timedelta(seconds=1)

        repo.add_conversation_message(second)
        repo.add_conversation_message(first)

        self.assertEqual([first, second], repo.list_conversation_messages_for_product(product_id))
        self.assertEqual([], repo.list_conversation_messages_for_product(uuid4()))


if __name__ == "__main__":
    unittest.main()
