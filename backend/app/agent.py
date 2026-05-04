from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Protocol

from .domain import ConversationMessage, Product, validate_product_payload


class ModelProvider(Protocol):
    name: str

    def complete(self, prompt: str, tools: list[str] | None = None) -> Any:
        ...


class BrowserMcpConnector(Protocol):
    def research(self, query_text: str) -> "ConnectorResult":
        ...


class EmailConnector(Protocol):
    def send(self, to: str, subject: str, body: str) -> "ConnectorResult":
        ...


class TelegramConnector(Protocol):
    def send(self, chat: str, body: str) -> "ConnectorResult":
        ...


@dataclass(frozen=True)
class ConnectorResult:
    success: bool
    payload: dict[str, Any] | None = None
    external_id: str | None = None
    error_message: str | None = None


# -----------------------------------------------------------------------------
# Company context for supplier communication
# -----------------------------------------------------------------------------
#
# IMPORTANT:
# docs/ooo.md is the authoritative company legend for this local MVP. The
# constants below mirror the same legend so model prompts do not drift back to
# the older demo company identity.
# -----------------------------------------------------------------------------

COMPANY_NAME_RU = "ООО «АЛС»"
COMPANY_SHORT_NAME_RU = "АЛС"
COMPANY_NAME_EN = "AlphaLogisticService LLC"
COMPANY_NAME_ZH = "AlphaLogisticService"

COMPANY_ROLE_RU = "цифровой помощник отдела закупок"
COMPANY_ROLE_EN = "digital assistant of the purchasing department"
COMPANY_ROLE_ZH = "采购部门数字助理"

COMPANY_PROFILE_RU = (
    "Общество с ограниченной ответственностью «АльфаЛогистикСервис» — логистический оператор "
    "для интернет-магазинов и малого/среднего бизнеса. Компания оказывает курьерскую доставку "
    "по Москве и Московской области, складскую обработку заказов, сборку, упаковку, маркировку "
    "и интеграцию с CRM-системами клиентов через API. Корпоративные ценности: прозрачность, "
    "скорость и забота о клиенте."
)

COMPANY_PROFILE_EN = (
    "AlphaLogisticService LLC is a logistics operator for online stores and small to medium-sized "
    "businesses. The company provides courier delivery across Moscow and the Moscow region, "
    "warehouse order processing, picking, packing, labeling, and CRM/API integrations for clients. "
    "Its values are transparency, speed, and care for the customer."
)

COMPANY_PROFILE_ZH = (
    "AlphaLogisticService LLC 是一家面向网店以及中小企业的物流运营商，"
    "提供莫斯科及莫斯科州快递配送、仓储订单处理、拣货、包装、贴标以及客户CRM/API系统集成服务。"
    "公司的价值观是透明、速度和客户关怀。"
)

COMPANY_STAFF_RU = (
    "Штатная численность по легенде — 42 человека. "
    "В структуре есть руководство, операционная логистика, складской блок, курьерская служба, "
    "IT/API-интеграции, коммерческий блок, бухгалтерия и юридическое сопровождение."
)

COMPANY_STAFF_EN = (
    "The company has 42 employees in the project legend. Its structure includes management, "
    "operations logistics, warehouse processing, courier service, IT/API integrations, "
    "commercial operations, accounting, and legal support."
)

COMPANY_STAFF_ZH = (
    "项目设定中公司有42名员工，结构包括管理层、运营物流、仓储处理、快递服务、IT/API集成、商务运营、会计和法律支持。"
)

COMPANY_PROCUREMENT_CATEGORIES_RU = (
    "Типовые категории закупок для деятельности компании: упаковочные материалы, маркировка, "
    "складское и курьерское оборудование, терминалы сбора данных, этикетки, расходные материалы, "
    "IT-оборудование, серверы, сетевое оборудование, интеграционные решения, офисное и операционное оснащение."
)

COMPANY_PROCUREMENT_CATEGORIES_EN = (
    "Typical procurement categories include packaging materials, labeling supplies, warehouse and "
    "courier equipment, data collection terminals, consumables, IT equipment, servers, network "
    "equipment, integration solutions, and office or operations equipment."
)

