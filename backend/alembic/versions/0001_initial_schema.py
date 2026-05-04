"""Initial Product Sourcing MVP schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_payload", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "task_type IN ('product_search', 'supplier_contact')",
            name="agent_tasks_type_check",
        ),
    )

    op.create_table(
        "search_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("agent_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "search_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("search_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("product_url", sa.Text(), nullable=False),
        sa.Column("source_domain", sa.Text(), nullable=True),
        sa.Column("supplier_name", sa.Text(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw_agent_payload", postgresql.JSONB(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("search_request_id", "product_url", name="uq_products_request_product_url"),
    )

    op.create_table(
        "supplier_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("contact_type", sa.String(length=32), nullable=False),
        sa.Column("contact_value", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "contact_type IN ('email', 'telegram')",
            name="supplier_contacts_type_check",
        ),
    )

    op.create_table(
        "contact_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("supplier_contacts.id"),
            nullable=False,
        ),
        sa.Column("agent_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id"), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("external_message_id", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "channel IN ('email', 'telegram')",
            name="contact_attempts_channel_check",
        ),
    )

    op.create_index("idx_agent_tasks_status", "agent_tasks", ["status"])
    op.create_index("idx_search_requests_status", "search_requests", ["status"])
    op.create_index("idx_products_search_request_id", "products", ["search_request_id"])
    op.create_index("idx_supplier_contacts_product_id", "supplier_contacts", ["product_id"])
    op.create_index("idx_contact_attempts_product_id", "contact_attempts", ["product_id"])


def downgrade() -> None:
    op.drop_index("idx_contact_attempts_product_id", table_name="contact_attempts")
    op.drop_index("idx_supplier_contacts_product_id", table_name="supplier_contacts")
    op.drop_index("idx_products_search_request_id", table_name="products")
    op.drop_index("idx_search_requests_status", table_name="search_requests")
    op.drop_index("idx_agent_tasks_status", table_name="agent_tasks")

    op.drop_table("contact_attempts")
    op.drop_table("supplier_contacts")
    op.drop_table("products")
    op.drop_table("search_requests")
    op.drop_table("agent_tasks")

