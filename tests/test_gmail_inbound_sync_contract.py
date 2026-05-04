import unittest
from datetime import datetime, timezone

from backend.app.agent import AgentRuntime, ConnectorResult, ToolRegistry
from backend.app.connectors import InboundEmailMessage
from backend.app.domain import ContactAttempt, ContactAttemptStatus, ContactType, ConversationMessage, Product, SearchRequest, SupplierContact
from backend.app.repositories import InMemoryRepository
from backend.app.workers import run_gmail_inbound_sync_loop, sync_gmail_inbound_messages


class GmailInboundConnector:
    def __init__(self, messages):
        self.messages = messages
        self.calls = []

    def fetch_unseen(self, limit=20):
        self.calls.append(limit)
        return type("Result", (), {"success": True, "payload": {"messages": self.messages}, "error_message": None})()


class RecordingEmailConnector:
    from_address = "agent@example.test"
    password = ""

    def __init__(self):
        self.calls = []

    def send(self, destination: str, subject: str, body: str):
        self.calls.append((destination, subject, body))
        return ConnectorResult(success=True, external_id="auto-reply-1")


class ModelProvider:
    name = "test-model"

    def complete(self, prompt: str, tools=None):
        return {
            "text": (
                "Здравствуйте. Наше направление - логистические услуги для интернет-магазинов и малого бизнеса. "
                "О вашем контакте узнали из карточки поставщика по этому товару."
            )
        }


class UnsafeModelProvider:
    name = "unsafe-model"

    def __init__(self):
        self.prompts = []
        self.calls = 0

    def complete(self, prompt: str, tools=None):
        self.prompts.append(prompt)
        self.calls += 1
        if self.calls == 1:
            return {"text": "confirmed order, we will pay today"}
        return {
            "text": (
                "Hello. I represent the purchasing department of AlphaLogisticService LLC. "
                "We are reviewing preliminary terms for E2E UAV Flight Controller FC-100; any order or payment decision requires internal approval."
            )
        }


class CompanyDetailsModelProvider:
    name = "company-details-model"

    def complete(self, prompt: str, tools=None):
        return {
            "text": (
                "Hello. Company details: AlphaLogisticService LLC, tax id 7703456789, "
                "KPP 770301001, OGRN 1237700309876."
            )
        }


class RaisingEmailConnector:
    from_address = "agent@example.test"
    password = ""

    def send(self, destination: str, subject: str, body: str):
        raise RuntimeError("SMTP transport disconnected")


def runtime_with_email(email, model=None):
    registry = ToolRegistry()
    registry.register("email", email)
    return AgentRuntime(model_provider=model or ModelProvider(), tool_registry=registry)