COMPANY_PROCUREMENT_CATEGORIES_ZH = (
    "典型采购类别包括包装材料、标签和标识耗材、仓储和快递设备、数据采集终端、IT设备、服务器、网络设备、集成解决方案以及办公和运营设备。"
)

COMPANY_REGIONS_RU = (
    "Основной регион операционной деятельности — Москва и Московская область. "
    "Поставщики могут рассматриваться в России и других регионах при наличии приемлемой логистики."
)

COMPANY_REGIONS_EN = (
    "The main operating region is Moscow and the Moscow region. Suppliers may be considered in Russia "
    "and other regions when logistics conditions are acceptable."
)

COMPANY_REGIONS_ZH = (
    "主要运营区域为莫斯科和莫斯科州。如物流条件合适，也可以考虑俄罗斯及其他地区的供应商。"
)

COMPANY_LIMITATIONS_RU = (
    "Компания не подтверждает заказы автоматически, не принимает финансовые обязательства без письменного "
    "согласования ответственного менеджера, не отправляет платёжные данные без отдельного разрешения, "
    "не занимается закупкой запрещённых товаров, не обсуждает обход ограничений и не скрывает назначение товара."
)

COMPANY_LIMITATIONS_EN = (
    "The company does not automatically confirm orders, does not create financial commitments without written "
    "approval from the responsible manager, does not send payment details without explicit permission, "
    "does not source prohibited goods, does not discuss circumvention of restrictions, and does not hide product end use."
)

COMPANY_LIMITATIONS_ZH = (
    "公司不会自动确认订单，不会在未获得负责人书面批准的情况下承担财务义务，不会在未获得明确许可的情况下发送付款信息，"
    "不会采购违禁商品，不会讨论规避限制，也不会隐瞒产品用途。"
)

COMPANY_REQUISITES_POLICY_RU = (
    "Юридические сведения из docs/ooo.md являются тестовой легендой компании и могут использоваться в ответе, "
    "если поставщик прямо спрашивает о компании. Банковские реквизиты и платёжные данные не отправляются "
    "автоматически без подтверждения ответственного менеджера."
)

COMPANY_REQUISITES_POLICY_EN = (
    "Legal company details from docs/ooo.md are the test company legend and may be used when the supplier "
    "explicitly asks about the company. Banking requisites and payment data are not sent automatically without "
    "confirmation from the responsible manager."
)

COMPANY_REQUISITES_POLICY_ZH = (
    "docs/ooo.md 中的公司法律信息是测试公司设定，供应商明确询问公司信息时可以使用。银行账户和付款数据未经负责人确认不会自动发送。"
)

def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "ooo.md").exists():
            return parent
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _ooo_company_knowledge() -> str:
    path = _repo_root() / "docs" / "ooo.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _company_context_for_prompt() -> str:
    ooo = _ooo_company_knowledge()
    return (
        "Company context from docs/ooo.md (authoritative for this project):\n"
        f"{ooo or 'docs/ooo.md is unavailable.'}\n"
        "\n"
        "Operational role for this product-sourcing workflow:\n"
        f"- Writer represents the purchasing/procurement function of {COMPANY_NAME_RU} / {COMPANY_NAME_EN}.\n"
        "- The company profile, contacts, addresses, requisites, and staff data from docs/ooo.md may be used when the supplier asks who we are or requests company details.\n"
        "- The conversation purpose is supplier information exchange for a product: clarify product identity, availability, price levels, MOQ, lead time, delivery, documents, and next steps.\n"
        "- Do not use any older demo company identity; docs/ooo.md is the current company legend.\n"
        "\n"
        "MVP boundaries:\n"
        f"{COMPANY_LIMITATIONS_RU}\n"
        f"{COMPANY_LIMITATIONS_EN}\n"
        f"{COMPANY_LIMITATIONS_ZH}\n"
    )


@dataclass
class ToolRegistry:
    tools: dict[str, Any] = field(default_factory=dict)

    def register(self, name: str, tool: Any) -> None:
        if not name:
            raise ValueError("tool name is required")
        self.tools[name] = tool

    def require(self, name: str) -> Any:
        try:
            return self.tools[name]
        except KeyError as exc:
            raise KeyError(f"required tool is not registered: {name}") from exc


