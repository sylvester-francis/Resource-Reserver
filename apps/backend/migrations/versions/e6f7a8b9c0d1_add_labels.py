"""Add labels and resource_labels tables.

Revision ID: e6f7a8b9c0d1
Revises: d5407f13c497
Create Date: 2026-01-12 10:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5407f13c497"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create labels and resource_labels tables."""
    # Create labels table
    op.create_table(
        "labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("value", sa.String(200), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category", "value", name="uq_label_category_value"),
    )
    op.create_index("ix_labels_id", "labels", ["id"])
    op.create_index("ix_labels_category", "labels", ["category"])

    # Create resource_labels association table
    op.create_table(
        "resource_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["label_id"], ["labels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_id", "label_id", name="uq_resource_label"),
    )
    op.create_index("ix_resource_labels_id", "resource_labels", ["id"])
    op.create_index(
        "ix_resource_labels_resource_id", "resource_labels", ["resource_id"]
    )
    op.create_index("ix_resource_labels_label_id", "resource_labels", ["label_id"])


def downgrade() -> None:
    """Remove labels and resource_labels tables."""
    # Drop resource_labels table
    op.drop_index("ix_resource_labels_label_id", table_name="resource_labels")
    op.drop_index("ix_resource_labels_resource_id", table_name="resource_labels")
    op.drop_index("ix_resource_labels_id", table_name="resource_labels")
    op.drop_table("resource_labels")

    # Drop labels table
    op.drop_index("ix_labels_category", table_name="labels")
    op.drop_index("ix_labels_id", table_name="labels")
    op.drop_table("labels")
