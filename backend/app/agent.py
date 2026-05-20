from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Protocol

from .domain import ConversationMessage, Product, validate_contract_draft_text, validate_product_payload


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
    errors.extend(_selected_language_errors(candidate, language))
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
    corrected_errors.extend(_selected_language_errors(corrected, language))
    if not corrected_errors:
        return corrected

    fallback = _fallback_initial_supplier_message(product_title, product_url, language)
    fallback_errors = _validate_initial_supplier_message(fallback, product_title, product_url)
    if not fallback_errors:
        return fallback

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


def _selected_language_errors(message: str, language: str) -> list[str]:
    text = (message or "").strip()
    if not text:
        return []
    if language == "ru" and not _contains_cyrillic(text):
        return ["message is not in selected Russian language"]
    if language == "zh" and not _contains_cjk(text):
        return ["message is not in selected Chinese language"]
    if language == "en" and _contains_cyrillic(text) and not _contains_latin(text):
        return ["message is not in selected English language"]
    return []


def _contains_cyrillic(text: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", text))


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _contains_latin(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]", text))


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


def _fallback_initial_supplier_message(product_title: str, product_url: str, language: str) -> str:
    if language == "ru":
        return (
            "Здравствуйте. Я представляю отдел закупок AlphaLogisticService LLC.\n"
            f"Товар: {product_title}\n"
            f"Ссылка на товар: {product_url}\n"
            "Пожалуйста, уточните актуальную цену (price), наличие (availability/stock), "
            "MOQ/minimum order quantity, срок поставки (lead time), условия оплаты (payment terms) "
            "и условия доставки/отгрузки (delivery/shipping terms) по этому товару."
        )
    if language == "zh":
        return (
            "您好。我代表 AlphaLogisticService LLC 采购部门。\n"
            f"产品: {product_title}\n"
            f"产品链接: {product_url}\n"
            "请确认当前价格 price、库存 availability/stock、MOQ/minimum order quantity、"
            "交期 lead time、付款条款 payment terms 以及交付/运输条款 delivery/shipping terms。"
        )
    return (
        "Hello. I represent the purchasing department of AlphaLogisticService LLC.\n"
        f"Product: {product_title}\n"
        f"Product link: {product_url}\n"
        "Please share the current price, availability/stock, MOQ/minimum order quantity, "
        "lead time, payment terms, and delivery/shipping terms for this product."
    )


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
    errors.extend(_selected_language_errors(candidate, language))
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
    corrected_errors.extend(_selected_language_errors(corrected, language))
    if not corrected_errors:
        return corrected

    fallback = _fallback_supplier_reply(product, messages, language)
    fallback_errors = _validate_follow_up_supplier_reply(fallback, messages)
    if not fallback_errors:
        return fallback

    raise RuntimeError("; ".join(corrected_errors))


def _fallback_supplier_reply(product: Product, messages: list[ConversationMessage], language: str) -> str:
    latest = _latest_supplier_message_text(messages).lower()
    if _asks_for_company_details(latest):
        if language == "ru":
            return (
                "Здравствуйте. Мы представляем AlphaLogisticService LLC, логистического оператора "
                "для интернет-магазинов и малого/среднего бизнеса. Ваш контакт найден во время "
                f"поиска поставщика по товару: {product.title}. Ссылка на товар: {product.product_url}. "
                "Точные юридические реквизиты можем предоставить после внутреннего подтверждения ответственным менеджером."
            )
        if language == "zh":
            return (
                "您好。我们代表 AlphaLogisticService LLC，一家面向线上商店和中小企业的物流运营商。"
                f"我们是在该产品的供应商调研中找到贵方联系方式的: {product.title}。产品链接: {product.product_url}。"
                "准确的法律信息可在负责人内部确认后提供。"
            )
        return (
            "Hello. We represent AlphaLogisticService LLC, a logistics operator for online stores "
            "and small to medium-sized businesses. We found your contact during supplier research "
            f"for this product: {product.title}. Product link: {product.product_url}. "
            "Exact legal requisites can be provided after internal confirmation by the responsible manager."
        )
    if language == "ru":
        return (
            "Здравствуйте. Спасибо за ответ. "
            f"Мы представляем AlphaLogisticService LLC. Пожалуйста, подтвердите актуальную цену и условия доставки/отгрузки по товару {product.title}. "
            f"Ссылка на товар: {product.product_url}."
        )
    if language == "zh":
        return (
            "您好。感谢您的回复。"
            f"请确认产品 {product.title} 的当前单价以及交付/运输条款。"
            f"产品链接: {product.product_url}."
        )
    return (
        "Hello. Thank you for the update. "
        f"Please confirm the current unit price and delivery/shipping terms for {product.title}. "
        f"Product link: {product.product_url}."
    )


def analyze_supplier_reply(model_provider: ModelProvider | None, product: Product, message: ConversationMessage) -> dict[str, str]:
    heuristic = _heuristic_supplier_reply_analysis(message.body)
    if model_provider is None:
        return heuristic
    prompt = (
        "Analyze the latest supplier reply for a product sourcing workflow.\n"
        "Return JSON only. Use this schema with string values: "
        "{\"summary\":\"...\",\"price\":\"...\",\"currency\":\"...\",\"moq\":\"...\","
        "\"leadTime\":\"...\",\"availability\":\"...\",\"paymentTerms\":\"...\","
        "\"deliveryTerms\":\"...\",\"supplierContactName\":\"...\",\"nextStep\":\"...\","
        "\"riskFlags\":\"...\",\"communicationScore\":\"0-100\"}.\n"
        "Use empty strings for missing fields. Do not invent values.\n"
        "Score communication higher when the supplier gives concrete commercial terms, "
        "clear availability, and a useful next step; lower when the answer is evasive.\n"
        f"Product: {product.title}\n"
        f"Product URL: {product.product_url}\n"
        f"Supplier message subject: {message.subject or ''}\n"
        f"Supplier message body:\n{message.body}\n"
    )
    try:
        raw = model_provider.complete(prompt)
        parsed = _parse_supplier_analysis(raw)
    except Exception:
        parsed = {}
    merged = dict(heuristic)
    for key, value in parsed.items():
        if str(value).strip():
            merged[key] = str(value).strip()
    merged["communicationScore"] = str(_bounded_score(merged.get("communicationScore"), heuristic.get("communicationScore", "45")))
    return merged


def answer_internal_product_assistant(
    model_provider: ModelProvider,
    product: Product,
    contacts: list[Any],
    messages: list[ConversationMessage],
    question: str,
) -> str:
    prompt = (
        "You are an internal AI assistant for a product sourcing operator.\n"
        "Answer only the user's internal question. Do not write a supplier email unless explicitly asked to draft one.\n"
        "Do not send messages, do not imply that anything was sent, and do not create purchase/payment commitments.\n"
        "Use the product card, supplier contacts, extracted supplier terms, and conversation history below.\n"
        "If information is missing, say what is missing and suggest the next practical question to ask the supplier.\n"
        "Keep the answer concise and actionable.\n"
        "\n"
        f"Product title: {product.title}\n"
        f"Product URL: {product.product_url}\n"
        f"Supplier: {product.supplier_name or ''}\n"
        f"Price: {product.price or ''} {product.currency or ''}\n"
        f"Attributes: {json.dumps(product.attributes, ensure_ascii=False, default=str)}\n"
        "Contacts:\n"
        f"{_contacts_for_prompt(contacts)}\n"
        "Conversation history:\n"
        f"{_conversation_for_prompt(messages)}\n"
        "\n"
        f"User internal question: {question}\n"
        "Return only the internal assistant answer as readable text for a non-technical user. "
        "Do not return raw JSON."
    )
    try:
        answer = _humanize_internal_assistant_answer(model_provider.complete(prompt))
    except Exception:
        answer = ""
    return answer or _fallback_internal_assistant_answer(product, messages, question)


def _humanize_internal_assistant_answer(raw: Any) -> str:
    if isinstance(raw, dict):
        return _humanize_internal_assistant_payload(raw)
    if isinstance(raw, list):
        return "\n".join(f"- {str(item).strip()}" for item in raw if str(item).strip())

    text = _completion_text(raw).strip()
    if not text:
        return ""
    parsed = _parse_json_like_object(text)
    if isinstance(parsed, dict):
        return _humanize_internal_assistant_payload(parsed)
    if isinstance(parsed, list):
        return "\n".join(f"- {str(item).strip()}" for item in parsed if str(item).strip())
    return text


def _parse_json_like_object(text: str) -> Any:
    candidates = [text]
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if match:
        candidates.append(match.group(1))
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _humanize_internal_assistant_payload(payload: dict[str, Any]) -> str:
    labels = {
        "summary": "Кратко",
        "riskLevel": "Уровень риска",
        "reasons": "Причины",
        "nextSteps": "Следующие шаги",
        "recommendation": "Рекомендация",
        "missingData": "Чего не хватает",
        "supplierStrengths": "Сильные стороны поставщика",
        "supplierWeaknesses": "Слабые места",
        "price": "Цена",
        "moq": "MOQ",
        "leadTime": "Срок поставки",
        "paymentTerms": "Условия оплаты",
        "deliveryTerms": "Условия доставки",
    }
    ordered_keys = [key for key in labels if key in payload]
    ordered_keys.extend(key for key in payload if key not in ordered_keys)
    sections: list[str] = []
    for key in ordered_keys:
        value = payload.get(key)
        if value in (None, "", [], {}):
            continue
        label = labels.get(key, _humanize_key(key))
        sections.append(_format_internal_assistant_section(label, value))
    return "\n\n".join(section for section in sections if section).strip()


def _format_internal_assistant_section(label: str, value: Any) -> str:
    if isinstance(value, list):
        items = [f"- {str(item).strip()}" for item in value if str(item).strip()]
        return f"{label}:\n" + "\n".join(items) if items else ""
    if isinstance(value, dict):
        items = [f"- {_humanize_key(str(item_key))}: {item_value}" for item_key, item_value in value.items() if item_value not in (None, "", [], {})]
        return f"{label}:\n" + "\n".join(items) if items else ""
    return f"{label}: {str(value).strip()}"


def _humanize_key(key: str) -> str:
    spaced = re.sub(r"(?<!^)([A-Z])", r" \1", key).replace("_", " ").replace("-", " ")
    return spaced[:1].upper() + spaced[1:]


def _contacts_for_prompt(contacts: list[Any]) -> str:
    lines = []
    for contact in contacts:
        contact_type = getattr(contact, "contact_type", "")
        contact_value = getattr(contact, "contact_value", "")
        is_primary = getattr(contact, "is_primary", False)
        lines.append(f"- {contact_type}: {contact_value} primary={is_primary}")
    return "\n".join(lines) or "<none>"


def _fallback_internal_assistant_answer(product: Product, messages: list[ConversationMessage], question: str) -> str:
    latest_inbound = _latest_supplier_message_text(messages)
    missing = []
    for label, markers in (
        ("price", ("price", "цена", "стоим")),
        ("MOQ", ("moq", "minimum", "миним")),
        ("lead time", ("lead time", "delivery time", "срок")),
        ("delivery terms", ("delivery", "shipping", "достав")),
        ("payment terms", ("payment", "оплат")),
    ):
        source = f"{product.attributes} {latest_inbound}".lower()
        if not any(marker in source for marker in markers):
            missing.append(label)
    if "risk" in question.lower() or "риск" in question.lower():
        return "Known risk points: verify supplier identity, payment terms, delivery terms, and whether the contact domain matches the supplier domain before committing."
    if missing:
        return f"Missing supplier data: {', '.join(missing)}. Next step: ask the supplier for these terms before comparing the offer."
    return "The card has enough initial supplier data to compare price, contact quality, response history, and extracted terms. Next step: compare this supplier against alternatives."


def _parse_supplier_analysis(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        payload = raw
    else:
        text = _completion_text(raw).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return {}
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    if not isinstance(payload, dict):
        return {}
    allowed = {
        "summary",
        "price",
        "currency",
        "moq",
        "leadTime",
        "availability",
        "paymentTerms",
        "deliveryTerms",
        "supplierContactName",
        "nextStep",
        "riskFlags",
        "communicationScore",
    }
    return {key: str(payload.get(key) or "").strip() for key in allowed}


def _heuristic_supplier_reply_analysis(text: str) -> dict[str, str]:
    normalized = text or ""
    price_match = re.search(r"(?:(USD|EUR|GBP|CNY|RUB)\s*)?(\d[\d\s,.]*)(?:\s*(USD|EUR|GBP|CNY|RUB|\$|€|£))?", normalized, flags=re.IGNORECASE)
    moq_match = re.search(r"\b(?:MOQ|minimum order(?: quantity)?|мин(?:имальн\w*)?)\D{0,20}(\d[\d\s,.]*)", normalized, flags=re.IGNORECASE)
    lead_match = re.search(r"\b(?:lead time|delivery time|ship(?:ping)?|срок(?:и)?|поставк\w*)\D{0,40}([A-Za-zА-Яа-я0-9\s\-]{2,40})", normalized, flags=re.IGNORECASE)
    availability = ""
    if re.search(r"\b(in stock|available|есть в наличии|на складе|stock)\b", normalized, flags=re.IGNORECASE):
        availability = "available"
    elif re.search(r"\b(out of stock|not available|нет в наличии)\b", normalized, flags=re.IGNORECASE):
        availability = "not available"
    currency = ""
    price = ""
    if price_match:
        currency = (price_match.group(1) or price_match.group(3) or "").replace("$", "USD").replace("€", "EUR").replace("£", "GBP").upper()
        price = price_match.group(2).strip()
    filled = sum(
        1
        for value in (
            price,
            currency,
            moq_match.group(1).strip() if moq_match else "",
            lead_match.group(1).strip() if lead_match else "",
            availability,
        )
        if value
    )
    score = 35 + filled * 12
    if re.search(r"\b(thank|thanks|regards|готов|можем|offer|quote)\b", normalized, flags=re.IGNORECASE):
        score += 10
    return {
        "summary": normalized.strip()[:220],
        "price": price,
        "currency": currency,
        "moq": moq_match.group(1).strip() if moq_match else "",
        "leadTime": lead_match.group(1).strip() if lead_match else "",
        "availability": availability,
        "paymentTerms": _first_phrase(normalized, ("payment", "оплат")),
        "deliveryTerms": _first_phrase(normalized, ("delivery", "shipping", "достав", "поставк")),
        "supplierContactName": "",
        "nextStep": "review supplier terms" if filled else "request missing commercial terms",
        "riskFlags": "",
        "communicationScore": str(max(0, min(100, score))),
    }


def _first_phrase(text: str, markers: tuple[str, ...]) -> str:
    for marker in markers:
        match = re.search(rf"[^.\n]*{re.escape(marker)}[^.\n]*", text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()[:160]
    return ""


def _bounded_score(value: Any, fallback: str) -> int:
    try:
        return max(0, min(100, int(float(str(value).strip()))))
    except (TypeError, ValueError):
        return max(0, min(100, int(float(str(fallback or "45").strip()))))


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


def generate_contract_draft(
    model_provider: ModelProvider,
    product: Product,
    messages: list[ConversationMessage],
) -> dict[str, Any]:
    prompt = _contract_draft_prompt(product, messages)
    try:
        raw = model_provider.complete(prompt)
        parsed = _parse_contract_draft_output(raw)
    except Exception as exc:
        parsed = _fallback_contract_draft(product, messages, str(exc))
    validate_contract_draft_text(parsed["draftText"])
    return parsed


def _contract_draft_prompt(product: Product, messages: list[ConversationMessage]) -> str:
    history = "\n".join(f"{message.direction.value}: {message.body}" for message in messages[-40:])
    return (
        "Prepare a supplier contract draft from the product card and supplier conversation.\n"
        "Return JSON only with title, extractedData, and draftText.\n"
        "The contract draft must be marked as DRAFT / NOT SIGNED / NOT BINDING.\n"
        "Do not confirm an order, promise payment, include payment instructions, include bank account data, "
        "add signatures, or create legal commitments. Use only facts present in the product card or conversation.\n"
        f"Product: {product.title}\n"
        f"Product URL: {product.product_url}\n"
        f"Supplier: {product.supplier_name or ''}\n"
        f"Known attributes: {json.dumps(product.attributes, ensure_ascii=False)}\n"
        f"Conversation history:\n{history}\n"
    )


def _parse_contract_draft_output(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        data = dict(raw)
    elif isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("model did not return valid contract draft JSON") from exc
    else:
        raise RuntimeError("model returned unsupported contract draft output")
    title = str(data.get("title") or "Contract draft").strip()
    extracted = data.get("extractedData") or data.get("extracted_data") or {}
    draft_text = str(data.get("draftText") or data.get("draft_text") or "").strip()
    if not isinstance(extracted, dict):
        raise RuntimeError("contract draft extractedData must be an object")
    if not draft_text:
        raise RuntimeError("contract draft text is required")
    return {"title": title, "extractedData": extracted, "draftText": draft_text}


def _fallback_contract_draft(product: Product, messages: list[ConversationMessage], error_message: str) -> dict[str, Any]:
    latest_terms = "\n".join(
        f"- {message.direction.value}: {message.body.strip()}"
        for message in messages[-8:]
        if message.body and message.body.strip()
    )
    extracted = {
        "product": product.title,
        "productUrl": product.product_url,
        "supplier": product.supplier_name or "",
        "knownConversationTerms": latest_terms,
        "missingFields": ["legal signatory", "delivery address", "final quantities", "manager approval"],
        "modelProviderError": error_message[:240],
    }
    draft_text = (
        "DRAFT CONTRACT - NOT SIGNED AND NOT BINDING\n"
        "For internal review only.\n\n"
        f"Supplier: {product.supplier_name or 'Supplier'}\n"
        f"Product: {product.title}\n"
        f"Product URL: {product.product_url}\n\n"
        "Known supplier conversation terms:\n"
        f"{latest_terms or '- No supplier commercial terms are recorded yet.'}\n\n"
        "Missing information before any formal document can be prepared:\n"
        "- legal signatory\n"
        "- delivery address\n"
        "- final quantities\n"
        "- responsible manager approval\n\n"
        "This draft does not confirm an order, does not authorize shipment, does not include signatures, "
        "and does not instruct any payment action."
    )
    return {
        "title": f"Draft contract for {product.title}",
        "extractedData": extracted,
        "draftText": draft_text,
    }


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