@dataclass(frozen=True)
class AgentRuntime:
    model_provider: ModelProvider
    tool_registry: ToolRegistry


@dataclass(frozen=True)
class AgentProductOutput:
    products: list[Product]
    skipped: list[dict[str, Any]]

    @property
    def products_created(self) -> int:
        return len(self.products)

    @property
    def products_skipped(self) -> int:
        return len(self.skipped)

    def to_task_payload(self) -> dict[str, Any]:
        return {
            "productsCreated": self.products_created,
            "productsSkipped": self.products_skipped,
            "errors": self.skipped,
        }


def validate_agent_product_output(
    payload: dict[str, Any],
    allow_products_without_contacts: bool = False,
) -> AgentProductOutput:
    products: list[Product] = []
    skipped: list[dict[str, Any]] = []

    for index, item in enumerate(payload.get("products") or []):
        result = validate_product_payload(item, allow_without_contacts=allow_products_without_contacts)
        if result.product is None:
            skipped.append({"index": index, "errors": result.errors, "raw": item})
            continue
        products.append(result.product)

    return AgentProductOutput(products=products, skipped=skipped)


class SafeMessagePolicy:
    FORBIDDEN_PHRASES = (
        "подтверждаем заказ",
        "оформляем заказ",
        "обещаем оплату",
        "оплатим",
        "купить",
        "confirmed order",
        "we will pay",
        "payment details",
        "bypass",
        "[your name]",
        "your name",
        "[ваше имя]",
        "ваше имя",
    )

    REQUIRED_TOPICS = (
        ("товар", "product", "产品"),
        ("ссылк", "link", "链接"),
        ("цен", "price", "价格"),
        ("налич", "availability", "stock", "库存"),
        ("минимальн", "moq", "minimum", "最小"),
        ("срок", "lead time", "delivery time", "交期"),
        ("оплат", "payment", "付款"),
        ("достав", "delivery", "shipping", "发货"),
    )

    @classmethod
    def validate(cls, message: str) -> list[str]:
        text = message.lower()
        errors = [f"forbidden phrase: {phrase}" for phrase in cls.FORBIDDEN_PHRASES if phrase in text]
        for topic in cls.REQUIRED_TOPICS:
            if not any(phrase in text for phrase in topic):
                errors.append(f"missing required topic: {topic[0]}")
        return errors

    @classmethod
    def validate_follow_up(cls, message: str) -> list[str]:
        text = message.lower()
        errors = [f"forbidden phrase: {phrase}" for phrase in cls.FORBIDDEN_PHRASES if phrase in text]
        if len(text.strip()) < 12:
            errors.append("reply is too short")
        if _looks_like_initial_request(text):
            errors.append("reply repeats initial outreach template")
        return errors


def normalize_message_language(language: str | None) -> str:
    value = (language or "ru").strip().lower()
    return value if value in {"ru", "en", "zh"} else "ru"


def normalize_message_style(style: str | None) -> str:
    value = (style or "formal").strip().lower()
    return value if value in {"concise", "formal", "friendly"} else "formal"


def generate_supplier_message(
    model_provider: ModelProvider,
    product_title: str,
    product_url: str,
    language: str = "ru",
    style: str = "formal",
) -> str:
    language = normalize_message_language(language)
    style = normalize_message_style(style)

    prompt = _supplier_initial_message_prompt(product_title, product_url, language, style)
    candidate = _complete_supplier_text(model_provider, prompt)
    errors = (
        _validate_initial_supplier_message(candidate, product_title, product_url)
        if candidate
        else ["model did not produce a supplier message"]
    )
    if not errors:
        return candidate

    corrected = _generate_corrected_supplier_message(
        model_provider,
        product_title,
        product_url,
        language=language,
        style=style,
        rejected_message=candidate,
        rejection_errors=errors,
    )
    corrected_errors = (
        _validate_initial_supplier_message(corrected, product_title, product_url)
        if corrected
        else ["model did not produce a corrected supplier message"]
    )
    if not corrected_errors:
        return corrected

    raise RuntimeError("; ".join(corrected_errors))


