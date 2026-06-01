from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.pool import NullPool

from .domain import (
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
    Product,
    SearchRequest,
    SearchRequestStatus,
    SupplierContact,
)
from .repositories import InMemoryContractsRepository


metadata = sa.MetaData()


agent_tasks = sa.Table(
    "agent_tasks",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("task_type", sa.String(64), nullable=False),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("input_payload", sa.JSON(), nullable=False, default=dict),
    sa.Column("output_payload", sa.JSON(), nullable=True),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
)

search_requests = sa.Table(
    "search_requests",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("query_text", sa.Text(), nullable=False),
    sa.Column("max_results", sa.Integer(), nullable=False, default=5),
    sa.Column("target_market", sa.Text(), nullable=True),
    sa.Column("quantity", sa.Text(), nullable=True),
    sa.Column("budget", sa.Text(), nullable=True),
    sa.Column("certifications", sa.JSON(), nullable=False, default=list),
    sa.Column("supplier_preference", sa.Text(), nullable=True),
    sa.Column("normalized_intent", sa.JSON(), nullable=False, default=dict),
    sa.Column("missing_fields", sa.JSON(), nullable=False, default=list),
    sa.Column("clarifying_questions", sa.JSON(), nullable=False, default=list),
    sa.Column("common_filters", sa.JSON(), nullable=False, default=list),
    sa.Column("product_attributes", sa.JSON(), nullable=False, default=list),
    sa.Column("sourcing_guidance", sa.JSON(), nullable=False, default=dict),
    sa.Column("suppliers_count", sa.Integer(), nullable=False, default=0),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("agent_task_id", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
)

products = sa.Table(
    "products",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("search_request_id", sa.String(36), nullable=True),
    sa.Column("title", sa.Text(), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("price", sa.Numeric(18, 4), nullable=True),
    sa.Column("currency", sa.String(16), nullable=True),
    sa.Column("product_url", sa.Text(), nullable=False),
    sa.Column("source_domain", sa.Text(), nullable=True),
    sa.Column("supplier_name", sa.Text(), nullable=True),
    sa.Column("images", sa.JSON(), nullable=False, default=list),
    sa.Column("attributes", sa.JSON(), nullable=False, default=dict),
    sa.Column("raw_agent_payload", sa.JSON(), nullable=True),
    sa.Column("moq", sa.Text(), nullable=True),
    sa.Column("price_range", sa.Text(), nullable=True),
    sa.Column("fit_score", sa.Numeric(5, 4), nullable=True),
    sa.Column("fit_summary", sa.Text(), nullable=True),
    sa.Column("matched_requirements", sa.JSON(), nullable=False, default=list),
    sa.Column("missing_requirements", sa.JSON(), nullable=False, default=list),
    sa.Column("supplier_badges", sa.JSON(), nullable=False, default=list),
    sa.Column("supplier_country", sa.Text(), nullable=True),
    sa.Column("supplier_city", sa.Text(), nullable=True),
    sa.Column("is_verified_supplier", sa.Boolean(), nullable=False, default=False),
    sa.Column("is_audited_supplier", sa.Boolean(), nullable=False, default=False),
    sa.Column("supports_customization", sa.Boolean(), nullable=False, default=False),
    sa.Column("sample_available", sa.Boolean(), nullable=False, default=False),
)

supplier_contacts = sa.Table(
    "supplier_contacts",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("product_id", sa.String(36), nullable=True),
    sa.Column("contact_type", sa.String(32), nullable=False),
    sa.Column("contact_value", sa.Text(), nullable=False),
    sa.Column("is_primary", sa.Boolean(), nullable=False, default=False),
    sa.Column("metadata", sa.JSON(), nullable=False, default=dict),
)

contact_attempts = sa.Table(
    "contact_attempts",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("product_id", sa.String(36), nullable=False),
    sa.Column("supplier_contact_id", sa.String(36), nullable=False),
    sa.Column("agent_task_id", sa.String(36), nullable=True),
    sa.Column("channel", sa.String(32), nullable=False),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("message_text", sa.Text(), nullable=False),
    sa.Column("external_message_id", sa.Text(), nullable=True),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
)

conversation_messages = sa.Table(
    "conversation_messages",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("product_id", sa.String(36), nullable=False),
    sa.Column("supplier_contact_id", sa.String(36), nullable=False),
    sa.Column("contact_attempt_id", sa.String(36), nullable=False),
    sa.Column("direction", sa.String(32), nullable=False),
    sa.Column("channel", sa.String(32), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column("subject", sa.Text(), nullable=True),
    sa.Column("from_address", sa.Text(), nullable=True),
    sa.Column("to_address", sa.Text(), nullable=True),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("external_message_id", sa.Text(), nullable=True),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("requires_user_approval", sa.Boolean(), nullable=False, default=False),
    sa.Column("approval_reason", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("provider_timestamp", sa.DateTime(timezone=True), nullable=True),
)

contract_drafts = sa.Table(
    "contract_drafts",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("product_id", sa.String(36), nullable=False),
    sa.Column("supplier_contact_id", sa.String(36), nullable=False),
    sa.Column("supplier_name", sa.Text(), nullable=False),
    sa.Column("agent_task_id", sa.String(36), nullable=True),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("title", sa.Text(), nullable=False),
    sa.Column("extracted_data", sa.JSON(), nullable=False, default=dict),
    sa.Column("draft_text", sa.Text(), nullable=True),
    sa.Column("file_name", sa.Text(), nullable=False),
    sa.Column("content_type", sa.Text(), nullable=False),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
)


class SqlAlchemyRepository:
    def __init__(self, database_url: str, create_schema: bool = False) -> None:
        self.database_url = database_url
        self.engine = sa.create_engine(database_url, future=True, poolclass=NullPool)
        self.contracts = SqlAlchemyContractsRepository(self)
        if create_schema:
            self.create_schema()

    def create_schema(self) -> None:
        metadata.create_all(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    def add_search_request(self, request: SearchRequest) -> SearchRequest:
        self._upsert(search_requests, _search_request_row(request))
        return request

    def get_search_request(self, request_id: UUID) -> SearchRequest | None:
        row = self._get(search_requests, request_id)
        return _search_request_from_row(row) if row else None

    def list_search_requests(self) -> list[SearchRequest]:
        with self.engine.begin() as connection:
            rows = connection.execute(sa.select(search_requests).order_by(search_requests.c.created_at.desc())).mappings().all()
        return [_search_request_from_row(row) for row in rows]

    def add_agent_task(self, task: AgentTask) -> AgentTask:
        self._upsert(agent_tasks, _agent_task_row(task))
        return task

    def get_agent_task(self, task_id: UUID) -> AgentTask | None:
        row = self._get(agent_tasks, task_id)
        return _agent_task_from_row(row) if row else None

    def list_queued_agent_tasks(self, limit: int = 10) -> list[AgentTask]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(agent_tasks)
                .where(agent_tasks.c.status == AgentTaskStatus.QUEUED.value)
                .order_by(agent_tasks.c.created_at.asc())
                .limit(limit)
            ).mappings().all()
        return [_agent_task_from_row(row) for row in rows]

    def add_product(self, product: Product) -> Product:
        self._upsert(products, _product_row(product))
        for contact in product.contacts:
            self.add_supplier_contact(contact)
        return product

    def get_product(self, product_id: UUID) -> Product | None:
        row = self._get(products, product_id)
        if not row:
            return None
        product = _product_from_row(row)
        product.contacts = self.list_contacts_for_product(product.id)
        return product

    def list_products_for_request(self, search_request_id: UUID | None) -> list[Product]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(products).where(products.c.search_request_id == str(search_request_id))
            ).mappings().all()
        return [_product_from_row(row) for row in rows]

    def add_supplier_contact(self, contact: SupplierContact) -> SupplierContact:
        self._upsert(supplier_contacts, _supplier_contact_row(contact))
        return contact

    def list_contacts_for_product(self, product_id: UUID) -> list[SupplierContact]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(supplier_contacts).where(supplier_contacts.c.product_id == str(product_id))
            ).mappings().all()
        return [_supplier_contact_from_row(row) for row in rows]

    def add_contact_attempt(self, attempt: ContactAttempt) -> ContactAttempt:
        self._upsert(contact_attempts, _contact_attempt_row(attempt))
        return attempt

    def list_attempts_for_product(self, product_id: UUID) -> list[ContactAttempt]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(contact_attempts).where(contact_attempts.c.product_id == str(product_id))
            ).mappings().all()
        return [_contact_attempt_from_row(row) for row in rows]

    def add_conversation_message(self, message: ConversationMessage) -> ConversationMessage:
        self._upsert(conversation_messages, _conversation_message_row(message))
        return message

    def list_conversation_messages_for_product(self, product_id: UUID) -> list[ConversationMessage]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(conversation_messages)
                .where(conversation_messages.c.product_id == str(product_id))
                .order_by(conversation_messages.c.created_at.asc())
            ).mappings().all()
        return [_conversation_message_from_row(row) for row in rows]

    @property
    def contact_attempts(self) -> dict[UUID, ContactAttempt]:
        return {attempt.id: attempt for product in self._all_products() for attempt in self.list_attempts_for_product(product.id)}

    @property
    def supplier_contacts(self) -> dict[UUID, SupplierContact]:
        with self.engine.begin() as connection:
            rows = connection.execute(sa.select(supplier_contacts)).mappings().all()
        return {_supplier_contact_from_row(row).id: _supplier_contact_from_row(row) for row in rows}

    @property
    def conversation_messages(self) -> dict[UUID, ConversationMessage]:
        with self.engine.begin() as connection:
            rows = connection.execute(sa.select(conversation_messages)).mappings().all()
        return {_conversation_message_from_row(row).id: _conversation_message_from_row(row) for row in rows}

    def _all_products(self) -> list[Product]:
        with self.engine.begin() as connection:
            rows = connection.execute(sa.select(products)).mappings().all()
        return [_product_from_row(row) for row in rows]

    def _get(self, table: sa.Table, entity_id: UUID):
        with self.engine.begin() as connection:
            return connection.execute(sa.select(table).where(table.c.id == str(entity_id))).mappings().first()

    def _upsert(self, table: sa.Table, values: dict[str, Any]) -> None:
        with self.engine.begin() as connection:
            exists = connection.execute(sa.select(table.c.id).where(table.c.id == values["id"])).first()
            if exists:
                connection.execute(table.update().where(table.c.id == values["id"]).values(**values))
            else:
                connection.execute(table.insert().values(**values))


