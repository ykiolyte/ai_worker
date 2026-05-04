"""Add supplier conversation message timeline.

Revision ID: 0002_conversation_messages
Revises: 0001_initial_schema
Create Date: 2026-05-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_conversation_messages"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contact_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("supplier_contacts.id"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("from_address", sa.Text(), nullable=True),
        sa.Column("to_address", sa.Text(), nullable=True),
        sa.Column("external_message_id", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "direction IN ('outbound', 'inbound')",
            name="conversation_messages_direction_check",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'sent', 'failed', 'received')",
            name="conversation_messages_status_check",
        ),
        sa.CheckConstraint(
            "channel IN ('email', 'telegram')",
            name="conversation_messages_channel_check",
        ),
    )
    op.create_index("idx_conversation_messages_product_id", "conversation_messages", ["product_id"])
    op.create_index(
        "idx_conversation_messages_contact_attempt_id",
        "conversation_messages",
        ["contact_attempt_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_conversation_messages_contact_attempt_id", table_name="conversation_messages")
    op.drop_index("idx_conversation_messages_product_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
