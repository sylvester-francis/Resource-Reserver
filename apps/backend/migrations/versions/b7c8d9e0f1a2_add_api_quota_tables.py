"""Add API quota and usage tracking tables.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create API quota and usage log tables."""
    # Create api_quotas table
    op.create_table(
        "api_quotas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "tier", sa.String(20), nullable=False, server_default="authenticated"
        ),
        sa.Column("custom_rate_limit", sa.Integer(), nullable=True),
        sa.Column("custom_daily_quota", sa.Integer(), nullable=True),
        sa.Column(
            "daily_request_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_request_date", sa.Date(), nullable=True),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "quota_reset_notified", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_api_quotas_id", "api_quotas", ["id"])

    # Create api_usage_logs table
    op.create_table(
        "api_usage_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("rate_remaining", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_usage_logs_id", "api_usage_logs", ["id"])
    op.create_index("ix_api_usage_logs_timestamp", "api_usage_logs", ["timestamp"])


def downgrade() -> None:
    """Drop API quota and usage log tables."""
    op.drop_index("ix_api_usage_logs_timestamp", table_name="api_usage_logs")
    op.drop_index("ix_api_usage_logs_id", table_name="api_usage_logs")
    op.drop_table("api_usage_logs")

    op.drop_index("ix_api_quotas_id", table_name="api_quotas")
    op.drop_table("api_quotas")