class SqlAlchemyContractsRepository(InMemoryContractsRepository):
    def __init__(self, parent: SqlAlchemyRepository) -> None:
        super().__init__()
        self.parent = parent

    def add_contract_draft(self, draft: ContractDraft) -> ContractDraft:
        self.parent._upsert(contract_drafts, _contract_draft_row(draft))
        return draft

    def get_contract_draft(self, draft_id: UUID) -> ContractDraft | None:
        row = self.parent._get(contract_drafts, draft_id)
        return _contract_draft_from_row(row) if row else None

    def list_contract_drafts_for_product(self, product_id: UUID) -> list[ContractDraft]:
        with self.parent.engine.begin() as connection:
            rows = connection.execute(
                sa.select(contract_drafts)
                .where(contract_drafts.c.product_id == str(product_id))
                .order_by(contract_drafts.c.created_at.desc())
            ).mappings().all()
        return [_contract_draft_from_row(row) for row in rows]


def _uuid(value: Any) -> UUID | None:
    return UUID(str(value)) if value else None


def _search_request_row(request: SearchRequest) -> dict[str, Any]:
    return {
        "id": str(request.id),
        "query_text": request.query_text,
        "max_results": request.max_results,
        "target_market": request.target_market,
        "quantity": request.quantity,
        "budget": request.budget,
        "certifications": request.certifications,
        "supplier_preference": request.supplier_preference,
        "normalized_intent": request.normalized_intent,
        "missing_fields": request.missing_fields,
        "clarifying_questions": request.clarifying_questions,
        "common_filters": request.common_filters,
        "product_attributes": request.product_attributes,
        "sourcing_guidance": request.sourcing_guidance,
        "suppliers_count": request.suppliers_count,
        "status": request.status.value,
        "error_message": request.error_message,
        "agent_task_id": str(request.agent_task_id) if request.agent_task_id else None,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "started_at": request.started_at,
        "completed_at": request.completed_at,
    }


