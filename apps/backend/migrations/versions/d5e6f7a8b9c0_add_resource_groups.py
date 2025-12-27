"""Add resource groups and resource hierarchy.

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create resource groups table and add hierarchy columns to resources."""
    # Create resource_groups table
    op.create_table(
        "resource_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("building", sa.String(200), nullable=True),
        sa.Column("floor", sa.String(50), nullable=True),
        sa.Column("room", sa.String(100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["resource_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_groups_id", "resource_groups", ["id"])
    op.create_index("ix_resource_groups_parent_id", "resource_groups", ["parent_id"])
    op.create_index("ix_resource_groups_building", "resource_groups", ["building"])

    # Add group_id and parent_id columns to resources table
    op.add_column(
        "resources",
        sa.Column("group_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "resources",
        sa.Column("parent_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_resources_group_id",
        "resources",
        "resource_groups",
        ["group_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_resources_parent_id",
        "resources",
        "resources",
        ["parent_id"],
        ["id"],
    )
    op.create_index("ix_resources_group_id", "resources", ["group_id"])
    op.create_index("ix_resources_parent_id", "resources", ["parent_id"])


def downgrade() -> None:
    """Remove resource groups and hierarchy columns."""
    # Remove indexes and foreign keys from resources
    op.drop_index("ix_resources_parent_id", table_name="resources")
    op.drop_index("ix_resources_group_id", table_name="resources")
    op.drop_constraint("fk_resources_parent_id", "resources", type_="foreignkey")
    op.drop_constraint("fk_resources_group_id", "resources", type_="foreignkey")
    op.drop_column("resources", "parent_id")
    op.drop_column("resources", "group_id")

    # Drop resource_groups table
    op.drop_index("ix_resource_groups_building", table_name="resource_groups")
    op.drop_index("ix_resource_groups_parent_id", table_name="resource_groups")
    op.drop_index("ix_resource_groups_id", table_name="resource_groups")
    op.drop_table("resource_groups")
