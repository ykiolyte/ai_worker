import unittest

from backend.app.agent import (
    AgentRuntime,
    ConnectorResult,
    SafeMessagePolicy,
    ToolRegistry,
    generate_supplier_reply,
    generate_supplier_message,
    validate_agent_product_output,
)
from backend.app.domain import ContactType, ConversationMessage, Product, SupplierContact


class FakeModelProvider:
    name = "fake-model"

    def complete(self, prompt: str, tools=None):
        return {
            "text": "Здравствуйте. Мы представляем логистического оператора и уточняем условия поставки по указанному товару.",
            "tools": tools or [],
        }


class SequenceModelProvider:
    name = "sequence-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete(self, prompt: str, tools=None):
        self.prompts.append(prompt)
        if not self.responses:
            return {"text": ""}
        return self.responses.pop(0)


class FakeBrowserConnector:
    def research(self, query_text: str):
        return ConnectorResult(success=True, payload={"queryText": query_text})


class FakeEmailConnector:
    def send(self, to: str, subject: str, body: str):
        return ConnectorResult(success=True, external_id="email-1")


class FakeTelegramConnector:
    def send(self, chat: str, body: str):
        return ConnectorResult(success=True, external_id="telegram-1")


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


class AgentRuntimeContractTest(unittest.TestCase):
    def test_tool_registry_resolves_connectors(self):
        registry = ToolRegistry()
        browser = FakeBrowserConnector()
        email = FakeEmailConnector()
        telegram = FakeTelegramConnector()

        registry.register("browser_mcp", browser)
        registry.register("email", email)
        registry.register("telegram", telegram)

        self.assertIs(browser, registry.require("browser_mcp"))
        self.assertIs(email, registry.require("email"))
        self.assertIs(telegram, registry.require("telegram"))

    def test_agent_runtime_holds_model_and_tools(self):
        registry = ToolRegistry()
        registry.register("browser_mcp", FakeBrowserConnector())
        runtime = AgentRuntime(model_provider=FakeModelProvider(), tool_registry=registry)

        self.assertEqual("fake-model", runtime.model_provider.name)
        self.assertIsInstance(runtime.tool_registry.require("browser_mcp"), FakeBrowserConnector)

    def test_structured_product_output_validation(self):
        output = validate_agent_product_output(
            {
                "products": [
                    {
                        "title": "E2E UAV Flight Controller FC-100",
                        "productUrl": "https://supplier.test/products/fc-100",
                        "price": "120.00",
                        "currency": "USD",
                        "contacts": [{"type": "email", "value": "supplier@example.test"}],
                    },
                    {
                        "title": "",
                        "productUrl": "not-a-url",
                        "contacts": [{"type": "email", "value": "not-an-email"}],
                    },
                ]
            }
        )

        self.assertEqual(1, len(output.products))
        self.assertEqual(1, len(output.skipped))
        self.assertEqual(1, output.products_created)
        self.assertEqual(1, output.products_skipped)
        self.assertIn("title is required", output.skipped[0]["errors"])

    def test_safe_supplier_message_policy(self):
        model = SequenceModelProvider([{"reply": valid_initial_message()}])
        message = generate_supplier_message(
            model,
            "E2E UAV Flight Controller FC-100",
            "https://supplier.test/products/fc-100",
        )

        errors = SafeMessagePolicy.validate(message)
        self.assertEqual([], errors)
        self.assertIn("E2E UAV Flight Controller FC-100", message)
        self.assertIn("https://supplier.test/products/fc-100", message)
        self.assertEqual(1, len(model.prompts))
        self.assertIn("docs/ooo.md", model.prompts[0])
        self.assertIn("Product link: https://supplier.test/products/fc-100", model.prompts[0])

        unsafe = "confirmed order, we will pay today"
        self.assertNotEqual([], SafeMessagePolicy.validate(unsafe))

    def test_generate_supplier_message_uses_second_ai_call_for_empty_model_output(self):
        model = SequenceModelProvider(
            [
                {"text": ""},
                {"reply": valid_initial_message()},
            ]
        )

        message = generate_supplier_message(
            model,
            "E2E UAV Flight Controller FC-100",
            "https://supplier.test/products/fc-100",
        )

        self.assertEqual([], SafeMessagePolicy.validate(message))
        self.assertEqual(2, len(model.prompts))
        self.assertIn("Previous model output was unusable", model.prompts[1])

    def test_generate_supplier_message_requires_exact_product_title(self):
        model = SequenceModelProvider(
            [
                {
                    "reply": (
                        "Hello. Product link: https://supplier.test/products/fc-100. "
                        "Please share the current price, availability, MOQ/minimum order quantity, "
                        "lead time, payment terms, and delivery/shipping terms."
                    )
                },
                {"reply": valid_initial_message()},
            ]
        )

        message = generate_supplier_message(
            model,
            "E2E UAV Flight Controller FC-100",
            "https://supplier.test/products/fc-100",
        )

        self.assertIn("E2E UAV Flight Controller FC-100", message)
        self.assertEqual(2, len(model.prompts))
        self.assertIn("missing exact product title", model.prompts[1])

    def test_generate_supplier_message_fails_when_model_correction_is_unusable(self):
        model = SequenceModelProvider([{"text": ""}, {"text": "ok"}])

        with self.assertRaises(RuntimeError):
            generate_supplier_message(
                model,
                "E2E UAV Flight Controller FC-100",
                "https://supplier.test/products/fc-100",
            )

        self.assertEqual(2, len(model.prompts))

    def test_follow_up_policy_allows_contextual_employee_reply_without_initial_topics(self):
        reply = "Здравствуйте. Я представляю отдел закупок нашей компании и уточняю условия по указанному товару."

        self.assertEqual([], SafeMessagePolicy.validate_follow_up(reply))

    def test_generate_supplier_reply_does_not_fallback_to_initial_template(self):
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            title="Демо-карточка для презентации",
            product_url="https://demo.local/product",
            contacts=[contact],
        )
        contact.product_id = product.id
        inbound = ConversationMessage.create_inbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=contact.id,
            channel=ContactType.EMAIL,
            subject="Re: request",
            body="Здравствуйте, какую компанию вы представляете?",
            from_address=contact.contact_value,
            to_address="agent@example.test",
        )

        class ContextModel:
            name = "context-model"

            def __init__(self):
                self.prompts = []

            def complete(self, prompt: str, tools=None):
                self.prompts.append(prompt)
                return {
                    "text": (
                        "Здравствуйте. Наша компания — логистический оператор для интернет-магазинов и малого бизнеса. "
                        "Сейчас уточняем условия поставки по демо-карточке."
                    )
                }

        model = ContextModel()
        reply = generate_supplier_reply(model, product, [inbound], language="ru", style="formal")

        self.assertIn("логистический оператор", reply.lower())
        self.assertNotIn("актуальную цену", reply.lower())
        self.assertIn("какую компанию", model.prompts[0])
        self.assertIn(product.product_url, model.prompts[0])
        self.assertIn("Общество с ограниченной ответственностью «АльфаЛогистикСервис»", model.prompts[0])
        self.assertIn("ООО «АЛС»", model.prompts[0])

    def test_generate_supplier_reply_answers_product_link_question_from_context(self):
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            title="E2E CNC Controller",
            product_url="https://supplier.test/products/cnc-200",
            contacts=[contact],
        )
        contact.product_id = product.id
        inbound = ConversationMessage.create_inbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=contact.id,
            channel=ContactType.EMAIL,
            subject="Re: request",
            body="Здравствуйте, по какому товару нужна информация? Пришлите ссылку.",
            from_address=contact.contact_value,
            to_address="agent@example.test",
        )

        class LinkModel:
            name = "link-model"

            def complete(self, prompt: str, tools=None):
                return {
                    "text": (
                        "Здравствуйте. Нас интересует E2E CNC Controller. "
                        "Ссылка на товар: https://supplier.test/products/cnc-200."
                    )
                }

        reply = generate_supplier_reply(LinkModel(), product, [inbound], language="ru", style="formal")

        self.assertIn(product.title, reply)
        self.assertIn(product.product_url, reply)
        self.assertNotIn("актуальную цену", reply.lower())

    def test_generate_supplier_reply_answers_quantity_question_without_order_commitment(self):
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            title="E2E Servo Drive",
            product_url="https://supplier.test/products/servo-drive",
            contacts=[contact],
        )
        contact.product_id = product.id
        inbound = ConversationMessage.create_inbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=contact.id,
            channel=ContactType.EMAIL,
            subject="Re: request",
            body="Какое количество вам нужно?",
            from_address=contact.contact_value,
            to_address="agent@example.test",
        )

        class QuantityModel:
            name = "quantity-model"

            def complete(self, prompt: str, tools=None):
                return {
                    "text": (
                        "Здравствуйте. Количество пока не подтверждаем: сначала хотим получить MOQ и ценовые уровни, "
                        "после этого согласуем объем внутри отдела закупок."
                    )
                }

        reply = generate_supplier_reply(QuantityModel(), product, [inbound], language="ru", style="formal")

        self.assertIn("количеств", reply.lower())
        self.assertNotIn("подтверждаем заказ", reply.lower())
        self.assertNotIn("оплатим", reply.lower())
        self.assertNotIn("актуальную цену", reply.lower())

    def test_generate_supplier_reply_uses_second_ai_call_for_empty_model_output(self):
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            title="E2E Servo Drive",
            product_url="https://supplier.test/products/servo-drive",
            contacts=[contact],
        )
        contact.product_id = product.id
        inbound = ConversationMessage.create_inbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=contact.id,
            channel=ContactType.EMAIL,
            subject="Re: request",
            body="Опишите ваше направление работы и откуда вы о нас узнали?",
            from_address=contact.contact_value,
            to_address="agent@example.test",
        )

        model = SequenceModelProvider(
            [
                {"text": ""},
                {
                    "text": (
                        "Здравствуйте. Я представляю отдел закупок ООО «АЛС». "
                        f"Мы уточняем условия по товару {product.title} и можем использовать данные компании из карточки."
                    )
                },
            ]
        )

        reply = generate_supplier_reply(model, product, [inbound], language="ru", style="formal")

        self.assertIn(product.title, reply)
        self.assertIn("ООО «АЛС»", reply)
        self.assertNotIn("актуальную цену", reply.lower())
        self.assertEqual(2, len(model.prompts))
        self.assertIn("Previous model output was unusable", model.prompts[1])

    def test_generate_supplier_reply_uses_second_ai_call_for_out_of_policy_model_output(self):
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            title="E2E Servo Drive",
            product_url="https://supplier.test/products/servo-drive",
            contacts=[contact],
        )
        contact.product_id = product.id
        inbound = ConversationMessage.create_inbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=contact.id,
            channel=ContactType.EMAIL,
            subject="Re: request",
            body="Can you confirm the order and payment today?",
            from_address=contact.contact_value,
            to_address="agent@example.test",
        )

        model = SequenceModelProvider(
            [
                {"text": "confirmed order, we will pay today"},
                {
                    "text": (
                        "Hello. I represent the purchasing department of AlphaLogisticService LLC. "
                        f"We are reviewing preliminary terms for {product.title}; any order or payment decision requires internal approval."
                    )
                },
            ]
        )

        reply = generate_supplier_reply(model, product, [inbound], language="en", style="formal")

        self.assertIn(product.title, reply)
        self.assertIn("AlphaLogisticService LLC", reply)
        self.assertNotIn("we will pay", reply.lower())
        self.assertEqual(2, len(model.prompts))

    def test_generate_supplier_reply_rejects_repeated_initial_request_for_requisites_question(self):
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            title="E2E Servo Drive",
            product_url="https://supplier.test/products/servo-drive",
            contacts=[contact],
        )
        contact.product_id = product.id
        inbound = ConversationMessage.create_inbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=contact.id,
            channel=ContactType.EMAIL,
            subject="Re: request",
            body="\u041f\u0440\u0435\u0434\u043e\u0441\u0442\u0430\u0432\u044c\u0442\u0435, \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0440\u0435\u043a\u0432\u0438\u0437\u0438\u0442\u044b \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0438 \u0418\u041d\u041d.",
            from_address=contact.contact_value,
            to_address="agent@example.test",
        )
        repeated_initial_request = (
            "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435. "
            "\u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u0442\u0435\u043a\u0443\u0449\u0443\u044e \u0446\u0435\u043d\u0443, "
            "\u043d\u0430\u043b\u0438\u0447\u0438\u0435, MOQ, \u0441\u0440\u043e\u043a\u0438 \u043f\u043e\u0441\u0442\u0430\u0432\u043a\u0438, "
            "\u0443\u0441\u043b\u043e\u0432\u0438\u044f \u043e\u043f\u043b\u0430\u0442\u044b \u0438 \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438."
        )
        model = SequenceModelProvider(
            [
                {"text": repeated_initial_request},
                {
                    "text": (
                        "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435. "
                        "\u041d\u0430\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u043c \u0434\u0430\u043d\u043d\u044b\u0435 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438: "
                        "\u041e\u041e\u041e \u00ab\u0410\u041b\u0421\u00bb, \u0418\u041d\u041d 7703456789, "
                        "\u041a\u041f\u041f 770301001, \u041e\u0413\u0420\u041d 1237700309876. "
                        "\u0411\u0430\u043d\u043a\u043e\u0432\u0441\u043a\u0438\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 \u0441\u043c\u043e\u0436\u0435\u043c "
                        "\u0443\u0442\u043e\u0447\u043d\u0438\u0442\u044c \u043f\u043e\u0441\u043b\u0435 \u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0435\u0433\u043e "
                        "\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044f."
                    )
                },
            ]
        )

        reply = generate_supplier_reply(model, product, [inbound], language="ru", style="formal")

        self.assertIn("7703456789", reply)
        self.assertNotIn("MOQ", reply)
        self.assertEqual(2, len(model.prompts))
        self.assertIn("reply repeats initial outreach template", model.prompts[1])

    def test_generate_supplier_reply_fails_when_model_correction_is_unusable(self):
        contact = SupplierContact.create(ContactType.EMAIL, "supplier@example.test")
        product = Product(
            title="E2E Servo Drive",
            product_url="https://supplier.test/products/servo-drive",
            contacts=[contact],
        )
        contact.product_id = product.id
        inbound = ConversationMessage.create_inbound(
            product_id=product.id,
            supplier_contact_id=contact.id,
            contact_attempt_id=contact.id,
            channel=ContactType.EMAIL,
            subject="Re: request",
            body="Can you confirm payment?",
            from_address=contact.contact_value,
            to_address="agent@example.test",
        )
        model = SequenceModelProvider([{"text": ""}, {"text": "ok"}])

        with self.assertRaises(RuntimeError):
            generate_supplier_reply(model, product, [inbound], language="en", style="formal")

        self.assertEqual(2, len(model.prompts))

    def test_supplier_message_supports_language_and_style(self):
        model = SequenceModelProvider(
            [
                {
                    "reply": valid_initial_message(
                        "BLITZ E80 Single ESC",
                        "https://shop.iflight.com/BLITZ-E80-Single-ESC-Pro-1797",
                    )
                },
                {
                    "reply": valid_initial_message(
                        "BLITZ E80 Single ESC",
                        "https://shop.iflight.com/BLITZ-E80-Single-ESC-Pro-1797",
                    )
                },
            ]
        )
        english = generate_supplier_message(
            model,
            "BLITZ E80 Single ESC",
            "https://shop.iflight.com/BLITZ-E80-Single-ESC-Pro-1797",
            language="en",
            style="concise",
        )
        chinese = generate_supplier_message(
            model,
            "BLITZ E80 Single ESC",
            "https://shop.iflight.com/BLITZ-E80-Single-ESC-Pro-1797",
            language="zh",
            style="formal",
        )

        self.assertIn("English", model.prompts[0])
        self.assertIn("Chinese", model.prompts[1])
        self.assertIn("Hello", english)
        self.assertIn("current price", english)
        self.assertIn("MOQ", english)
        self.assertIn("BLITZ E80 Single ESC", chinese)
        self.assertEqual([], SafeMessagePolicy.validate(english))
        self.assertEqual([], SafeMessagePolicy.validate(chinese))


if __name__ == "__main__":
    unittest.main()
