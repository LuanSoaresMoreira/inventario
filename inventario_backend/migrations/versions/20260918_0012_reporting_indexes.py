"""Adiciona índices para consultas de planejamento, alertas e relatórios."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260918_0012"
down_revision: str | None = "20260918_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_equipment_next_maintenance", "equipment", ["next_maintenance_on"]
    )
    op.create_index(
        "ix_maintenances_scheduled_status",
        "maintenances",
        ["scheduled_for", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maintenances_scheduled_status", table_name="maintenances"
    )
    op.drop_index("ix_equipment_next_maintenance", table_name="equipment")