class GmailInboundSyncContractTest(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()

    def create_product_with_email_contact(self):
        request = self.repo.add_search_request(SearchRequest.create("E2E supplier reply"))
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
        return product, contact, attempt

    def test_sync_matches_inbound_email_to_supplier_contact(self):
        product, contact, attempt = self.create_product_with_email_contact()
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-inbound-1@example.test>",
                    subject="Re: Product request",
                    body="We have stock. MOQ is 10 units.",
                    from_address="Supplier <supplier@example.test>",
                    to_address="agent@example.test",
                    provider_timestamp=datetime(2026, 5, 2, 15, 55, 53, tzinfo=timezone.utc),
                )
            ]
        )

        result = sync_gmail_inbound_messages(self.repo, connector, limit=10)

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 0}, result)
        self.assertEqual([10], connector.calls)
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(1, len(messages))
        self.assertEqual("inbound", messages[0].direction.value)
        self.assertEqual(contact.id, messages[0].supplier_contact_id)
        self.assertEqual(attempt.id, messages[0].contact_attempt_id)
        self.assertEqual("<gmail-inbound-1@example.test>", messages[0].external_message_id)
        self.assertEqual("2026-05-02T15:55:53+00:00", messages[0].provider_timestamp.isoformat())
        self.assertIn("MOQ is 10", messages[0].body)

    def test_sync_deduplicates_by_external_message_id(self):
        product, _, _ = self.create_product_with_email_contact()
        inbound = InboundEmailMessage(
            external_id="<gmail-inbound-1@example.test>",
            subject="Re: Product request",
            body="We have stock. MOQ is 10 units.",
            from_address="supplier@example.test",
            to_address="agent@example.test",
        )
        connector = GmailInboundConnector([inbound, inbound])

        first = sync_gmail_inbound_messages(self.repo, connector)
        second = sync_gmail_inbound_messages(self.repo, connector)

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 1, "autoRepliesSent": 0}, first)
        self.assertEqual({"messagesCreated": 0, "messagesSkipped": 2, "autoRepliesSent": 0}, second)
        self.assertEqual(1, len(self.repo.list_conversation_messages_for_product(product.id)))

    def test_sync_matches_reply_headers_to_existing_outbound_message(self):
        product, contact, attempt = self.create_product_with_email_contact()
        outbound = ConversationMessage.create_outbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=attempt.id,
            channel=ContactType.EMAIL,
            subject="Product request",
            body="Initial request",
            from_address="agent@example.test",
            to_address=contact.contact_value,
        )
        outbound.mark_sent("<gmail-outbound-1@example.test>")
        self.repo.add_conversation_message(outbound)
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-inbound-2@example.test>",
                    subject="Re: Product request",
                    body="Price is 120 USD.",
                    from_address="sales-team@example.test",
                    to_address="agent@example.test",
                    in_reply_to="<gmail-outbound-1@example.test>",
                    references="<gmail-outbound-1@example.test>",
                )
            ]
        )

        result = sync_gmail_inbound_messages(self.repo, connector)

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 0}, result)
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(["outbound", "inbound"], [message.direction.value for message in messages])
        self.assertEqual(contact.id, messages[-1].supplier_contact_id)

    def test_sync_marks_supplier_business_question_for_user_approval(self):
        product, _, _ = self.create_product_with_email_contact()
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-inbound-question@example.test>",
                    subject="Re: Product request",
                    body="Do you want to place an order now?",
                    from_address="supplier@example.test",
                    to_address="agent@example.test",
                )
            ]
        )

        result = sync_gmail_inbound_messages(self.repo, connector)

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 0}, result)
        message = self.repo.list_conversation_messages_for_product(product.id)[0]
        self.assertTrue(message.requires_user_approval)
        self.assertIn("approval", message.approval_reason.lower())

    def test_sync_auto_replies_even_when_approval_mode_is_requested(self):
        product, _, _ = self.create_product_with_email_contact()
        email = RecordingEmailConnector()
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-inbound-approval-enabled@example.test>",
                    subject="Re: Product request",
                    body="Опишите ваше направление работы и откуда вы о нас узнали?",
                    from_address="supplier@example.test",
                    to_address="agent@example.test",
                )
            ]
        )

        result = sync_gmail_inbound_messages(
            self.repo,
            connector,
            runtime=runtime_with_email(email),
            require_ai_reply_approval=True,
        )

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 1}, result)
        self.assertEqual(1, len(email.calls))
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(["inbound", "outbound"], [message.direction.value for message in messages])
        self.assertFalse(messages[0].requires_user_approval)

    def test_sync_uses_second_ai_reply_when_model_reply_is_unsafe(self):
        product, _, _ = self.create_product_with_email_contact()
        email = RecordingEmailConnector()
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-inbound-unsafe-model@example.test>",
                    subject="Re: Product request",
                    body="Can you confirm the order and payment today?",
                    from_address="supplier@example.test",
                    to_address="agent@example.test",
                )
            ]
        )

        model = UnsafeModelProvider()
        result = sync_gmail_inbound_messages(
            self.repo,
            connector,
            runtime=runtime_with_email(email, model),
            require_ai_reply_approval=True,
        )

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 1}, result)
        self.assertEqual(1, len(email.calls))
        self.assertIn(product.title, email.calls[0][2])
        self.assertIn("AlphaLogisticService LLC", email.calls[0][2])
        self.assertNotIn("confirmed order", email.calls[0][2].lower())
        self.assertNotIn("we will pay", email.calls[0][2].lower())
        self.assertEqual(2, len(model.prompts))

    def test_sync_marks_auto_reply_attempt_failed_when_connector_raises(self):
        product, _, _ = self.create_product_with_email_contact()
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-inbound-send-error@example.test>",
                    subject="Re: Product request",
                    body="Please send your company details.",
                    from_address="supplier@example.test",
                    to_address="agent@example.test",
                )
            ]
        )

        result = sync_gmail_inbound_messages(
            self.repo,
            connector,
            runtime=runtime_with_email(RaisingEmailConnector(), CompanyDetailsModelProvider()),
            require_ai_reply_approval=False,
        )

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 0}, result)
        attempts = self.repo.list_attempts_for_product(product.id)
        self.assertFalse(ContactAttempt.has_active(attempts))
        self.assertEqual(ContactAttemptStatus.FAILED, attempts[-1].status)
        self.assertIn("SMTP transport disconnected", attempts[-1].error_message)

    def test_sync_auto_replies_with_ai_when_setting_disabled(self):
        product, _, _ = self.create_product_with_email_contact()
        email = RecordingEmailConnector()
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-inbound-link-question@example.test>",
                    subject="Re: Product request",
                    body="Which product link are you asking about?",
                    from_address="supplier@example.test",
                    to_address="agent@example.test",
                )
            ]
        )

        result = sync_gmail_inbound_messages(
            self.repo,
            connector,
            runtime=runtime_with_email(email),
            require_ai_reply_approval=False,
        )

        self.assertEqual({"messagesCreated": 1, "messagesSkipped": 0, "autoRepliesSent": 1}, result)
        self.assertEqual(1, len(email.calls))
        self.assertIn("логистические услуги", email.calls[0][2])
        self.assertNotIn("Please share the current price", email.calls[0][2])
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(["inbound", "outbound"], [message.direction.value for message in messages])

    def test_background_gmail_sync_loop_auto_replies_without_page_refresh(self):
        product, _, _ = self.create_product_with_email_contact()
        email = RecordingEmailConnector()
        connector = GmailInboundConnector(
            [
                InboundEmailMessage(
                    external_id="<gmail-background-inbound@example.test>",
                    subject="Re: Product request",
                    body="Опишите вашу компанию.",
                    from_address="supplier@example.test",
                    to_address="agent@example.test",
                )
            ]
        )

        ticks = run_gmail_inbound_sync_loop(
            self.repo,
            runtime_with_email(email),
            connector,
            limit=20,
            poll_interval_seconds=0,
            max_ticks=1,
        )

        self.assertEqual(1, ticks)
        self.assertEqual(1, len(email.calls))
        messages = self.repo.list_conversation_messages_for_product(product.id)
        self.assertEqual(["inbound", "outbound"], [message.direction.value for message in messages])


if __name__ == "__main__":
    unittest.main()
