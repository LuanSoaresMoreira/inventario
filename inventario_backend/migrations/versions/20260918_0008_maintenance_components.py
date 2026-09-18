"""Adiciona componentes substituídos em manutenções."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0008"
down_revision: str | None = "20260918_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "maintenance_components",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("maintenance_id", sa.Uuid(), nullable=False),
        sa.Column("component_name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["maintenance_id"], ["maintenances.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maintenance_components_maintenance",
        "maintenance_components",
        ["maintenance_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maintenance_components_maintenance", table_name="maintenance_components"
    )
    op.drop_table("maintenance_components")
