"""Adiciona índices para a rastreabilidade de movimentações."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260918_0005"
down_revision: str | None = "20260918_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_movements_origin_created",
        "movements",
        ["origin_environment_id", "created_at"],
    )
    op.create_index(
        "ix_movements_destination_created",
        "movements",
        ["destination_environment_id", "created_at"],
    )
    op.create_index(
        "ix_occurrences_equipment_status", "occurrences", ["equipment_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_occurrences_equipment_status", table_name="occurrences")
    op.drop_index("ix_movements_destination_created", table_name="movements")
    op.drop_index("ix_movements_origin_created", table_name="movements")
