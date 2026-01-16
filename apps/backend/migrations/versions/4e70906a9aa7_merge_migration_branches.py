"""merge migration branches

Revision ID: 4e70906a9aa7
Revises: d5e6f7a8b9c0, f8a9b0c1d2e3
Create Date: 2026-01-15 23:58:17.686479

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "4e70906a9aa7"
down_revision: str | Sequence[str] | None = ("d5e6f7a8b9c0", "f8a9b0c1d2e3")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
