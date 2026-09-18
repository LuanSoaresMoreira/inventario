"""Adiciona revogação de link público e dados mínimos do comunicante."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0006"
down_revision: str | None = "20260918_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "equipment",
        sa.Column("public_token_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("occurrences", sa.Column("reporter_name", sa.String(160), nullable=True))
    op.add_column(
        "occurrences", sa.Column("reporter_contact", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("occurrences", "reporter_contact")
    op.drop_column("occurrences", "reporter_name")
    op.drop_column("equipment", "public_token_revoked_at")
