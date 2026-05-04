"""Add per-request product result limit.

Revision ID: 0003_search_request_max_results
Revises: 0002_conversation_messages
Create Date: 2026-05-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_search_request_max_results"
down_revision = "0002_conversation_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "search_requests",
        sa.Column("max_results", sa.Integer(), nullable=False, server_default=sa.text("5")),
    )


def downgrade() -> None:
    op.drop_column("search_requests", "max_results")
