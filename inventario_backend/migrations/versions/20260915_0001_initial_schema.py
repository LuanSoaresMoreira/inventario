"""Cria o esquema inicial de inventário.

Revision ID: 20260915_0001
Revises:
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "internal_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('it', 'management', 'administration')",
            name="ck_internal_users_role",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_subject"),
    )
    op.create_table(
        "environments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "equipment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_token", sa.Uuid(), nullable=False),
        sa.Column("asset_tag", sa.String(length=80), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("registered_by_id", sa.Uuid(), nullable=False),
        sa.Column("last_maintenance_on", sa.Date(), nullable=True),
        sa.Column("next_maintenance_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('computer', 'projector', 'air_conditioner', 'remote_control', 'other')",
            name="ck_equipment_kind",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'maintenance', 'inactive')",
            name="ck_equipment_status",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["environments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["registered_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag"),
        sa.UniqueConstraint("public_token"),
    )
    op.create_index("ix_equipment_location_id", "equipment", ["location_id"])
    op.create_table(
        "occurrences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_tracking_token", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_occurrences_priority",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_occurrences_status",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"], ["environments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_tracking_token"),
    )
    op.create_index(
        "ix_occurrences_status_created", "occurrences", ["status", "created_at"]
    )
    op.create_table(
        "movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("origin_environment_id", sa.Uuid(), nullable=False),
        sa.Column("destination_environment_id", sa.Uuid(), nullable=False),
        sa.Column("moved_by_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "origin_environment_id <> destination_environment_id",
            name="ck_movements_distinct_environments",
        ),
        sa.ForeignKeyConstraint(
            ["destination_environment_id"], ["environments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["moved_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["origin_environment_id"], ["environments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_movements_equipment_created", "movements", ["equipment_id", "created_at"]
    )
    op.create_table(
        "maintenances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("technician_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_for", sa.Date(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('preventive', 'corrective')", name="ck_maintenances_kind"
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
            name="ck_maintenances_status",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["occurrences.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["technician_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maintenances_equipment_created",
        "maintenances",
        ["equipment_id", "created_at"],
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_events_entity",
        "audit_events",
        ["entity_type", "entity_id", "occurred_at"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_audit_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_event_mutation()")
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_maintenances_equipment_created", table_name="maintenances")
    op.drop_table("maintenances")
    op.drop_index("ix_movements_equipment_created", table_name="movements")
    op.drop_table("movements")
    op.drop_index("ix_occurrences_status_created", table_name="occurrences")
    op.drop_table("occurrences")
    op.drop_index("ix_equipment_location_id", table_name="equipment")
    op.drop_table("equipment")
    op.drop_table("environments")
    op.drop_table("internal_users")
