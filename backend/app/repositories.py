from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from .domain import AgentTask, ContactAttempt, ContractDraft, ConversationMessage, Product, SearchRequest, SupplierContact


@dataclass
class InMemoryContractsRepository:
    contract_drafts: dict[UUID, ContractDraft] = field(default_factory=dict)

    def add_contract_draft(self, draft: ContractDraft) -> ContractDraft:
        self.contract_drafts[draft.id] = draft
        return draft

    def get_contract_draft(self, draft_id: UUID) -> ContractDraft | None:
        return self.contract_drafts.get(draft_id)

    def list_contract_drafts_for_product(self, product_id: UUID) -> list[ContractDraft]:
        return sorted(
            (draft for draft in self.contract_drafts.values() if draft.product_id == product_id),
            key=lambda draft: draft.created_at,
            reverse=True,
        )


@dataclass
class InMemoryRepository:
    search_requests: dict[UUID, SearchRequest] = field(default_factory=dict)
    agent_tasks: dict[UUID, AgentTask] = field(default_factory=dict)
    products: dict[UUID, Product] = field(default_factory=dict)
    supplier_contacts: dict[UUID, SupplierContact] = field(default_factory=dict)
    contact_attempts: dict[UUID, ContactAttempt] = field(default_factory=dict)
    conversation_messages: dict[UUID, ConversationMessage] = field(default_factory=dict)
    contracts: InMemoryContractsRepository = field(default_factory=InMemoryContractsRepository)

    def add_search_request(self, request: SearchRequest) -> SearchRequest:
        self.search_requests[request.id] = request
        return request

    def get_search_request(self, request_id: UUID) -> SearchRequest | None:
        return self.search_requests.get(request_id)

    def list_search_requests(self) -> list[SearchRequest]:
        return sorted(self.search_requests.values(), key=lambda request: request.created_at, reverse=True)

    def add_agent_task(self, task: AgentTask) -> AgentTask:
        self.agent_tasks[task.id] = task
        return task

    def get_agent_task(self, task_id: UUID) -> AgentTask | None:
        return self.agent_tasks.get(task_id)

    def add_product(self, product: Product) -> Product:
        self.products[product.id] = product
        for contact in product.contacts:
            self.add_supplier_contact(contact)
        return product

    def get_product(self, product_id: UUID) -> Product | None:
        return self.products.get(product_id)

    def list_products_for_request(self, search_request_id: UUID) -> list[Product]:
        return [
            product
            for product in self.products.values()
            if product.search_request_id == search_request_id
        ]

    def add_supplier_contact(self, contact: SupplierContact) -> SupplierContact:
        self.supplier_contacts[contact.id] = contact
        return contact

    def list_contacts_for_product(self, product_id: UUID) -> list[SupplierContact]:
        return [
            contact
            for contact in self.supplier_contacts.values()
            if contact.product_id == product_id
        ]

    def add_contact_attempt(self, attempt: ContactAttempt) -> ContactAttempt:
        self.contact_attempts[attempt.id] = attempt
        return attempt

    def list_attempts_for_product(self, product_id: UUID) -> list[ContactAttempt]:
        return [
            attempt
            for attempt in self.contact_attempts.values()
            if attempt.product_id == product_id
        ]

    def add_conversation_message(self, message: ConversationMessage) -> ConversationMessage:
        self.conversation_messages[message.id] = message
        return message

    def list_conversation_messages_for_product(self, product_id: UUID) -> list[ConversationMessage]:
        return sorted(
            (
                message
                for message in self.conversation_messages.values()
                if message.product_id == product_id
            ),
            key=lambda message: message.created_at,
        )