def _supplier_initial_message_prompt(product_title: str, product_url: str, language: str, style: str) -> str:
    language_names = {"ru": "Russian", "en": "English", "zh": "Chinese"}
    return (
        f"Write one {style} first business message to a supplier in {language_names[language]}.\n"
        "You are writing as a real employee from the user's company, not as an AI assistant.\n"
        "Use the company context below as the authoritative background for identity, business profile, procurement scope, and restrictions.\n"
        "Do not copy a fixed template: compose the message naturally for this exact product and company context.\n"
        "\n"
        f"{_company_context_for_prompt()}\n"
        "\n"
        "Message requirements:\n"
        f'- The visible message must contain this exact product title substring: "{product_title}".\n'
        f'- The visible message must contain this exact product link substring: "{product_url}".\n'
        "- Mention the product title and product link exactly as provided.\n"
        "- Ask the supplier for current price, availability/stock, MOQ/minimum order quantity, lead time or delivery timing, payment terms, and delivery/shipping terms.\n"
        "- Keep the message business-like and concise enough for email or Telegram.\n"
        "- Do not confirm an order, promise payment, send payment details, request policy bypass, or create legal commitments.\n"
        "- Do not invent company details; use docs/ooo.md only when company information is needed.\n"
        "- Do not include placeholders such as [your name] or [ваше имя].\n"
        "- Before returning, verify that the exact product title and exact product link are present in the message body.\n"
        'Return only the message body. If JSON is required, return exactly {"reply": "<message body>"}.\n'
        f"Product: {product_title}\n"
        f"Product link: {product_url}\n"
    )


def _validate_initial_supplier_message(message: str, product_title: str, product_url: str) -> list[str]:
    errors = SafeMessagePolicy.validate(message)
    text = message.lower()
    if product_title.strip().lower() not in text:
        errors.append("missing exact product title")
    if product_url.strip() not in message:
        errors.append("missing exact product link")
    return errors


def _generate_corrected_supplier_message(
    model_provider: ModelProvider,
    product_title: str,
    product_url: str,
    language: str,
    style: str,
    rejected_message: str,
    rejection_errors: list[str],
) -> str:
    language_names = {"ru": "Russian", "en": "English", "zh": "Chinese"}
    prompt = (
        f"Previous model output was unusable for an initial supplier message: {', '.join(rejection_errors)}.\n"
        f"Write a corrected {style} first business message in {language_names[language]}.\n"
        "The message must be newly authored by the model for this product and company context.\n"
        f'The corrected message will be rejected unless it visibly contains this exact product title substring: "{product_title}".\n'
        f'The corrected message will be rejected unless it visibly contains this exact product link substring: "{product_url}".\n'
        "It must include product title, product link, price, availability, MOQ/minimum order quantity, lead time/delivery timing, payment terms, and delivery/shipping terms.\n"
        "It must not confirm an order, promise payment, send payment details, request policy bypass, or create legal commitments.\n"
        "It must not include placeholders such as [your name] or [ваше имя].\n"
        "Use docs/ooo.md company knowledge below as the authoritative source for identity and details.\n"
        "\n"
        f"{_company_context_for_prompt()}\n"
        "\n"
        f"Rejected message:\n{rejected_message or '<empty>'}\n"
        f"Product: {product_title}\n"
        f"Product link: {product_url}\n"
        'Return only the message body. If JSON is required, return exactly {"reply": "<message body>"}.\n'
    )
    return _complete_supplier_text(model_provider, prompt)


def generate_supplier_reply(
    model_provider: ModelProvider,
    product: Product,
    messages: list[ConversationMessage],
    language: str = "ru",
    style: str = "formal",
) -> str:
    language = normalize_message_language(language)
    style = normalize_message_style(style)

    prompt = _supplier_reply_prompt(product, messages, language, style)
    candidate = _complete_supplier_text(model_provider, prompt)
    errors = (
        _validate_follow_up_supplier_reply(candidate, messages)
        if candidate
        else ["model did not produce a supplier reply"]
    )
    if not errors:
        return candidate

    corrected = _generate_corrected_supplier_reply(
        model_provider,
        product,
        messages,
        language=language,
        style=style,
        rejected_reply=candidate,
        rejection_errors=errors,
    )
    corrected_errors = (
        _validate_follow_up_supplier_reply(corrected, messages)
        if corrected
        else ["model did not produce a corrected supplier reply"]
    )
    if not corrected_errors:
        return corrected

    raise RuntimeError("; ".join(corrected_errors))