def _search_request_from_row(row) -> SearchRequest:
    return SearchRequest(
        id=_uuid(row["id"]),
        query_text=row["query_text"],
        max_results=row["max_results"],
        target_market=row.get("target_market"),
        quantity=row.get("quantity"),
        budget=row.get("budget"),
        certifications=list(row.get("certifications") or []),
        supplier_preference=row.get("supplier_preference"),
        normalized_intent=dict(row.get("normalized_intent") or {}),
        missing_fields=list(row.get("missing_fields") or []),
        clarifying_questions=list(row.get("clarifying_questions") or []),
        common_filters=list(row.get("common_filters") or []),
        product_attributes=list(row.get("product_attributes") or []),
        sourcing_guidance=dict(row.get("sourcing_guidance") or {}),
        suppliers_count=int(row.get("suppliers_count") or 0),
        status=SearchRequestStatus(row["status"]),
        error_message=row.get("error_message"),
        agent_task_id=_uuid(row.get("agent_task_id")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
    )


def _agent_task_row(task: AgentTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "task_type": task.task_type.value,
        "status": task.status.value,
        "input_payload": task.input_payload,
        "output_payload": task.output_payload,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }


def _agent_task_from_row(row) -> AgentTask:
    return AgentTask(
        id=_uuid(row["id"]),
        task_type=AgentTaskType(row["task_type"]),
        status=AgentTaskStatus(row["status"]),
        input_payload=dict(row.get("input_payload") or {}),
        output_payload=row.get("output_payload"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
    )


def _product_row(product: Product) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "search_request_id": str(product.search_request_id) if product.search_request_id else None,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "currency": product.currency,
        "product_url": product.product_url,
        "source_domain": product.source_domain,
        "supplier_name": product.supplier_name,
        "images": product.images,
        "attributes": product.attributes,
        "raw_agent_payload": product.raw_agent_payload,
        "moq": product.moq,
        "price_range": product.price_range,
        "fit_score": product.fit_score,
        "fit_summary": product.fit_summary,
        "matched_requirements": product.matched_requirements,
        "missing_requirements": product.missing_requirements,
        "supplier_badges": product.supplier_badges,
        "supplier_country": product.supplier_country,
        "supplier_city": product.supplier_city,
        "is_verified_supplier": product.is_verified_supplier,
        "is_audited_supplier": product.is_audited_supplier,
        "supports_customization": product.supports_customization,
        "sample_available": product.sample_available,
    }


def _product_from_row(row) -> Product:
    return Product(
        id=_uuid(row["id"]),
        search_request_id=_uuid(row.get("search_request_id")),
        title=row["title"],
        description=row.get("description"),
        price=Decimal(str(row["price"])) if row.get("price") is not None else None,
        currency=row.get("currency"),
        product_url=row["product_url"],
        source_domain=row.get("source_domain"),
        supplier_name=row.get("supplier_name"),
        images=list(row.get("images") or []),
        attributes=dict(row.get("attributes") or {}),
        raw_agent_payload=row.get("raw_agent_payload"),
        contacts=[],
        moq=row.get("moq"),
        price_range=row.get("price_range"),
        fit_score=Decimal(str(row["fit_score"])) if row.get("fit_score") is not None else None,
        fit_summary=row.get("fit_summary"),
        matched_requirements=list(row.get("matched_requirements") or []),
        missing_requirements=list(row.get("missing_requirements") or []),
        supplier_badges=list(row.get("supplier_badges") or []),
        supplier_country=row.get("supplier_country"),
        supplier_city=row.get("supplier_city"),
        is_verified_supplier=bool(row.get("is_verified_supplier")),
        is_audited_supplier=bool(row.get("is_audited_supplier")),
        supports_customization=bool(row.get("supports_customization")),
        sample_available=bool(row.get("sample_available")),
    )


def _supplier_contact_row(contact: SupplierContact) -> dict[str, Any]:
    return {
        "id": str(contact.id),
        "product_id": str(contact.product_id) if contact.product_id else None,
        "contact_type": contact.contact_type.value,
        "contact_value": contact.contact_value,
        "is_primary": contact.is_primary,
        "metadata": contact.metadata,
    }


def _supplier_contact_from_row(row) -> SupplierContact:
    return SupplierContact(
        id=_uuid(row["id"]),
        product_id=_uuid(row.get("product_id")),
        contact_type=ContactType(row["contact_type"]),
        contact_value=row["contact_value"],
        is_primary=bool(row.get("is_primary")),
        metadata=dict(row.get("metadata") or {}),
    )


def _contact_attempt_row(attempt: ContactAttempt) -> dict[str, Any]:
    return {
        "id": str(attempt.id),
        "product_id": str(attempt.product_id),
        "supplier_contact_id": str(attempt.supplier_contact_id),
        "agent_task_id": str(attempt.agent_task_id) if attempt.agent_task_id else None,
        "channel": attempt.channel.value,
        "status": attempt.status.value,
        "message_text": attempt.message_text,
        "external_message_id": attempt.external_message_id,
        "error_message": attempt.error_message,
        "created_at": attempt.created_at,
        "updated_at": attempt.updated_at,
        "sent_at": attempt.sent_at,
        "completed_at": attempt.completed_at,
    }


def _contact_attempt_from_row(row) -> ContactAttempt:
    return ContactAttempt(
        id=_uuid(row["id"]),
        product_id=_uuid(row["product_id"]),
        supplier_contact_id=_uuid(row["supplier_contact_id"]),
        agent_task_id=_uuid(row.get("agent_task_id")),
        channel=ContactType(row["channel"]),
        status=ContactAttemptStatus(row["status"]),
        message_text=row["message_text"],
        external_message_id=row.get("external_message_id"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        sent_at=row.get("sent_at"),
        completed_at=row.get("completed_at"),
    )


def _conversation_message_row(message: ConversationMessage) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "product_id": str(message.product_id),
        "supplier_contact_id": str(message.supplier_contact_id),
        "contact_attempt_id": str(message.contact_attempt_id),
        "direction": message.direction.value,
        "channel": message.channel.value,
        "body": message.body,
        "subject": message.subject,
        "from_address": message.from_address,
        "to_address": message.to_address,
        "status": message.status.value,
        "external_message_id": message.external_message_id,
        "error_message": message.error_message,
        "requires_user_approval": message.requires_user_approval,
        "approval_reason": message.approval_reason,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
        "sent_at": message.sent_at,
        "provider_timestamp": message.provider_timestamp,
    }


def _conversation_message_from_row(row) -> ConversationMessage:
    return ConversationMessage(
        id=_uuid(row["id"]),
        product_id=_uuid(row["product_id"]),
        supplier_contact_id=_uuid(row["supplier_contact_id"]),
        contact_attempt_id=_uuid(row["contact_attempt_id"]),
        direction=ConversationDirection(row["direction"]),
        channel=ContactType(row["channel"]),
        body=row["body"],
        subject=row.get("subject"),
        from_address=row.get("from_address"),
        to_address=row.get("to_address"),
        status=ConversationMessageStatus(row["status"]),
        external_message_id=row.get("external_message_id"),
        error_message=row.get("error_message"),
        requires_user_approval=bool(row.get("requires_user_approval")),
        approval_reason=row.get("approval_reason"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        sent_at=row.get("sent_at"),
        provider_timestamp=row.get("provider_timestamp"),
    )


def _contract_draft_row(draft: ContractDraft) -> dict[str, Any]:
    return {
        "id": str(draft.id),
        "product_id": str(draft.product_id),
        "supplier_contact_id": str(draft.supplier_contact_id),
        "supplier_name": draft.supplier_name,
        "agent_task_id": str(draft.agent_task_id) if draft.agent_task_id else None,
        "status": draft.status.value,
        "title": draft.title,
        "extracted_data": draft.extracted_data,
        "draft_text": draft.draft_text,
        "file_name": draft.file_name,
        "content_type": draft.content_type,
        "error_message": draft.error_message,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
        "completed_at": draft.completed_at,
    }


def _contract_draft_from_row(row) -> ContractDraft:
    return ContractDraft(
        id=_uuid(row["id"]),
        product_id=_uuid(row["product_id"]),
        supplier_contact_id=_uuid(row["supplier_contact_id"]),
        supplier_name=row["supplier_name"],
        agent_task_id=_uuid(row.get("agent_task_id")),
        status=ContractDraftStatus(row["status"]),
        title=row["title"],
        extracted_data=dict(row.get("extracted_data") or {}),
        draft_text=row.get("draft_text"),
        file_name=row["file_name"],
        content_type=row["content_type"],
        error_message=row.get("error_message"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row.get("completed_at"),
    )
