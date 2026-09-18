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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
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
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserSession(TimestampMixin, Base):
    __tablename__ = "user_sessions"
    __table_args__ = (Index("ix_user_sessions_token_hash", "token_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Environment(TimestampMixin, Base):
    __tablename__ = "environments"
    __table_args__ = (
        Index("ix_environments_name", "name"),
        Index("ix_environments_kind_active", "kind", "active"),
    )

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
        Index("ix_equipment_kind_status", "kind", "status"),
        Index("ix_equipment_status_created", "status", "created_at"),
        Index("ix_equipment_next_maintenance", "next_maintenance_on"),
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
    public_token_revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class Movement(TimestampMixin, Base):
    __tablename__ = "movements"
    __table_args__ = (
        CheckConstraint(
            "origin_environment_id <> destination_environment_id",
            name="ck_movements_distinct_environments",
        ),
        Index("ix_movements_equipment_created", "equipment_id", "created_at"),
        Index("ix_movements_origin_created", "origin_environment_id", "created_at"),
        Index("ix_movements_destination_created", "destination_environment_id", "created_at"),
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
        Index("ix_occurrences_equipment_status", "equipment_id", "status"),
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
    reporter_name: Mapped[str | None] = mapped_column(String(160))
    reporter_contact: Mapped[str | None] = mapped_column(String(255))
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT")
    )
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
        Index("ix_maintenances_scheduled_status", "scheduled_for", "status"),
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


class OccurrenceComment(TimestampMixin, Base):
    __tablename__ = "occurrence_comments"
    __table_args__ = (Index("ix_occurrence_comments_occurrence", "occurrence_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    occurrence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occurrences.id", ondelete="RESTRICT"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)


class MaintenanceComponent(TimestampMixin, Base):
    __tablename__ = "maintenance_components"
    __table_args__ = (
        Index("ix_maintenance_components_maintenance", "maintenance_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    maintenance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("maintenances.id", ondelete="RESTRICT"), nullable=False
    )
    component_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    observation: Mapped[str | None] = mapped_column(Text)


class MaintenancePlan(TimestampMixin, Base):
    __tablename__ = "maintenance_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'simulated', 'approved', 'published', 'archived')",
            name="ck_maintenance_plans_status",
        ),
        UniqueConstraint("year", "version", name="uq_maintenance_plans_year_version"),
        Index("ix_maintenance_plans_year_status", "year", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    capacity_monthly: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    blackout_periods: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MaintenancePlanItem(TimestampMixin, Base):
    __tablename__ = "maintenance_plan_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'conflict', 'unallocated')",
            name="ck_maintenance_plan_items_status",
        ),
        UniqueConstraint("plan_id", "equipment_id", name="uq_maintenance_plan_items_equipment"),
        Index("ix_maintenance_plan_items_plan_date", "plan_id", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("maintenance_plans.id", ondelete="RESTRICT"), nullable=False
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_for: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)


class MaintenanceAlert(TimestampMixin, Base):
    __tablename__ = "maintenance_alerts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('upcoming', 'overdue')",
            name="ck_maintenance_alerts_kind",
        ),
        CheckConstraint(
            "status IN ('open', 'dispatched', 'failed')",
            name="ck_maintenance_alerts_status",
        ),
        UniqueConstraint("idempotency_key", name="uq_maintenance_alerts_idempotency"),
        Index("ix_maintenance_alerts_status_due", "status", "due_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    maintenance_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("maintenances.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    generated_for: Mapped[date] = mapped_column(Date, nullable=False)


class NotificationDelivery(TimestampMixin, Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('mock_email')",
            name="ck_notification_deliveries_channel",
        ),
        CheckConstraint(
            "status IN ('queued', 'sent', 'failed')",
            name="ck_notification_deliveries_status",
        ),
        UniqueConstraint("idempotency_key", name="uq_notification_deliveries_idempotency"),
        Index("ix_notification_deliveries_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("maintenance_alerts.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    recipient_label: Mapped[str] = mapped_column(String(160), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FailurePredictionPolicy(TimestampMixin, Base):
    __tablename__ = "failure_prediction_policies"
    __table_args__ = (
        CheckConstraint(
            "status IN ('disabled', 'enabled', 'retired')",
            name="ck_failure_prediction_policies_status",
        ),
        CheckConstraint("horizon_days BETWEEN 1 AND 365", name="ck_failure_prediction_policies_horizon"),
        CheckConstraint("min_history_count BETWEEN 0 AND 1000", name="ck_failure_prediction_policies_history"),
        CheckConstraint(
            "min_confidence >= 0 AND min_confidence <= 1",
            name="ck_failure_prediction_policies_confidence",
        ),
        UniqueConstraint("name", "version", name="uq_failure_prediction_policies_name_version"),
        Index("ix_failure_prediction_policies_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="disabled", nullable=False)
    baseline_version: Mapped[str] = mapped_column(String(80), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    min_history_count: Mapped[int] = mapped_column(Integer, nullable=False)
    min_confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    evaluation_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evaluation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )
    enabled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT")
    )
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disable_reason: Mapped[str | None] = mapped_column(Text)


class FailurePrediction(TimestampMixin, Base):
    __tablename__ = "failure_predictions"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('high', 'medium', 'low', 'abstain')",
            name="ck_failure_predictions_risk_level",
        ),
        CheckConstraint(
            "status IN ('recommended', 'confirmed', 'rejected', 'dismissed')",
            name="ck_failure_predictions_status",
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="ck_failure_predictions_score"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_failure_predictions_confidence",
        ),
        UniqueConstraint("idempotency_key", name="uq_failure_predictions_idempotency"),
        Index("ix_failure_predictions_policy_created", "policy_id", "created_at"),
        Index("ix_failure_predictions_equipment_status", "equipment_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("failure_prediction_policies.id", ondelete="RESTRICT"), nullable=False
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    generated_for: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_end: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="recommended", nullable=False)
    rationale: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    feature_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)


class PredictionEvaluation(TimestampMixin, Base):
    __tablename__ = "prediction_evaluations"
    __table_args__ = (
        UniqueConstraint("policy_id", "run_key", name="uq_prediction_evaluations_policy_run"),
        Index("ix_prediction_evaluations_policy_evaluated", "policy_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("failure_prediction_policies.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    run_key: Mapped[str] = mapped_column(String(255), nullable=False)
    evaluated_for: Mapped[date] = mapped_column(Date, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    labeled_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_precision: Mapped[float | None] = mapped_column(Numeric(5, 4))
    baseline_recall: Mapped[float | None] = mapped_column(Numeric(5, 4))
    heuristic_precision: Mapped[float | None] = mapped_column(Numeric(5, 4))
    heuristic_recall: Mapped[float | None] = mapped_column(Numeric(5, 4))
    false_positives: Mapped[int] = mapped_column(Integer, nullable=False)
    false_negatives: Mapped[int] = mapped_column(Integer, nullable=False)
    abstentions: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evaluated_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )


class PredictionNotification(TimestampMixin, Base):
    __tablename__ = "prediction_notifications"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('mock_email')",
            name="ck_prediction_notifications_channel",
        ),
        CheckConstraint(
            "status IN ('queued', 'sent', 'failed')",
            name="ck_prediction_notifications_status",
        ),
        UniqueConstraint("idempotency_key", name="uq_prediction_notifications_idempotency"),
        Index("ix_prediction_notifications_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("failure_predictions.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    recipient_label: Mapped[str] = mapped_column(String(160), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )


class EquipmentWarranty(TimestampMixin, Base):
    __tablename__ = "equipment_warranties"
    __table_args__ = (
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_equipment_warranties_period",
        ),
        Index("ix_equipment_warranties_equipment_ends", "equipment_id", "ends_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    supplier: Mapped[str] = mapped_column(String(160), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date)
    terms: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )


class MaintenanceCost(TimestampMixin, Base):
    __tablename__ = "maintenance_costs"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_maintenance_costs_amount_nonnegative"),
        CheckConstraint("char_length(currency) = 3", name="ck_maintenance_costs_currency"),
        Index("ix_maintenance_costs_equipment_created", "equipment_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    maintenance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("maintenances.id", ondelete="RESTRICT"), nullable=False
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("internal_users.id", ondelete="RESTRICT"), nullable=False
    )


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
