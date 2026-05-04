from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import re
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4


class SearchRequestStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContactAttemptStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SENT = "sent"
    RESPONDED = "responded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTaskType(str, Enum):
    PRODUCT_SEARCH = "product_search"
    SUPPLIER_CONTACT = "supplier_contact"


class ContactType(str, Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"


class ConversationDirection(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class ConversationMessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    RECEIVED = "received"


class ProductValidationError(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_contact_type(value: ContactType | str) -> ContactType:
    if isinstance(value, ContactType):
        return value
    try:
        return ContactType(value)
    except ValueError as exc:
        raise ValueError(f"unsupported contact type: {value}") from exc


def normalize_conversation_direction(value: ConversationDirection | str) -> ConversationDirection:
    if isinstance(value, ConversationDirection):
        return value
    try:
        return ConversationDirection(value)
    except ValueError as exc:
        raise ValueError(f"unsupported conversation direction: {value}") from exc


def normalize_conversation_status(value: ConversationMessageStatus | str) -> ConversationMessageStatus:
    if isinstance(value, ConversationMessageStatus):
        return value
    try:
        return ConversationMessageStatus(value)
    except ValueError as exc:
        raise ValueError(f"unsupported conversation message status: {value}") from exc


def validate_search_query(query_text: str) -> str:
    normalized = query_text.strip()
    if not normalized:
        raise ValueError("queryText is required")
    if len(normalized) < 3:
        raise ValueError("queryText must be at least 3 characters")
    if len(normalized) > 1000:
        raise ValueError("queryText must be at most 1000 characters")
    return normalized


def validate_max_results(max_results: int) -> int:
    try:
        normalized = int(max_results)
    except (TypeError, ValueError) as exc:
        raise ValueError("maxResults must be an integer") from exc
    if normalized < 1:
        raise ValueError("maxResults must be at least 1")
    if normalized > 50:
        raise ValueError("maxResults must be at most 50")
    return normalized


@dataclass
class SearchRequest:
    query_text: str
    max_results: int = 5
    id: UUID = field(default_factory=uuid4)
    status: SearchRequestStatus = SearchRequestStatus.QUEUED
    error_message: str | None = None
    agent_task_id: UUID | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def create(cls, query_text: str, max_results: int = 5) -> "SearchRequest":
        return cls(
            query_text=validate_search_query(query_text),
            max_results=validate_max_results(max_results),
        )

    def transition_to(self, next_status: SearchRequestStatus) -> None:
        allowed = {
            SearchRequestStatus.QUEUED: {SearchRequestStatus.RUNNING, SearchRequestStatus.CANCELLED},
            SearchRequestStatus.RUNNING: {
                SearchRequestStatus.COMPLETED,
                SearchRequestStatus.FAILED,
                SearchRequestStatus.CANCELLED,
            },
            SearchRequestStatus.COMPLETED: set(),
            SearchRequestStatus.FAILED: set(),
            SearchRequestStatus.CANCELLED: set(),
        }
        if next_status not in allowed[self.status]:
            raise ValueError(f"invalid search request transition: {self.status} -> {next_status}")
        self.status = next_status
        self.updated_at = utcnow()
        if next_status == SearchRequestStatus.RUNNING:
            self.started_at = self.started_at or self.updated_at
        if next_status in {SearchRequestStatus.COMPLETED, SearchRequestStatus.FAILED, SearchRequestStatus.CANCELLED}:
            self.completed_at = self.completed_at or self.updated_at


@dataclass
class SupplierContact:
    contact_type: ContactType
    contact_value: str
    id: UUID = field(default_factory=uuid4)
    product_id: UUID | None = None
    is_primary: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, contact_type: ContactType | str, contact_value: str) -> "SupplierContact":
        normalized_type = normalize_contact_type(contact_type)
        value = contact_value.strip()
        if not value:
            raise ValueError("contact value is required")
        if normalized_type == ContactType.EMAIL and not is_valid_email(value):
            raise ValueError("email contact must be valid")
        if normalized_type == ContactType.TELEGRAM and not is_valid_telegram(value):
            raise ValueError("telegram contact must be @username or https://t.me/username")
        return cls(contact_type=normalized_type, contact_value=value)


def is_valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def is_valid_telegram(value: str) -> bool:
    return bool(
        re.fullmatch(r"@[A-Za-z0-9_]{5,32}", value)
        or re.fullmatch(r"https://t\.me/[A-Za-z0-9_]{5,32}", value)
    )


@dataclass
class Product:
    title: str
    product_url: str
    contacts: list[SupplierContact]
    id: UUID = field(default_factory=uuid4)
    search_request_id: UUID | None = None
    description: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    images: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    supplier_name: str | None = None
    source_domain: str | None = None
    raw_agent_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProductValidationResult:
    product: Product | None
    errors: list[str]


def validate_product_payload(payload: dict[str, Any], allow_without_contacts: bool = False) -> ProductValidationResult:
    errors: list[str] = []
    title = str(payload.get("title") or "").strip()
    product_url = str(payload.get("productUrl") or payload.get("product_url") or "").strip()

    if not title:
        errors.append("title is required")
    if not validate_url(product_url):
        errors.append("productUrl must be a valid URL")

    contacts: list[SupplierContact] = []
    for index, contact_payload in enumerate(payload.get("contacts") or []):
        try:
            contacts.append(SupplierContact.create(contact_payload.get("type"), contact_payload.get("value", "")))
        except ValueError as exc:
            errors.append(f"contact[{index}]: {exc}")

    if not contacts and not allow_without_contacts:
        errors.append("at least one supplier contact is required")

    if errors:
        return ProductValidationResult(product=None, errors=errors)

    price_value = payload.get("price")
    price = Decimal(str(price_value)) if price_value is not None else None
    product = Product(
        title=title,
        product_url=product_url,
        contacts=contacts,
        description=payload.get("description"),
        price=price,
        currency=payload.get("currency"),
        images=list(payload.get("images") or []),
        attributes=dict(payload.get("attributes") or {}),
        supplier_name=payload.get("supplierName") or payload.get("supplier_name"),
        source_domain=urlparse(product_url).netloc,
        raw_agent_payload=payload,
    )
    for contact in contacts:
        contact.product_id = product.id
    return ProductValidationResult(product=product, errors=[])


@dataclass
class ContactAttempt:
    product_id: UUID
    supplier_contact_id: UUID
    channel: ContactType
    message_text: str
    id: UUID = field(default_factory=uuid4)
    agent_task_id: UUID | None = None
    status: ContactAttemptStatus = ContactAttemptStatus.QUEUED
    error_message: str | None = None
    external_message_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    sent_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        product_id: UUID,
        supplier_contact_id: UUID,
        channel: ContactType | str,
        message_text: str,
    ) -> "ContactAttempt":
        if not message_text.strip():
            raise ValueError("message_text is required")
        return cls(
            product_id=product_id,
            supplier_contact_id=supplier_contact_id,
            channel=normalize_contact_type(channel),
            message_text=message_text,
        )

    @staticmethod
    def has_active(attempts: list["ContactAttempt"]) -> bool:
        return any(attempt.status in {ContactAttemptStatus.QUEUED, ContactAttemptStatus.RUNNING} for attempt in attempts)

    def transition_to(self, next_status: ContactAttemptStatus) -> None:
        allowed = {
            ContactAttemptStatus.QUEUED: {ContactAttemptStatus.RUNNING, ContactAttemptStatus.CANCELLED},
            ContactAttemptStatus.RUNNING: {
                ContactAttemptStatus.SENT,
                ContactAttemptStatus.RESPONDED,
                ContactAttemptStatus.FAILED,
                ContactAttemptStatus.CANCELLED,
            },
            ContactAttemptStatus.SENT: {ContactAttemptStatus.RESPONDED},
            ContactAttemptStatus.RESPONDED: set(),
            ContactAttemptStatus.FAILED: set(),
            ContactAttemptStatus.CANCELLED: set(),
        }
        if next_status not in allowed[self.status]:
            raise ValueError(f"invalid contact attempt transition: {self.status} -> {next_status}")
        self.status = next_status
        self.updated_at = utcnow()
        if next_status == ContactAttemptStatus.SENT:
            self.sent_at = self.sent_at or self.updated_at
        if next_status in {
            ContactAttemptStatus.SENT,
            ContactAttemptStatus.RESPONDED,
            ContactAttemptStatus.FAILED,
            ContactAttemptStatus.CANCELLED,
        }:
            self.completed_at = self.completed_at or self.updated_at


@dataclass
class ConversationMessage:
    product_id: UUID
    supplier_contact_id: UUID
    contact_attempt_id: UUID
    direction: ConversationDirection
    channel: ContactType
    body: str
    id: UUID = field(default_factory=uuid4)
    subject: str | None = None
    from_address: str | None = None
    to_address: str | None = None
    status: ConversationMessageStatus = ConversationMessageStatus.QUEUED
    external_message_id: str | None = None
    error_message: str | None = None
    requires_user_approval: bool = False
    approval_reason: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    sent_at: datetime | None = None
    provider_timestamp: datetime | None = None

    @classmethod
    def create_outbound(
        cls,
        product_id: UUID,
        supplier_contact_id: UUID,
        contact_attempt_id: UUID,
        channel: ContactType | str,
        subject: str | None,
        body: str,
        from_address: str | None,
        to_address: str | None,
    ) -> "ConversationMessage":
        normalized_body = body.strip()
        if not normalized_body:
            raise ValueError("conversation message body is required")
        return cls(
            product_id=product_id,
            supplier_contact_id=supplier_contact_id,
            contact_attempt_id=contact_attempt_id,
            direction=ConversationDirection.OUTBOUND,
            channel=normalize_contact_type(channel),
            subject=subject.strip() if subject else None,
            body=normalized_body,
            from_address=from_address.strip() if from_address else None,
            to_address=to_address.strip() if to_address else None,
        )

    @classmethod
    def create_inbound(
        cls,
        product_id: UUID,
        supplier_contact_id: UUID,
        contact_attempt_id: UUID,
        channel: ContactType | str,
        subject: str | None,
        body: str,
        from_address: str | None,
        to_address: str | None,
        external_message_id: str | None = None,
        provider_timestamp: datetime | None = None,
    ) -> "ConversationMessage":
        normalized_body = body.strip()
        if not normalized_body:
            raise ValueError("conversation message body is required")
        now = utcnow()
        return cls(
            product_id=product_id,
            supplier_contact_id=supplier_contact_id,
            contact_attempt_id=contact_attempt_id,
            direction=ConversationDirection.INBOUND,
            channel=normalize_contact_type(channel),
            subject=subject.strip() if subject else None,
            body=normalized_body,
            from_address=from_address.strip() if from_address else None,
            to_address=to_address.strip() if to_address else None,
            status=ConversationMessageStatus.RECEIVED,
            external_message_id=external_message_id.strip() if external_message_id else None,
            created_at=now,
            updated_at=now,
            provider_timestamp=provider_timestamp,
        )

    def mark_sent(self, external_message_id: str | None = None, provider_timestamp: datetime | None = None) -> None:
        self.status = ConversationMessageStatus.SENT
        self.external_message_id = external_message_id
        self.error_message = None
        self.sent_at = self.sent_at or utcnow()
        self.provider_timestamp = provider_timestamp or self.provider_timestamp
        self.updated_at = self.sent_at

    def mark_failed(self, error_message: str) -> None:
        self.status = ConversationMessageStatus.FAILED
        self.error_message = error_message
        self.updated_at = utcnow()

    def mark_requires_user_approval(self, reason: str) -> None:
        self.requires_user_approval = True
        self.approval_reason = reason.strip() or "User approval required"
        self.updated_at = utcnow()


@dataclass
class AgentTask:
    task_type: AgentTaskType
    input_payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    status: AgentTaskStatus = AgentTaskStatus.QUEUED
    output_payload: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def create(cls, task_type: AgentTaskType | str, input_payload: dict[str, Any]) -> "AgentTask":
        normalized_type = AgentTaskType(task_type)
        return cls(task_type=normalized_type, input_payload=dict(input_payload))

    def transition_to(self, next_status: AgentTaskStatus) -> None:
        allowed = {
            AgentTaskStatus.QUEUED: {AgentTaskStatus.RUNNING, AgentTaskStatus.CANCELLED},
            AgentTaskStatus.RUNNING: {AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED},
            AgentTaskStatus.COMPLETED: set(),
            AgentTaskStatus.FAILED: set(),
            AgentTaskStatus.CANCELLED: set(),
        }
        if next_status not in allowed[self.status]:
            raise ValueError(f"invalid agent task transition: {self.status} -> {next_status}")
        self.status = next_status
        now = utcnow()
        if next_status == AgentTaskStatus.RUNNING:
            self.started_at = self.started_at or now
        if next_status in {AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.CANCELLED}:
            self.completed_at = self.completed_at or now
