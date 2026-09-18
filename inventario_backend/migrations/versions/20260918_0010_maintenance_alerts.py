"""Adiciona alertas idempotentes e entregas de notificação mock."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0010"
down_revision: str | None = "20260918_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "maintenance_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("maintenance_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generated_for", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('upcoming', 'overdue')", name="ck_maintenance_alerts_kind"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'dispatched', 'failed')",
            name="ck_maintenance_alerts_status",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["maintenance_id"], ["maintenances.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_maintenance_alerts_idempotency"),
    )
    op.create_index(
        "ix_maintenance_alerts_status_due",
        "maintenance_alerts",
        ["status", "due_on"],
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recipient_label", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "channel IN ('mock_email')", name="ck_notification_deliveries_channel"
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'sent', 'failed')",
            name="ck_notification_deliveries_status",
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"], ["maintenance_alerts.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_notification_deliveries_idempotency"
        ),
    )
    op.create_index(
        "ix_notification_deliveries_status_created",
        "notification_deliveries",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_deliveries_status_created",
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")
    op.drop_index("ix_maintenance_alerts_status_due", table_name="maintenance_alerts")
    op.drop_table("maintenance_alerts")
