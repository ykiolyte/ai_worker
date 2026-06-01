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
    ContractDraft,
    ContractDraftStatus,
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
from backend.app.sourcing import (
    ProductCandidate,
    ProductFitEvaluator,
    ProductNormalizer,
    SourcingSearchOutputSchema,
)


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

    def test_search_request_has_sourcing_defaults(self):
        request = SearchRequest.create("ПК, вычислительные компьютеры, ноутбуки")

        self.assertEqual({}, request.normalized_intent)
        self.assertEqual([], request.missing_fields)
        self.assertEqual([], request.clarifying_questions)
        self.assertEqual([], request.common_filters)
        self.assertEqual([], request.product_attributes)
        self.assertEqual({}, request.sourcing_guidance)
        self.assertEqual(0, request.suppliers_count)

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

    def test_valid_extended_sourcing_product(self):
        result = validate_product_payload(
            {
                "title": "Industrial Fanless Mini PC",
                "productUrl": "https://supplier.test/products/mini-pc",
                "priceRange": "Negotiable",
                "moq": "10 Pieces",
                "fitScore": 0.86,
                "fitSummary": "Matches industrial computing request.",
                "matchedRequirements": [
                    {"requirement": "computer supplier", "evidence": "Title mentions Mini PC"}
                ],
                "missingRequirements": ["No certification evidence found"],
                "supplierBadges": ["Manufacturer", "Customization Available"],
                "supplierCountry": "China",
                "supplierCity": "Shenzhen",
                "isVerifiedSupplier": True,
                "supportsCustomization": True,
                "sampleAvailable": True,
                "contacts": [{"type": "email", "value": "supplier@example.test"}],
            }
        )

        self.assertEqual([], result.errors)
        self.assertEqual("Negotiable", result.product.price_range)
        self.assertEqual("10 Pieces", result.product.moq)
        self.assertEqual(Decimal("0.86"), result.product.fit_score)
        self.assertEqual(["Manufacturer", "Customization Available"], result.product.supplier_badges)
        self.assertTrue(result.product.is_verified_supplier)

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

    def test_invalid_extended_sourcing_product_is_rejected(self):
        result = validate_product_payload(
            {
                "title": "Industrial Fanless Mini PC",
                "productUrl": "https://supplier.test/products/mini-pc",
                "fitScore": 1.4,
                "matchedRequirements": [{"requirement": "computer supplier"}],
                "images": ["not-a-url"],
                "contacts": [{"type": "email", "value": "supplier@example.test"}],
            }
        )

        self.assertIsNone(result.product)
        self.assertIn("fitScore must be between 0 and 1", result.errors)
        self.assertIn("matchedRequirements[0] must include requirement and evidence", result.errors)
        self.assertIn("images[0] must be a valid URL", result.errors)


class SourcingOutputValidationTest(unittest.TestCase):
    def test_sourcing_search_output_schema_accepts_ai_like_payload(self):
        output = SourcingSearchOutputSchema.model_validate(
            {
                "normalizedIntent": {
                    "rawQuery": "ПК, вычислительные компьютеры, ноутбуки",
                    "productCategory": "computers and computing equipment",
                    "supplierPreference": "manufacturer_first",
                },
                "missingFields": ["quantity"],
                "clarifyingQuestions": ["Какой объём закупки планируется?"],
                "commonFilters": ["Manufacturer"],
                "productAttributes": [{"name": "Processor", "values": ["Intel", "AMD"]}],
                "products": [
                    {
                        "title": "Industrial Fanless Mini PC",
                        "productUrl": "https://supplier.test/products/mini-pc",
                        "priceRange": "Negotiable",
                        "moq": "10 Pieces",
                        "fitScore": 0.8,
                        "matchedRequirements": [
                            {"requirement": "computer supplier", "evidence": "Title mentions Mini PC"}
                        ],
                        "contacts": [{"type": "email", "value": "supplier@example.test"}],
                    }
                ],
                "sourcingGuidance": {"riskWarnings": ["Verify supplier identity"]},
            }
        )

        self.assertEqual("manufacturer_first", output.normalized_intent.supplier_preference)
        self.assertEqual(1, len(output.products))

    def test_sourcing_search_output_supports_legacy_products_shape(self):
        output = SourcingSearchOutputSchema.from_agent_payload(
            {
                "products": [
                    {
                        "title": "Legacy product",
                        "productUrl": "https://supplier.test/products/legacy",
                        "contacts": [{"type": "email", "value": "supplier@example.test"}],
                    }
                ]
            }
        )

        self.assertEqual({}, output.normalized_intent.model_dump(exclude_none=True, by_alias=True))
        self.assertEqual("Legacy product", output.products[0].title)

    def test_product_normalizer_and_fit_evaluator_do_not_invent_claims(self):
        candidate = ProductCandidate(
            title="Industrial Fanless Mini PC Manufacturer",
            product_url="https://supplier.test/products/mini-pc",
            supplier_name="Example Technology Co., Ltd.",
            price_text="Negotiable",
            moq_text="10 Pieces",
            supplier_badges=["Manufacturer", "Customization Available"],
            source_url="https://supplier.test/search?q=mini+pc",
            source_domain="supplier.test",
            extraction_method="public_page",
            confidence=0.75,
        )
        intent = {"supplierPreference": "manufacturer_first", "mustHave": ["mini pc"], "certifications": ["CE"]}

        normalized = ProductNormalizer().normalize(candidate)
        evaluated = ProductFitEvaluator().evaluate(intent, normalized)

        self.assertEqual("Negotiable", normalized["priceRange"])
        self.assertEqual("10 Pieces", normalized["moq"])
        self.assertTrue(evaluated["fitScore"] > 0)
        self.assertIn("CE", " ".join(evaluated["missingRequirements"]))
        self.assertTrue(all(item["evidence"] for item in evaluated["matchedRequirements"]))


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


class ContractDraftPolicyTest(unittest.TestCase):
    def test_contract_draft_status_transitions_and_download_policy(self):
        draft = ContractDraft.create(product_id=uuid4(), supplier_contact_id=uuid4(), supplier_name="Supplier Test")

        self.assertEqual(ContractDraftStatus.QUEUED, draft.status)
        self.assertFalse(draft.is_downloadable())
        draft.transition_to(ContractDraftStatus.RUNNING)
        draft.mark_ready("DRAFT CONTRACT\nSupplier: Supplier Test", {"product": "FC-100"})

        self.assertEqual(ContractDraftStatus.READY, draft.status)
        self.assertTrue(draft.is_downloadable())
        self.assertIn("draft", draft.file_name)

    def test_contract_draft_rejects_unsafe_commitment_text(self):
        draft = ContractDraft.create(product_id=uuid4(), supplier_contact_id=uuid4(), supplier_name="Supplier Test")

        draft.transition_to(ContractDraftStatus.RUNNING)
        with self.assertRaises(ValueError):
            draft.mark_ready("DRAFT CONTRACT\nWe confirm the order and will pay now.", {})


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

    def test_contract_repository_is_separate_from_sourcing_repository(self):
        repo = InMemoryRepository()
        draft = ContractDraft.create(product_id=uuid4(), supplier_contact_id=uuid4(), supplier_name="Supplier Test")

        repo.contracts.add_contract_draft(draft)

        self.assertEqual(draft, repo.contracts.get_contract_draft(draft.id))
        self.assertEqual([], repo.list_attempts_for_product(draft.product_id))
        self.assertEqual([], repo.list_conversation_messages_for_product(draft.product_id))


if __name__ == "__main__":
    unittest.main()
