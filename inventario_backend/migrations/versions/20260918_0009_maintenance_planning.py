"""Adiciona versões e itens do planejamento preventivo anual."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0009"
down_revision: str | None = "20260918_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "maintenance_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("capacity_monthly", sa.JSON(), nullable=False),
        sa.Column("blackout_periods", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'simulated', 'approved', 'published', 'archived')",
            name="ck_maintenance_plans_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "version", name="uq_maintenance_plans_year_version"),
    )
    op.create_index(
        "ix_maintenance_plans_year_status",
        "maintenance_plans",
        ["year", "status"],
    )
    op.create_table(
        "maintenance_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'conflict', 'unallocated')",
            name="ck_maintenance_plan_items_status",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["maintenance_plans.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "equipment_id", name="uq_maintenance_plan_items_equipment"),
    )
    op.create_index(
        "ix_maintenance_plan_items_plan_date",
        "maintenance_plan_items",
        ["plan_id", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maintenance_plan_items_plan_date", table_name="maintenance_plan_items"
    )
    op.drop_table("maintenance_plan_items")
    op.drop_index("ix_maintenance_plans_year_status", table_name="maintenance_plans")
    op.drop_table("maintenance_plans")
