"""Add provider timestamp to conversation messages.

Revision ID: 0004_conversation_message_provider_timestamp
Revises: 0003_search_request_max_results
Create Date: 2026-05-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_conversation_message_provider_timestamp"
down_revision = "0003_search_request_max_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation_messages",
        sa.Column("provider_timestamp", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_messages", "provider_timestamp")
