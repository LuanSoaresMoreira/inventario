"""Adiciona índices para o catálogo de ambientes."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260918_0003"
down_revision: str | None = "20260918_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_environments_name", "environments", ["name"])
    op.create_index(
        "ix_environments_kind_active", "environments", ["kind", "active"]
    )


def downgrade() -> None:
    op.drop_index("ix_environments_kind_active", table_name="environments")
    op.drop_index("ix_environments_name", table_name="environments")