def _supplier_reply_prompt(
    product: Product,
    messages: list[ConversationMessage],
    language: str,
    style: str,
) -> str:
    language_names = {"ru": "Russian", "en": "English", "zh": "Chinese"}
    return (
        f"Write one {style} business reply to the supplier in {language_names[language]}.\n"
        "You are writing as a real employee from the user's company, not as an AI assistant.\n"
        "Use the company context below as the authoritative background for identity, business profile, company role, procurement scope, and restrictions.\n"
        "\n"
        f"{_company_context_for_prompt()}\n"
        "\n"
        "Conversation rules:\n"
        "- Read the full conversation history and answer the supplier's latest message directly.\n"
        "- Do not use generic phrases such as 'I will check internally and get back to you' unless the supplier asks for information that is genuinely unavailable.\n"
        "- Do not repeat the initial outreach request when the supplier has already replied.\n"
        "- If the supplier asks about company profile, direction of work, how we found them, product identity, product link, quantity, delivery address, or requisites, answer that specific question first.\n"
        "- If the supplier asks for company details, legal requisites, INN, KPP, or OGRN, answer with available non-payment legal company details from docs/ooo.md and do not ask for price, availability, MOQ, lead time, payment, or delivery in that reply.\n"
        "- If exact data is unavailable, say what is known from the product and company context, then ask one concise clarifying question if needed.\n"
        f"You represent the purchasing department of {COMPANY_NAME_RU} / {COMPANY_NAME_EN}.\n"
        "You may explicitly state the company name and describe the company as a logistics operator for online stores and small to medium-sized businesses.\n"
        "If the supplier asks how we found them, explain that the contact was found during supplier research for the product shown below.\n"
        "If the supplier asks for legal requisites, INN, KPP, OGRN, BIC, bank account, legal address, or payment details, do not invent them. "
        "Say that exact requisites can be provided after internal confirmation by the responsible manager.\n"
        "Do not confirm an order, promise payment, send payment details, or create legal commitments.\n"
        'Return only the message body. If JSON is required, return exactly {"reply": "<message body>"}.\n'
        f"Product: {product.title}\n"
        f"Product link: {product.product_url}\n"
        "Conversation history:\n"
        f"{_conversation_for_prompt(messages)}"
    )


def _validate_follow_up_supplier_reply(message: str, messages: list[ConversationMessage]) -> list[str]:
    errors = SafeMessagePolicy.validate_follow_up(message)
    latest = _latest_supplier_message_text(messages).lower()
    reply = message.lower()
    if _asks_for_company_details(latest):
        if _looks_like_initial_request(reply) and "reply repeats initial outreach template" not in errors:
            errors.append("reply repeats initial outreach template")
        if not _answers_company_details(reply):
            errors.append("reply does not answer supplier company/requisites question")
    return errors


def _latest_supplier_message_text(messages: list[ConversationMessage]) -> str:
    for message in reversed(messages):
        if message.direction.value == "inbound":
            return message.body or ""
    return messages[-1].body if messages else ""


def _asks_for_company_details(text: str) -> bool:
    markers = (
        "\u0440\u0435\u043a\u0432\u0438\u0437",
        "\u0438\u043d\u043d",
        "\u043a\u043f\u043f",
        "\u043e\u0433\u0440\u043d",
        "\u044e\u0440\u0438\u0434",
        "\u043a\u043e\u043c\u043f\u0430\u043d",
        "requisites",
        "company details",
        "legal details",
        "tax id",
        "inn",
        "kpp",
        "ogrn",
    )
    return any(marker in text for marker in markers)


def _answers_company_details(text: str) -> bool:
    markers = (
        "\u0440\u0435\u043a\u0432\u0438\u0437",
        "\u0438\u043d\u043d",
        "\u043a\u043f\u043f",
        "\u043e\u0433\u0440\u043d",
        "\u044e\u0440\u0438\u0434",
        "\u043e\u043e\u043e",
        "\u043a\u043e\u043c\u043f\u0430\u043d",
        "\u043b\u043e\u0433\u0438\u0441\u0442",
        "\u043d\u0430\u043f\u0440\u0430\u0432\u043b",
        "\u0434\u0435\u044f\u0442\u0435\u043b",
        "requisites",
        "company details",
        "legal details",
        "company",
        "business",
        "logistics",
        "tax id",
        "llc",
        "inn",
        "kpp",
        "ogrn",
    )
    return any(marker in text for marker in markers)


