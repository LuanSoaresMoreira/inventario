"""Adiciona garantias e custos informativos de manutenção."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0011"
down_revision: str | None = "20260918_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "equipment_warranties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("supplier", sa.String(length=160), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_equipment_warranties_period",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equipment_warranties_equipment_ends",
        "equipment_warranties",
        ["equipment_id", "ends_on"],
    )
    op.create_table(
        "maintenance_costs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("maintenance_id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "amount >= 0", name="ck_maintenance_costs_amount_nonnegative"
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3", name="ck_maintenance_costs_currency"
        ),
        sa.ForeignKeyConstraint(
            ["maintenance_id"], ["maintenances.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maintenance_costs_equipment_created",
        "maintenance_costs",
        ["equipment_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maintenance_costs_equipment_created", table_name="maintenance_costs"
    )
    op.drop_table("maintenance_costs")
    op.drop_index(
        "ix_equipment_warranties_equipment_ends", table_name="equipment_warranties"
    )
    op.drop_table("equipment_warranties")
