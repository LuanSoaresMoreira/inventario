"""Adiciona índices para o inventário de equipamentos."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260918_0004"
down_revision: str | None = "20260918_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_equipment_kind_status", "equipment", ["kind", "status"]
    )
    op.create_index(
        "ix_equipment_status_created", "equipment", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_equipment_status_created", table_name="equipment")
    op.drop_index("ix_equipment_kind_status", table_name="equipment")