def _generate_corrected_supplier_reply(
    model_provider: ModelProvider,
    product: Product,
    messages: list[ConversationMessage],
    language: str,
    style: str,
    rejected_reply: str,
    rejection_errors: list[str],
) -> str:
    language_names = {"ru": "Russian", "en": "English", "zh": "Chinese"}
    prompt = (
        f"Previous model output was unusable for a supplier reply: {', '.join(rejection_errors)}.\n"
        f"Write a corrected {style} business reply in {language_names[language]}.\n"
        "The reply must be authored by the model as the company's employee and must answer the supplier's latest message directly.\n"
        "Use docs/ooo.md company knowledge below as the authoritative source for company identity and details.\n"
        "Do not replace the reply with a generic supplier-request message; respond to the current conversation.\n"
        "If the supplier asked for company details, legal requisites, INN, KPP, or OGRN, answer that request from docs/ooo.md using non-payment legal details. Do not ask for price, availability, MOQ, lead time, payment, or delivery in that corrected reply.\n"
        "Do not confirm an order, promise payment, send payment details, or create legal commitments.\n"
        "\n"
        f"{_company_context_for_prompt()}\n"
        "\n"
        f"Rejected reply:\n{rejected_reply or '<empty>'}\n"
        f"Product: {product.title}\n"
        f"Product link: {product.product_url}\n"
        "Conversation history:\n"
        f"{_conversation_for_prompt(messages)}\n"
        'Return only the message body. If JSON is required, return exactly {"reply": "<message body>"}.\n'
    )
    return _complete_supplier_text(model_provider, prompt)


def _complete_supplier_text(model_provider: ModelProvider, prompt: str) -> str:
    try:
        return _completion_text(model_provider.complete(prompt)).strip()
    except Exception:
        return ""


def _completion_text(raw: Any) -> str:
    if isinstance(raw, str):
        value = raw.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                parsed_string = json.loads(value)
            except json.JSONDecodeError:
                parsed_string = None
            if isinstance(parsed_string, str):
                return parsed_string
        if value.startswith("{") and value.endswith("}"):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return raw

            if isinstance(parsed, dict):
                for key in ("agent", "text", "message", "content", "reply"):
                    parsed_value = parsed.get(key)
                    if isinstance(parsed_value, str):
                        return parsed_value

            return raw

        return raw

    if isinstance(raw, dict):
        for key in ("agent", "text", "message", "content", "reply"):
            value = raw.get(key)
            if isinstance(value, str):
                return value

        choices = raw.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content

                text = first.get("text")
                if isinstance(text, str):
                    return text

    return str(raw or "")


def _conversation_for_prompt(messages: list[ConversationMessage]) -> str:
    lines = []
    for message in messages[-12:]:
        direction = "supplier" if message.direction.value == "inbound" else "agent"
        subject = f" | {message.subject}" if message.subject else ""
        lines.append(f"{direction}{subject}: {message.body}")
    return "\n".join(lines)


def _looks_like_initial_request(text: str) -> bool:
    topic_markers = (
        ("\u0446\u0435\u043d", "\u0441\u0442\u043e\u0438\u043c", "price", "cost"),
        ("\u043d\u0430\u043b\u0438\u0447", "\u0441\u043a\u043b\u0430\u0434", "availability", "stock"),
        ("\u043c\u0438\u043d\u0438\u043c", "\u043f\u0430\u0440\u0442", "moq", "minimum order"),
        ("\u0441\u0440\u043e\u043a", "\u043f\u043e\u0441\u0442\u0430\u0432", "lead time", "delivery time"),
        ("\u043e\u043f\u043b\u0430\u0442", "payment", "payment terms"),
        ("\u0434\u043e\u0441\u0442\u0430\u0432", "\u043e\u0442\u0433\u0440\u0443\u0437", "delivery", "shipping"),
    )
    return sum(1 for topic in topic_markers if any(marker in text for marker in topic)) >= 5
