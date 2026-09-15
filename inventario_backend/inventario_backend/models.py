import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base compartilhada pelos modelos persistidos."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InternalUser(TimestampMixin, Base):
    __tablename__ = "internal_users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('it', 'management', 'administration')",
            name="ck_internal_users_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Environment(TimestampMixin, Base):
    __tablename__ = "environments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Equipment(TimestampMixin, Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('computer', 'projector', 'air_conditioner', "
            "'remote_control', 'other')",
            name="ck_equipment_kind",
        ),
        CheckConstraint(
            "status IN ('active', 'maintenance', 'inactive')",
            name="ck_equipment_status",
        ),
        Index("ix_equipment_location_id", "location_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    public_token: Mapped[uuid.UUID] = mapped_column(
        Uuid, unique=True, default=uuid.uuid4, nullable=False
    )
    asset_tag: Mapped[str | None] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), nullable=False
    )
    registered_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )
    last_maintenance_on: Mapped[date | None] = mapped_column(Date)
    next_maintenance_on: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Movement(TimestampMixin, Base):
    __tablename__ = "movements"
    __table_args__ = (
        CheckConstraint(
            "origin_environment_id <> destination_environment_id",
            name="ck_movements_distinct_environments",
        ),
        Index("ix_movements_equipment_created", "equipment_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    origin_environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), nullable=False
    )
    destination_environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), nullable=False
    )
    moved_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class Occurrence(TimestampMixin, Base):
    __tablename__ = "occurrences"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_occurrences_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_occurrences_priority",
        ),
        Index("ix_occurrences_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    public_tracking_token: Mapped[uuid.UUID] = mapped_column(
        Uuid, unique=True, default=uuid.uuid4, nullable=False
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT")
    )


class Maintenance(TimestampMixin, Base):
    __tablename__ = "maintenances"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('preventive', 'corrective')",
            name="ck_maintenances_kind",
        ),
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
            name="ck_maintenances_status",
        ),
        Index("ix_maintenances_equipment_created", "equipment_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occurrences.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    technician_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT")
    )
    scheduled_for: Mapped[date | None] = mapped_column(Date)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    procedure: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity", "entity_type", "entity_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT")
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_state: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
