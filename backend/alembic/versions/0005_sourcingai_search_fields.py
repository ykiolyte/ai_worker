"""Add SourcingAI-like search and product fields.

Revision ID: 0005_sourcingai_search_fields
Revises: 0004_conversation_message_provider_timestamp
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_sourcingai_search_fields"
down_revision = "0004_conversation_message_provider_timestamp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("search_requests", sa.Column("normalized_intent", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("search_requests", sa.Column("missing_fields", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("search_requests", sa.Column("clarifying_questions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("search_requests", sa.Column("common_filters", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("search_requests", sa.Column("product_attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("search_requests", sa.Column("sourcing_guidance", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("search_requests", sa.Column("suppliers_count", sa.Integer(), nullable=False, server_default=sa.text("0")))

    op.add_column("products", sa.Column("moq", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("price_range", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("fit_score", sa.Numeric(5, 4), nullable=True))
    op.add_column("products", sa.Column("fit_summary", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("matched_requirements", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("products", sa.Column("missing_requirements", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("products", sa.Column("supplier_badges", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("products", sa.Column("supplier_country", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("supplier_city", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("is_verified_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("products", sa.Column("is_audited_supplier", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("products", sa.Column("supports_customization", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("products", sa.Column("sample_available", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_check_constraint("products_fit_score_range_check", "products", "fit_score IS NULL OR (fit_score >= 0 AND fit_score <= 1)")

    op.drop_constraint("agent_tasks_type_check", "agent_tasks", type_="check")
    op.create_check_constraint(
        "agent_tasks_type_check",
        "agent_tasks",
        "task_type IN ('product_search', 'supplier_contact', 'contract_draft')",
    )
    op.create_table(
        "contract_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_contacts.id"), nullable=False),
        sa.Column("supplier_name", sa.Text(), nullable=False),
        sa.Column("agent_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("extracted_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("draft_text", sa.Text(), nullable=True),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'ready', 'failed', 'cancelled')",
            name="contract_drafts_status_check",
        ),
    )
    op.create_index("idx_contract_drafts_product_id", "contract_drafts", ["product_id"])


def downgrade() -> None:
    op.drop_index("idx_contract_drafts_product_id", table_name="contract_drafts")
    op.drop_table("contract_drafts")
    op.drop_constraint("agent_tasks_type_check", "agent_tasks", type_="check")
    op.create_check_constraint(
        "agent_tasks_type_check",
        "agent_tasks",
        "task_type IN ('product_search', 'supplier_contact')",
    )
    op.drop_constraint("products_fit_score_range_check", "products", type_="check")
    for column in [
        "sample_available",
        "supports_customization",
        "is_audited_supplier",
        "is_verified_supplier",
        "supplier_city",
        "supplier_country",
        "supplier_badges",
        "missing_requirements",
        "matched_requirements",
        "fit_summary",
        "fit_score",
        "price_range",
        "moq",
    ]:
        op.drop_column("products", column)
    for column in [
        "suppliers_count",
        "sourcing_guidance",
        "product_attributes",
        "common_filters",
        "clarifying_questions",
        "missing_fields",
        "normalized_intent",
    ]:
        op.drop_column("search_requests", column)
