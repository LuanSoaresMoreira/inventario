import calendar
import csv
import io
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import threading
import time
from typing import Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import ValidationError
import qrcode
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from inventario_backend.config import get_settings
from inventario_backend.database import check_database, get_db
from inventario_backend.models import (
    AuditEvent,
    Equipment,
    Environment,
    InternalUser,
    Maintenance,
    MaintenanceComponent,
    MaintenanceAlert,
    MaintenanceCost,
    MaintenancePlan,
    MaintenancePlanItem,
    EquipmentWarranty,
    FailurePrediction,
    FailurePredictionPolicy,
    Movement,
    NotificationDelivery,
    Occurrence,
    OccurrenceComment,
    PredictionEvaluation,
    PredictionNotification,
)
from inventario_backend.security import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    AuthContext,
    ROLE_PERMISSIONS,
    create_session,
    require_csrf,
    require_permission,
    revoke_session,
    verify_password,
)


class HealthResponse(BaseModel):
    status: str
    service: str


class LoginRequest(BaseModel):
    auth_subject: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class UserResponse(BaseModel):
    id: UUID
    display_name: str
    role: str
    permissions: list[str]


class SessionResponse(BaseModel):
    user: UserResponse
    expires_at: datetime


class RoleChangeRequest(BaseModel):
    role: Literal["it", "management", "administration"]
    reason: str = Field(min_length=3, max_length=500)


class EnvironmentCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("code", "name", "kind", "reason", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class EnvironmentUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: str | None = Field(default=None, min_length=1, max_length=64)
    active: bool | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("code", "name", "kind", "reason", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self) -> "EnvironmentUpdateRequest":
        if self.code is None and self.name is None and self.kind is None and self.active is None:
            raise ValueError("at least one environment field must change")
        return self


class EnvironmentResponse(BaseModel):
    id: UUID
    code: str
    name: str
    kind: str
    active: bool
    created_at: datetime


class EnvironmentListResponse(BaseModel):
    items: list[EnvironmentResponse]
    total: int
    limit: int
    offset: int


EquipmentKind = Literal[
    "computer", "projector", "air_conditioner", "remote_control", "other"
]
EquipmentStatus = Literal["active", "maintenance", "inactive"]


class EquipmentCreateRequest(BaseModel):
    kind: EquipmentKind
    asset_tag: str | None = Field(default=None, max_length=80)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    location_id: UUID
    last_maintenance_on: date | None = None
    next_maintenance_on: date | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("asset_tag", "brand", "model", "reason", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return None if stripped == "" and value != "reason" else stripped

    @model_validator(mode="after")
    def validate_maintenance_dates(self) -> "EquipmentCreateRequest":
        if (
            self.last_maintenance_on is not None
            and self.next_maintenance_on is not None
            and self.next_maintenance_on < self.last_maintenance_on
        ):
            raise ValueError("next maintenance date cannot precede last maintenance date")
        return self


class EquipmentUpdateRequest(BaseModel):
    kind: EquipmentKind | None = None
    asset_tag: str | None = Field(default=None, max_length=80)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    location_id: UUID | None = None
    status: EquipmentStatus | None = None
    last_maintenance_on: date | None = None
    next_maintenance_on: date | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("asset_tag", "brand", "model", "reason", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return None if stripped == "" and value != "reason" else stripped

    @model_validator(mode="after")
    def validate_update(self) -> "EquipmentUpdateRequest":
        if not (self.model_fields_set - {"reason"}):
            raise ValueError("at least one equipment field must change")
        if (
            self.last_maintenance_on is not None
            and self.next_maintenance_on is not None
            and self.next_maintenance_on < self.last_maintenance_on
        ):
            raise ValueError("next maintenance date cannot precede last maintenance date")
        return self


class EquipmentResponse(BaseModel):
    id: UUID
    asset_tag: str | None
    kind: EquipmentKind
    brand: str | None
    model: str | None
    status: EquipmentStatus
    location_id: UUID
    registered_by_id: UUID
    last_maintenance_on: date | None
    next_maintenance_on: date | None
    active: bool
    created_at: datetime
    occurrence_count: int = 0
    maintenance_count: int = 0


class EquipmentListResponse(BaseModel):
    items: list[EquipmentResponse]
    total: int
    limit: int
    offset: int


class MovementCreateRequest(BaseModel):
    origin_environment_id: UUID
    destination_environment_id: UUID
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MovementResponse(BaseModel):
    id: UUID
    equipment_id: UUID
    origin_environment_id: UUID
    destination_environment_id: UUID
    moved_by_id: UUID
    reason: str
    created_at: datetime


class MovementListResponse(BaseModel):
    items: list[MovementResponse]
    total: int
    limit: int
    offset: int


class PublicReportRequest(BaseModel):
    description: str = Field(min_length=5, max_length=2000)
    reporter_name: str | None = Field(default=None, max_length=160)
    reporter_contact: str | None = Field(default=None, max_length=255)

    @field_validator("description", "reporter_name", "reporter_contact", mode="before")
    @classmethod
    def strip_public_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None


class PublicReportFormResponse(BaseModel):
    message: str


class PublicReportResponse(BaseModel):
    message: str
    tracking_token: UUID


class PublicTrackingResponse(BaseModel):
    status: Literal["received"]
    message: str


class PublicAccessResponse(BaseModel):
    public_url: str
    qr_svg: str
    revoked: bool


OccurrenceStatus = Literal["open", "in_progress", "resolved", "closed"]
OccurrencePriority = Literal["low", "normal", "high", "urgent"]


class OccurrenceUpdateRequest(BaseModel):
    status: OccurrenceStatus | None = None
    priority: OccurrencePriority | None = None
    assigned_to_id: UUID | None = None
    resolution_reason: str | None = Field(default=None, min_length=3, max_length=1000)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("resolution_reason", "reason", mode="before")
    @classmethod
    def strip_occurrence_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self) -> "OccurrenceUpdateRequest":
        if not (self.model_fields_set - {"reason"}):
            raise ValueError("at least one occurrence field must change")
        return self


class OccurrenceCreateRequest(BaseModel):
    equipment_id: UUID
    description: str = Field(min_length=5, max_length=2000)
    priority: OccurrencePriority = "normal"
    reporter_name: str | None = Field(default=None, max_length=160)
    reporter_contact: str | None = Field(default=None, max_length=255)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator(
        "description", "reporter_name", "reporter_contact", "reason", mode="before"
    )
    @classmethod
    def strip_create_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None


class OccurrenceCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("body", mode="before")
    @classmethod
    def strip_comment(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class OccurrenceCommentResponse(BaseModel):
    id: UUID
    occurrence_id: UUID
    author_id: UUID
    body: str
    created_at: datetime


class OccurrenceHistoryResponse(BaseModel):
    id: UUID
    action: str
    actor_id: UUID | None
    previous_state: dict[str, object] | None
    new_state: dict[str, object] | None
    reason: str | None
    occurred_at: datetime


class OccurrenceResponse(BaseModel):
    id: UUID
    public_tracking_token: UUID
    equipment_id: UUID
    environment_id: UUID
    description: str
    status: OccurrenceStatus
    priority: OccurrencePriority
    assigned_to_id: UUID | None
    reporter_name: str | None
    reporter_contact: str | None
    resolution_reason: str | None
    closed_at: datetime | None
    created_at: datetime


class OccurrenceDetailResponse(OccurrenceResponse):
    comments: list[OccurrenceCommentResponse]
    history: list[OccurrenceHistoryResponse]


class OccurrenceListResponse(BaseModel):
    items: list[OccurrenceResponse]
    total: int
    limit: int
    offset: int


MaintenanceKind = Literal["preventive", "corrective"]
MaintenanceStatus = Literal["planned", "in_progress", "completed", "cancelled"]


class MaintenanceCreateRequest(BaseModel):
    equipment_id: UUID
    occurrence_id: UUID | None = None
    kind: MaintenanceKind
    technician_id: UUID | None = None
    scheduled_for: date | None = None
    procedure: str | None = Field(default=None, max_length=5000)
    result: str | None = Field(default=None, max_length=5000)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("procedure", "result", "reason", mode="before")
    @classmethod
    def strip_maintenance_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None


class MaintenanceUpdateRequest(BaseModel):
    status: MaintenanceStatus | None = None
    technician_id: UUID | None = None
    scheduled_for: date | None = None
    procedure: str | None = Field(default=None, max_length=5000)
    result: str | None = Field(default=None, max_length=5000)
    next_maintenance_on: date | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("procedure", "result", "reason", mode="before")
    @classmethod
    def strip_update_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def require_change(self) -> "MaintenanceUpdateRequest":
        if not (self.model_fields_set - {"reason"}):
            raise ValueError("at least one maintenance field must change")
        return self


class MaintenanceComponentCreateRequest(BaseModel):
    component_name: str = Field(min_length=1, max_length=160)
    quantity: int = Field(default=1, ge=1, le=100000)
    observation: str | None = Field(default=None, max_length=2000)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("component_name", "observation", "reason", mode="before")
    @classmethod
    def strip_component_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None


class MaintenanceComponentResponse(BaseModel):
    id: UUID
    maintenance_id: UUID
    component_name: str
    quantity: int
    observation: str | None
    created_at: datetime


class MaintenanceResponse(BaseModel):
    id: UUID
    equipment_id: UUID
    occurrence_id: UUID | None
    kind: MaintenanceKind
    status: MaintenanceStatus
    technician_id: UUID | None
    scheduled_for: date | None
    started_at: datetime | None
    completed_at: datetime | None
    procedure: str | None
    result: str | None
    created_at: datetime
    components: list[MaintenanceComponentResponse] = Field(default_factory=list)


class MaintenanceListResponse(BaseModel):
    items: list[MaintenanceResponse]
    total: int
    limit: int
    offset: int


PlanStatus = Literal["draft", "simulated", "approved", "published", "archived"]
PlanItemStatus = Literal["planned", "conflict", "unallocated"]


class BlackoutPeriodRequest(BaseModel):
    starts_on: date
    ends_on: date
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_blackout_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_period(self) -> "BlackoutPeriodRequest":
        if self.ends_on < self.starts_on:
            raise ValueError("blackout end must not precede start")
        return self


def _default_monthly_capacity() -> dict[str, int]:
    return {str(month): 10 for month in range(1, 13)}


class MaintenancePlanCreateRequest(BaseModel):
    year: int = Field(ge=2020, le=2100)
    capacity_monthly: dict[str, int] = Field(default_factory=_default_monthly_capacity)
    blackout_periods: list[BlackoutPeriodRequest] = Field(default_factory=list, max_length=100)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("capacity_monthly")
    @classmethod
    def validate_capacity(cls, value: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for month, capacity in value.items():
            if str(month) not in {str(number) for number in range(1, 13)}:
                raise ValueError("capacity_monthly keys must be months 1 through 12")
            if capacity < 0 or capacity > 10000:
                raise ValueError("monthly capacity must be between 0 and 10000")
            normalized[str(month)] = capacity
        return {str(month): normalized.get(str(month), 0) for month in range(1, 13)}

    @field_validator("reason", mode="before")
    @classmethod
    def strip_plan_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MaintenancePlanApprovalRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_plan_approval_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MaintenancePlanItemResponse(BaseModel):
    id: UUID
    plan_id: UUID
    equipment_id: UUID
    environment_id: UUID
    scheduled_for: date | None
    status: PlanItemStatus
    justification: str
    created_at: datetime


class MaintenancePlanResponse(BaseModel):
    id: UUID
    year: int
    version: int
    status: PlanStatus
    capacity_monthly: dict[str, int]
    blackout_periods: list[dict[str, object]]
    summary: dict[str, object] | None
    created_by_id: UUID
    approved_by_id: UUID | None
    approved_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    items: list[MaintenancePlanItemResponse] = Field(default_factory=list)


class MaintenancePlanListResponse(BaseModel):
    items: list[MaintenancePlanResponse]
    total: int
    limit: int
    offset: int


AlertKind = Literal["upcoming", "overdue"]
AlertStatus = Literal["open", "dispatched", "failed"]


class MaintenanceAlertResponse(BaseModel):
    id: UUID
    equipment_id: UUID
    maintenance_id: UUID | None
    kind: AlertKind
    due_on: date
    idempotency_key: str
    status: AlertStatus
    generated_for: date
    created_at: datetime


class MaintenanceAlertListResponse(BaseModel):
    items: list[MaintenanceAlertResponse]
    total: int
    limit: int
    offset: int


class MaintenanceAlertGenerationResponse(BaseModel):
    created: int
    items: list[MaintenanceAlertResponse]


class MaintenanceAlertGenerateRequest(BaseModel):
    as_of: date | None = None
    upcoming_days: int = Field(default=30, ge=1, le=365)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_alert_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class NotificationDispatchRequest(BaseModel):
    recipient_label: str = Field(default="ti-institucional-ficticio", min_length=3, max_length=160)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("recipient_label", "reason", mode="before")
    @classmethod
    def strip_dispatch_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class NotificationDeliveryResponse(BaseModel):
    id: UUID
    alert_id: UUID
    channel: Literal["mock_email"]
    recipient_label: str
    idempotency_key: str
    status: Literal["queued", "sent", "failed"]
    attempts: int
    last_error: str | None
    sent_at: datetime | None
    created_at: datetime


class NotificationDeliveryListResponse(BaseModel):
    items: list[NotificationDeliveryResponse]
    total: int
    limit: int
    offset: int


class DashboardResponse(BaseModel):
    reference_at: datetime
    period_start: date | None
    period_end: date | None
    filters: dict[str, object]
    total_equipment: int
    functioning_equipment: int
    equipment_in_maintenance: int
    overdue_maintenance: int
    open_occurrences: int
    upcoming_maintenance: int
    definitions: dict[str, str]


class WarrantyCreateRequest(BaseModel):
    supplier: str = Field(min_length=1, max_length=160)
    starts_on: date
    ends_on: date | None = None
    terms: str | None = Field(default=None, max_length=5000)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("supplier", "terms", "reason", mode="before")
    @classmethod
    def strip_warranty_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_warranty_period(self) -> "WarrantyCreateRequest":
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("warranty end must not precede start")
        return self


class WarrantyResponse(BaseModel):
    id: UUID
    equipment_id: UUID
    supplier: str
    starts_on: date
    ends_on: date | None
    terms: str | None
    created_by_id: UUID
    created_at: datetime


class MaintenanceCostCreateRequest(BaseModel):
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    source: str = Field(min_length=1, max_length=255)
    reference: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("source", "reference", "note", "reason", mode="before")
    @classmethod
    def strip_cost_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        return value or None


class MaintenanceCostResponse(BaseModel):
    id: UUID
    maintenance_id: UUID
    equipment_id: UUID
    amount: float
    currency: str
    source: str
    reference: str | None
    note: str | None
    created_by_id: UUID
    created_at: datetime


class ComponentHistoryResponse(BaseModel):
    id: UUID
    maintenance_id: UUID
    equipment_id: UUID
    component_name: str
    quantity: int
    observation: str | None
    created_at: datetime


class ComponentHistoryListResponse(BaseModel):
    items: list[ComponentHistoryResponse]
    total: int
    limit: int
    offset: int


class ReportResponse(BaseModel):
    reference_at: datetime
    filters: dict[str, object]
    equipment_count: int
    maintenance_count: int
    component_count: int
    warranty_count: int
    total_cost: float
    rows: list[dict[str, object]]


PredictionPolicyStatus = Literal["disabled", "enabled", "retired"]
PredictionRiskLevel = Literal["high", "medium", "low", "abstain"]
PredictionStatus = Literal["recommended", "confirmed", "rejected", "dismissed"]
PredictionDecision = Literal["confirmed", "rejected", "dismissed"]


class PredictionPolicyCreateRequest(BaseModel):
    name: str = Field(default="baseline-falhas-institucional", min_length=3, max_length=120)
    version: int = Field(default=1, ge=1, le=1000)
    baseline_version: str = Field(default="deterministic-v1", min_length=3, max_length=80)
    horizon_days: int = Field(default=90, ge=1, le=365)
    min_history_count: int = Field(default=2, ge=0, le=1000)
    min_confidence: Decimal = Field(default=Decimal("0.60"), ge=0, le=1, max_digits=5, decimal_places=4)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("name", "baseline_version", "reason", mode="before")
    @classmethod
    def strip_prediction_policy_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PredictionPolicyActionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_policy_action_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PredictionPolicyResponse(BaseModel):
    id: UUID
    name: str
    version: int
    status: PredictionPolicyStatus
    baseline_version: str
    horizon_days: int
    min_history_count: int
    min_confidence: float
    evaluation_approved: bool
    evaluation_summary: dict[str, object] | None
    created_by_id: UUID
    enabled_by_id: UUID | None
    enabled_at: datetime | None
    disabled_at: datetime | None
    disable_reason: str | None
    created_at: datetime


class PredictionPolicyListResponse(BaseModel):
    items: list[PredictionPolicyResponse]
    total: int
    limit: int
    offset: int


class PredictionEvaluationRequest(BaseModel):
    policy_id: UUID
    dataset_version: Literal["synthetic-v1"] = "synthetic-v1"
    evaluated_for: date | None = None
    approve_evaluation: bool = False
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_evaluation_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PredictionEvaluationResponse(BaseModel):
    id: UUID
    policy_id: UUID
    dataset_version: str
    run_key: str
    evaluated_for: date
    sample_count: int
    labeled_count: int
    baseline_precision: float | None
    baseline_recall: float | None
    heuristic_precision: float | None
    heuristic_recall: float | None
    false_positives: int
    false_negatives: int
    abstentions: int
    metrics: dict[str, object]
    evaluated_by_id: UUID
    created_at: datetime


class FailurePredictionResponse(BaseModel):
    id: UUID
    policy_id: UUID
    equipment_id: UUID
    generated_for: date
    horizon_end: date
    score: float
    confidence: float
    risk_level: PredictionRiskLevel
    status: PredictionStatus
    rationale: dict[str, object]
    feature_snapshot: dict[str, object]
    idempotency_key: str
    decided_by_id: UUID | None
    decided_at: datetime | None
    decision_reason: str | None
    created_at: datetime


class FailurePredictionListResponse(BaseModel):
    items: list[FailurePredictionResponse]
    total: int
    limit: int
    offset: int


class PredictionSimulationRequest(BaseModel):
    policy_id: UUID
    as_of: date | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_simulation_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PredictionGenerationResponse(BaseModel):
    generated: int
    abstained: int
    items: list[FailurePredictionResponse]


class PredictionDecisionRequest(BaseModel):
    decision: PredictionDecision
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_decision_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PredictionMockNotificationRequest(BaseModel):
    confirm: bool
    recipient_label: str = Field(default="ti-institucional-ficticio", min_length=3, max_length=160)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("recipient_label", "reason", mode="before")
    @classmethod
    def strip_prediction_notification_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PredictionNotificationResponse(BaseModel):
    id: UUID
    prediction_id: UUID
    channel: Literal["mock_email"]
    recipient_label: str
    idempotency_key: str
    status: Literal["queued", "sent", "failed"]
    attempts: int
    last_error: str | None
    sent_at: datetime | None
    created_by_id: UUID
    created_at: datetime


class PredictionNotificationListResponse(BaseModel):
    items: list[PredictionNotificationResponse]
    total: int
    limit: int
    offset: int


class PredictionMonitoringResponse(BaseModel):
    reference_at: datetime
    enabled_policy_id: UUID | None
    recommendation_count: int
    abstention_count: int
    confirmed_count: int
    rejected_count: int
    latest_evaluation: PredictionEvaluationResponse | None
    degradation: dict[str, object]


def _user_response(context: AuthContext) -> UserResponse:
    return UserResponse(
        id=context.user.id,
        display_name=context.user.display_name,
        role=context.user.role,
        permissions=sorted(context.permissions),
    )


def _session_response(context: AuthContext) -> SessionResponse:
    return SessionResponse(
        user=_user_response(context), expires_at=context.session.expires_at
    )


def _set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    settings = get_settings()
    max_age = settings.session_ttl_minutes * 60
    cookie_options = {
        "max_age": max_age,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        **cookie_options,
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        **cookie_options,
    )


def _commit_or_service_unavailable(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="operation unavailable",
        ) from error


def _environment_response(environment: Environment) -> EnvironmentResponse:
    return EnvironmentResponse(
        id=environment.id,
        code=environment.code,
        name=environment.name,
        kind=environment.kind,
        active=environment.active,
        created_at=environment.created_at,
    )


def _environment_state(environment: Environment) -> dict[str, object]:
    return {
        "code": environment.code,
        "name": environment.name,
        "kind": environment.kind,
        "active": environment.active,
    }


def _environment_audit(
    *,
    actor_id: UUID,
    environment_id: UUID,
    action: str,
    reason: str,
    previous_state: dict[str, object] | None = None,
    new_state: dict[str, object] | None = None,
) -> AuditEvent:
    return AuditEvent(
        actor_id=actor_id,
        entity_type="environment",
        entity_id=environment_id,
        action=action,
        previous_state=previous_state,
        new_state=new_state,
        reason=reason,
    )


def _equipment_response(
    equipment: Equipment,
    *,
    occurrence_count: int = 0,
    maintenance_count: int = 0,
) -> EquipmentResponse:
    return EquipmentResponse(
        id=equipment.id,
        asset_tag=equipment.asset_tag,
        kind=equipment.kind,
        brand=equipment.brand,
        model=equipment.model,
        status=equipment.status,
        location_id=equipment.location_id,
        registered_by_id=equipment.registered_by_id,
        last_maintenance_on=equipment.last_maintenance_on,
        next_maintenance_on=equipment.next_maintenance_on,
        active=equipment.active,
        created_at=equipment.created_at,
        occurrence_count=occurrence_count,
        maintenance_count=maintenance_count,
    )


def _equipment_state(equipment: Equipment) -> dict[str, object]:
    return {
        "asset_tag": equipment.asset_tag,
        "kind": equipment.kind,
        "brand": equipment.brand,
        "model": equipment.model,
        "status": equipment.status,
        "location_id": str(equipment.location_id),
        "registered_by_id": str(equipment.registered_by_id),
        "last_maintenance_on": (
            equipment.last_maintenance_on.isoformat()
            if equipment.last_maintenance_on is not None
            else None
        ),
        "next_maintenance_on": (
            equipment.next_maintenance_on.isoformat()
            if equipment.next_maintenance_on is not None
            else None
        ),
        "active": equipment.active,
    }


def _equipment_audit(
    *,
    actor_id: UUID,
    equipment_id: UUID,
    action: str,
    reason: str,
    previous_state: dict[str, object] | None = None,
    new_state: dict[str, object] | None = None,
) -> AuditEvent:
    return AuditEvent(
        actor_id=actor_id,
        entity_type="equipment",
        entity_id=equipment_id,
        action=action,
        previous_state=previous_state,
        new_state=new_state,
        reason=reason,
    )


def _require_active_environment(db: Session, location_id: UUID) -> Environment:
    environment = db.get(Environment, location_id)
    if environment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="location not found",
        )
    if not environment.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="equipment location must be an active environment",
        )
    return environment


EQUIPMENT_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "active": frozenset({"active", "maintenance", "inactive"}),
    "maintenance": frozenset({"active", "maintenance", "inactive"}),
    "inactive": frozenset({"active", "inactive"}),
}

OCCURRENCE_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"open", "in_progress"}),
    "in_progress": frozenset({"in_progress", "resolved"}),
    "resolved": frozenset({"resolved", "closed"}),
    "closed": frozenset({"closed"}),
}
MAINTENANCE_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "planned": frozenset({"planned", "in_progress", "cancelled"}),
    "in_progress": frozenset({"in_progress", "completed", "cancelled"}),
    "completed": frozenset({"completed"}),
    "cancelled": frozenset({"cancelled"}),
}

_PUBLIC_RATE_LIMIT: dict[str, tuple[float, int]] = {}
_PUBLIC_RATE_LIMIT_LOCK = threading.Lock()
_PUBLIC_RATE_WINDOW_SECONDS = 60.0
_PUBLIC_RATE_MAX_REQUESTS = 12


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


_ACCENTED_SEARCH_CHARS = "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ"
_PLAIN_SEARCH_CHARS = "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC"


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).lower()


def _accent_insensitive_contains(column, value: str):
    normalized_column = func.lower(
        func.translate(column, _ACCENTED_SEARCH_CHARS, _PLAIN_SEARCH_CHARS)
    )
    return normalized_column.ilike(f"%{_normalize_search_text(value)}%")


def _movement_response(movement: Movement) -> MovementResponse:
    return MovementResponse(
        id=movement.id,
        equipment_id=movement.equipment_id,
        origin_environment_id=movement.origin_environment_id,
        destination_environment_id=movement.destination_environment_id,
        moved_by_id=movement.moved_by_id,
        reason=movement.reason,
        created_at=movement.created_at,
    )


def _occurrence_state(occurrence: Occurrence) -> dict[str, object]:
    return {
        "equipment_id": str(occurrence.equipment_id),
        "environment_id": str(occurrence.environment_id),
        "status": occurrence.status,
        "priority": occurrence.priority,
        "assigned_to_id": (
            str(occurrence.assigned_to_id) if occurrence.assigned_to_id else None
        ),
        "resolution_reason": occurrence.resolution_reason,
    }


def _occurrence_response(
    occurrence: Occurrence, *, include_contact: bool = False
) -> OccurrenceResponse:
    return OccurrenceResponse(
        id=occurrence.id,
        public_tracking_token=occurrence.public_tracking_token,
        equipment_id=occurrence.equipment_id,
        environment_id=occurrence.environment_id,
        description=occurrence.description,
        status=occurrence.status,
        priority=occurrence.priority,
        assigned_to_id=occurrence.assigned_to_id,
        reporter_name=occurrence.reporter_name if include_contact else None,
        reporter_contact=occurrence.reporter_contact if include_contact else None,
        resolution_reason=occurrence.resolution_reason,
        closed_at=occurrence.closed_at,
        created_at=occurrence.created_at,
    )


def _comment_response(comment: OccurrenceComment) -> OccurrenceCommentResponse:
    return OccurrenceCommentResponse(
        id=comment.id,
        occurrence_id=comment.occurrence_id,
        author_id=comment.author_id,
        body=comment.body,
        created_at=comment.created_at,
    )


def _history_response(event: AuditEvent) -> OccurrenceHistoryResponse:
    return OccurrenceHistoryResponse(
        id=event.id,
        action=event.action,
        actor_id=event.actor_id,
        previous_state=event.previous_state,
        new_state=event.new_state,
        reason=event.reason,
        occurred_at=event.occurred_at,
    )


def _component_response(component: MaintenanceComponent) -> MaintenanceComponentResponse:
    return MaintenanceComponentResponse(
        id=component.id,
        maintenance_id=component.maintenance_id,
        component_name=component.component_name,
        quantity=component.quantity,
        observation=component.observation,
        created_at=component.created_at,
    )


def _maintenance_response(
    maintenance: Maintenance, components: list[MaintenanceComponent] | None = None
) -> MaintenanceResponse:
    return MaintenanceResponse(
        id=maintenance.id,
        equipment_id=maintenance.equipment_id,
        occurrence_id=maintenance.occurrence_id,
        kind=maintenance.kind,
        status=maintenance.status,
        technician_id=maintenance.technician_id,
        scheduled_for=maintenance.scheduled_for,
        started_at=maintenance.started_at,
        completed_at=maintenance.completed_at,
        procedure=maintenance.procedure,
        result=maintenance.result,
        created_at=maintenance.created_at,
        components=[_component_response(item) for item in (components or [])],
    )


def _public_url(public_token: UUID) -> str:
    base_url = get_settings().public_app_url.rstrip("/")
    return f"{base_url}/public/equipment/{public_token}"


def _qr_svg(value: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=2,
    )
    qr.add_data(value)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    size = len(matrix)
    path_parts = []
    for row_index, row in enumerate(matrix):
        for column_index, enabled in enumerate(row):
            if enabled:
                path_parts.append(f"M{column_index},{row_index}h1v1h-1z")
    path = "".join(path_parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="QR Code do inventário" viewBox="0 0 {size} {size}" '
        f'shape-rendering="crispEdges"><rect width="100%" height="100%" fill="#fff"/>'
        f'<path d="{path}" fill="#000"/></svg>'
    )


def _enforce_public_rate_limit(request: Request, discriminator: str) -> None:
    host = request.client.host if request.client else "unknown"
    key = f"{host}:{discriminator}"
    now = time.monotonic()
    with _PUBLIC_RATE_LIMIT_LOCK:
        window_start, count = _PUBLIC_RATE_LIMIT.get(key, (now, 0))
        if now - window_start >= _PUBLIC_RATE_WINDOW_SECONDS:
            window_start, count = now, 0
        count += 1
        _PUBLIC_RATE_LIMIT[key] = (window_start, count)
        if count > _PUBLIC_RATE_MAX_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="public request limit exceeded",
            )


app = FastAPI(
    title="Inventário institucional API",
    description="API do sistema institucional de inventário e manutenção.",
    version="0.1.0",
)

# Apenas os servidores locais usados pelo frontend durante o desenvolvimento.
# Credenciais não são habilitadas por padrão.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)


@app.post(
    "/api/auth/login",
    response_model=SessionResponse,
    tags=["autenticação"],
)
def login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Cria uma sessão local sem devolver token para o JavaScript."""

    user = db.scalar(
        select(InternalUser).where(InternalUser.auth_subject == credentials.auth_subject)
    )
    if (
        user is None
        or not user.active
        or not verify_password(credentials.password, user.password_hash)
    ):
        failed_user_id = user.id if user is not None else UUID(int=0)
        db.add(
            AuditEvent(
                actor_id=user.id if user is not None else None,
                entity_type="authentication",
                entity_id=failed_user_id,
                action="session.login_failed",
                reason="invalid credentials",
            )
        )
        _commit_or_service_unavailable(db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, csrf_token, expires_at = create_session(db, user)
    db.add(
        AuditEvent(
            actor_id=user.id,
            entity_type="authentication",
            entity_id=user.id,
            action="session.created",
            new_state={"role": user.role},
            reason="authenticated session created",
        )
    )
    _commit_or_service_unavailable(db)
    _set_session_cookies(response, token, csrf_token)
    return SessionResponse(
        user=UserResponse(
            id=user.id,
            display_name=user.display_name,
            role=user.role,
            permissions=sorted(ROLE_PERMISSIONS.get(user.role, frozenset())),
        ),
        expires_at=expires_at,
    )


@app.post(
    "/api/auth/logout",
    response_model=HealthResponse,
    tags=["autenticação"],
)
def logout(
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> HealthResponse:
    revoke_session(db, context)
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="authentication",
            entity_id=context.user.id,
            action="session.revoked",
            reason="user requested logout",
        )
    )
    _commit_or_service_unavailable(db)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return HealthResponse(status="ok", service="session-revoked")


@app.get(
    "/api/auth/me",
    response_model=SessionResponse,
    tags=["autenticação"],
)
def current_session(
    context: AuthContext = Depends(require_permission("auth:read_self")),
) -> SessionResponse:
    return _session_response(context)


@app.patch(
    "/api/auth/users/{user_id}/role",
    response_model=UserResponse,
    tags=["autorização"],
)
def change_role(
    user_id: UUID,
    change: RoleChangeRequest,
    context: AuthContext = Depends(require_permission("users:manage")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> UserResponse:
    target = db.get(InternalUser, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    previous_role = target.role
    target.role = change.role
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="internal_user",
            entity_id=target.id,
            action="role.changed",
            previous_state={"role": previous_role},
            new_state={"role": target.role},
            reason=change.reason,
        )
    )
    _commit_or_service_unavailable(db)
    refreshed_context = AuthContext(user=target, session=context.session)
    return _user_response(refreshed_context)


@app.get(
    "/api/environments",
    response_model=EnvironmentListResponse,
    tags=["ambientes"],
)
def list_environments(
    search: str | None = Query(default=None, max_length=120),
    kind: str | None = Query(default=None, max_length=64),
    active: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("environment:read")),
    db: Session = Depends(get_db),
) -> EnvironmentListResponse:
    filters = []
    if search:
        filters.append(
            or_(
                _accent_insensitive_contains(Environment.code, search.strip()),
                _accent_insensitive_contains(Environment.name, search.strip()),
                _accent_insensitive_contains(Environment.kind, search.strip()),
            )
        )
    if kind:
        filters.append(Environment.kind == kind.strip())
    if active is not None:
        filters.append(Environment.active == active)

    total = db.scalar(select(func.count()).select_from(Environment).where(*filters)) or 0
    environments = db.scalars(
        select(Environment)
        .where(*filters)
        .order_by(Environment.code)
        .offset(offset)
        .limit(limit)
    ).all()
    return EnvironmentListResponse(
        items=[_environment_response(environment) for environment in environments],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/api/environments",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ambientes"],
)
def create_environment(
    payload: EnvironmentCreateRequest,
    context: AuthContext = Depends(require_permission("environment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> EnvironmentResponse:
    environment = Environment(
        code=payload.code,
        name=payload.name,
        kind=payload.kind,
        active=True,
    )
    db.add(environment)
    try:
        db.flush()
        db.add(
            _environment_audit(
                actor_id=context.user.id,
                environment_id=environment.id,
                action="environment.created",
                reason=payload.reason,
                new_state=_environment_state(environment),
            )
        )
        db.commit()
        db.refresh(environment)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="environment code already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="environment unavailable",
        ) from error
    return _environment_response(environment)


@app.patch(
    "/api/environments/{environment_id}",
    response_model=EnvironmentResponse,
    tags=["ambientes"],
)
def update_environment(
    environment_id: UUID,
    payload: EnvironmentUpdateRequest,
    context: AuthContext = Depends(require_permission("environment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> EnvironmentResponse:
    environment = db.get(Environment, environment_id)
    if environment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="environment not found")

    previous_state = _environment_state(environment)
    changes = payload.model_dump(exclude={"reason"}, exclude_unset=True)
    for field, value in changes.items():
        setattr(environment, field, value)
    db.add(
        _environment_audit(
            actor_id=context.user.id,
            environment_id=environment.id,
            action="environment.updated",
            reason=payload.reason,
            previous_state=previous_state,
            new_state=_environment_state(environment),
        )
    )
    try:
        db.commit()
        db.refresh(environment)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="environment code already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="environment unavailable",
        ) from error
    return _environment_response(environment)


@app.delete(
    "/api/environments/{environment_id}",
    response_model=HealthResponse,
    tags=["ambientes"],
)
def delete_environment(
    environment_id: UUID,
    reason: str = Query(min_length=3, max_length=500),
    context: AuthContext = Depends(require_permission("environment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> HealthResponse:
    environment = db.get(Environment, environment_id)
    if environment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="environment not found")

    has_equipment = db.scalar(
        select(Equipment.id).where(Equipment.location_id == environment_id).limit(1)
    )
    has_movement = db.scalar(
        select(Movement.id)
        .where(
            or_(
                Movement.origin_environment_id == environment_id,
                Movement.destination_environment_id == environment_id,
            )
        )
        .limit(1)
    )
    has_occurrence = db.scalar(
        select(Occurrence.id).where(Occurrence.environment_id == environment_id).limit(1)
    )
    if has_equipment is not None or has_movement is not None or has_occurrence is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="environment has historical links; inactivate it instead",
        )

    previous_state = _environment_state(environment)
    db.add(
        _environment_audit(
            actor_id=context.user.id,
            environment_id=environment.id,
            action="environment.deleted",
            reason=reason.strip(),
            previous_state=previous_state,
        )
    )
    db.delete(environment)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="environment unavailable",
        ) from error
    return HealthResponse(status="ok", service="environment-deleted")


@app.get(
    "/api/equipment",
    response_model=EquipmentListResponse,
    tags=["equipamentos"],
)
def list_equipment(
    search: str | None = Query(default=None, max_length=120),
    kind: EquipmentKind | None = None,
    status_filter: EquipmentStatus | None = Query(default=None, alias="status"),
    location_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("equipment:read")),
    db: Session = Depends(get_db),
) -> EquipmentListResponse:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Equipment.asset_tag.ilike(pattern),
                Equipment.brand.ilike(pattern),
                Equipment.model.ilike(pattern),
            )
        )
    if kind:
        filters.append(Equipment.kind == kind)
    if status_filter:
        filters.append(Equipment.status == status_filter)
    if location_id:
        filters.append(Equipment.location_id == location_id)

    total = db.scalar(select(func.count()).select_from(Equipment).where(*filters)) or 0
    equipment_items = db.scalars(
        select(Equipment)
        .where(*filters)
        .order_by(Equipment.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    items = []
    for equipment in equipment_items:
        occurrence_count = db.scalar(
            select(func.count())
            .select_from(Occurrence)
            .where(Occurrence.equipment_id == equipment.id)
        ) or 0
        maintenance_count = db.scalar(
            select(func.count())
            .select_from(Maintenance)
            .where(Maintenance.equipment_id == equipment.id)
        ) or 0
        items.append(
            _equipment_response(
                equipment,
                occurrence_count=occurrence_count,
                maintenance_count=maintenance_count,
            )
        )
    return EquipmentListResponse(items=items, total=total, limit=limit, offset=offset)


@app.post(
    "/api/equipment",
    response_model=EquipmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["equipamentos"],
)
def create_equipment(
    payload: EquipmentCreateRequest,
    context: AuthContext = Depends(require_permission("equipment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> EquipmentResponse:
    _require_active_environment(db, payload.location_id)
    equipment = Equipment(
        kind=payload.kind,
        asset_tag=payload.asset_tag,
        brand=payload.brand,
        model=payload.model,
        location_id=payload.location_id,
        registered_by_id=context.user.id,
        last_maintenance_on=payload.last_maintenance_on,
        next_maintenance_on=payload.next_maintenance_on,
        status="active",
        active=True,
    )
    db.add(equipment)
    try:
        db.flush()
        db.add(
            _equipment_audit(
                actor_id=context.user.id,
                equipment_id=equipment.id,
                action="equipment.created",
                reason=payload.reason,
                new_state=_equipment_state(equipment),
            )
        )
        db.commit()
        db.refresh(equipment)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="asset tag already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="equipment unavailable",
        ) from error
    return _equipment_response(equipment)


@app.get(
    "/api/equipment/{equipment_id}",
    response_model=EquipmentResponse,
    tags=["equipamentos"],
)
def get_equipment(
    equipment_id: UUID,
    _context: AuthContext = Depends(require_permission("equipment:read")),
    db: Session = Depends(get_db),
) -> EquipmentResponse:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    occurrence_count = db.scalar(
        select(func.count())
        .select_from(Occurrence)
        .where(Occurrence.equipment_id == equipment.id)
    ) or 0
    maintenance_count = db.scalar(
        select(func.count())
        .select_from(Maintenance)
        .where(Maintenance.equipment_id == equipment.id)
    ) or 0
    return _equipment_response(
        equipment,
        occurrence_count=occurrence_count,
        maintenance_count=maintenance_count,
    )


@app.patch(
    "/api/equipment/{equipment_id}",
    response_model=EquipmentResponse,
    tags=["equipamentos"],
)
def update_equipment(
    equipment_id: UUID,
    payload: EquipmentUpdateRequest,
    context: AuthContext = Depends(require_permission("equipment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> EquipmentResponse:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")

    changes = payload.model_dump(exclude={"reason"}, exclude_unset=True)
    next_status = changes.get("status", equipment.status)
    if next_status not in EQUIPMENT_STATUS_TRANSITIONS.get(equipment.status, frozenset()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="equipment status transition is not allowed",
        )
    next_location = changes.get("location_id", equipment.location_id)
    if next_location != equipment.location_id:
        _require_active_environment(db, next_location)

    next_last_maintenance = changes.get(
        "last_maintenance_on", equipment.last_maintenance_on
    )
    next_maintenance = changes.get(
        "next_maintenance_on", equipment.next_maintenance_on
    )
    if (
        next_last_maintenance is not None
        and next_maintenance is not None
        and next_maintenance < next_last_maintenance
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="next maintenance date cannot precede last maintenance date",
        )

    previous_state = _equipment_state(equipment)
    for field, value in changes.items():
        setattr(equipment, field, value)
    if "status" in changes:
        equipment.active = equipment.status != "inactive"

    action = (
        "equipment.inactivated"
        if equipment.status == "inactive" and previous_state["status"] != "inactive"
        else "equipment.updated"
    )
    db.add(
        _equipment_audit(
            actor_id=context.user.id,
            equipment_id=equipment.id,
            action=action,
            reason=payload.reason,
            previous_state=previous_state,
            new_state=_equipment_state(equipment),
        )
    )
    try:
        db.commit()
        db.refresh(equipment)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="asset tag already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="equipment unavailable",
        ) from error
    return _equipment_response(equipment)


@app.delete(
    "/api/equipment/{equipment_id}",
    response_model=HealthResponse,
    tags=["equipamentos"],
)
def delete_equipment(
    equipment_id: UUID,
    reason: str = Query(min_length=3, max_length=500),
    context: AuthContext = Depends(require_permission("equipment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> HealthResponse:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")

    has_movement = db.scalar(
        select(Movement.id).where(Movement.equipment_id == equipment_id).limit(1)
    )
    has_occurrence = db.scalar(
        select(Occurrence.id).where(Occurrence.equipment_id == equipment_id).limit(1)
    )
    has_maintenance = db.scalar(
        select(Maintenance.id).where(Maintenance.equipment_id == equipment_id).limit(1)
    )
    if (
        has_movement is not None
        or has_occurrence is not None
        or has_maintenance is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="equipment has historical links; inactivate it instead",
        )

    db.add(
        _equipment_audit(
            actor_id=context.user.id,
            equipment_id=equipment.id,
            action="equipment.deleted",
            reason=reason.strip(),
            previous_state=_equipment_state(equipment),
        )
    )
    db.delete(equipment)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="equipment unavailable",
        ) from error
    return HealthResponse(status="ok", service="equipment-deleted")


@app.get("/api/health", response_model=HealthResponse, tags=["diagnóstico"])
def health() -> HealthResponse:
    """Informa se a API está disponível para o frontend."""

    return HealthResponse(status="ok", service="inventario-backend")


@app.get(
    "/api/health/database",
    response_model=HealthResponse,
    tags=["diagnóstico"],
)
def database_health() -> HealthResponse:
    """Informa prontidão do banco sem expor credenciais ou detalhes internos."""

    try:
        check_database()
    except (SQLAlchemyError, ValidationError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from error

    return HealthResponse(status="ok", service="postgresql")


@app.post(
    "/api/equipment/{equipment_id}/movements",
    response_model=MovementResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["movimentações"],
)
def create_movement(
    equipment_id: UUID,
    payload: MovementCreateRequest,
    context: AuthContext = Depends(require_permission("movement:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MovementResponse:
    equipment = db.scalar(
        select(Equipment).where(Equipment.id == equipment_id).with_for_update()
    )
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    if equipment.status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inactive equipment cannot be moved",
        )
    if payload.origin_environment_id != equipment.location_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="origin does not match current equipment location",
        )
    if payload.origin_environment_id == payload.destination_environment_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="origin and destination must differ",
        )
    origin = db.get(Environment, payload.origin_environment_id)
    destination = db.get(Environment, payload.destination_environment_id)
    if origin is None or destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="environment not found")
    if not origin.active or not destination.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="origin and destination must be active environments",
        )

    previous_state = _equipment_state(equipment)
    movement = Movement(
        equipment_id=equipment.id,
        origin_environment_id=payload.origin_environment_id,
        destination_environment_id=payload.destination_environment_id,
        moved_by_id=context.user.id,
        reason=payload.reason,
    )
    equipment.location_id = payload.destination_environment_id
    db.add(movement)
    db.add(
        _equipment_audit(
            actor_id=context.user.id,
            equipment_id=equipment.id,
            action="equipment.moved",
            reason=payload.reason,
            previous_state=previous_state,
            new_state=_equipment_state(equipment),
        )
    )
    try:
        db.flush()
        db.commit()
        db.refresh(movement)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="movement unavailable",
        ) from error
    return _movement_response(movement)


@app.get(
    "/api/movements",
    response_model=MovementListResponse,
    tags=["movimentações"],
)
@app.get(
    "/api/equipment/{equipment_id}/movements",
    response_model=MovementListResponse,
    tags=["movimentações"],
)
def list_movements(
    equipment_id: UUID | None = None,
    environment_id: UUID | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("movement:read")),
    db: Session = Depends(get_db),
) -> MovementListResponse:
    if equipment_id is not None and db.get(Equipment, equipment_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    filters = []
    if equipment_id:
        filters.append(Movement.equipment_id == equipment_id)
    if environment_id:
        filters.append(
            or_(
                Movement.origin_environment_id == environment_id,
                Movement.destination_environment_id == environment_id,
            )
        )
    if from_date:
        filters.append(
            Movement.created_at >= datetime.combine(from_date, datetime.min.time(), timezone.utc)
        )
    if to_date:
        filters.append(
            Movement.created_at < datetime.combine(
                to_date + timedelta(days=1), datetime.min.time(), timezone.utc
            )
        )
    total = db.scalar(select(func.count()).select_from(Movement).where(*filters)) or 0
    items = db.scalars(
        select(Movement)
        .where(*filters)
        .order_by(Movement.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return MovementListResponse(
        items=[_movement_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/equipment/{equipment_id}/public-access",
    response_model=PublicAccessResponse,
    tags=["comunicação pública"],
)
def public_access(
    equipment_id: UUID,
    _context: AuthContext = Depends(require_permission("equipment:read")),
    db: Session = Depends(get_db),
) -> PublicAccessResponse:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    public_url = _public_url(equipment.public_token)
    return PublicAccessResponse(
        public_url=public_url,
        qr_svg=_qr_svg(public_url),
        revoked=equipment.public_token_revoked_at is not None,
    )


@app.post(
    "/api/equipment/{equipment_id}/public-access/rotate",
    response_model=PublicAccessResponse,
    tags=["comunicação pública"],
)
def rotate_public_access(
    equipment_id: UUID,
    context: AuthContext = Depends(require_permission("equipment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PublicAccessResponse:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    old_token = equipment.public_token
    equipment.public_token = uuid4()
    equipment.public_token_revoked_at = None
    db.add(
        _equipment_audit(
            actor_id=context.user.id,
            equipment_id=equipment.id,
            action="equipment.public_link_rotated",
            reason="public access token rotated",
            previous_state={"public_token": str(old_token)},
            new_state={"public_token": str(equipment.public_token)},
        )
    )
    _commit_or_service_unavailable(db)
    public_url = _public_url(equipment.public_token)
    return PublicAccessResponse(
        public_url=public_url,
        qr_svg=_qr_svg(public_url),
        revoked=False,
    )


@app.post(
    "/api/equipment/{equipment_id}/public-access/revoke",
    response_model=PublicAccessResponse,
    tags=["comunicação pública"],
)
def revoke_public_access(
    equipment_id: UUID,
    context: AuthContext = Depends(require_permission("equipment:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PublicAccessResponse:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    equipment.public_token_revoked_at = _now_utc()
    db.add(
        _equipment_audit(
            actor_id=context.user.id,
            equipment_id=equipment.id,
            action="equipment.public_link_revoked",
            reason="public access token revoked",
            new_state={"revoked": True},
        )
    )
    _commit_or_service_unavailable(db)
    public_url = _public_url(equipment.public_token)
    return PublicAccessResponse(
        public_url=public_url,
        qr_svg=_qr_svg(public_url),
        revoked=True,
    )


@app.get(
    "/api/public/equipment/{public_token}",
    response_model=PublicReportFormResponse,
    tags=["comunicação pública"],
)
def public_equipment_form(
    public_token: UUID,
    request: Request,
) -> PublicReportFormResponse:
    _enforce_public_rate_limit(request, "form")
    return PublicReportFormResponse(
        message="Use este formulário para comunicar um problema ao inventário institucional."
    )


@app.post(
    "/api/public/equipment/{public_token}/occurrences",
    response_model=PublicReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["comunicação pública"],
)
def public_report_occurrence(
    public_token: UUID,
    payload: PublicReportRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicReportResponse:
    _enforce_public_rate_limit(request, "submit")
    equipment = db.scalar(
        select(Equipment).where(
            Equipment.public_token == public_token,
            Equipment.public_token_revoked_at.is_(None),
            Equipment.status != "inactive",
        )
    )
    tracking_token = uuid4()
    if equipment is not None:
        occurrence = Occurrence(
            equipment_id=equipment.id,
            environment_id=equipment.location_id,
            description=payload.description,
            status="open",
            priority="normal",
            reporter_name=payload.reporter_name,
            reporter_contact=payload.reporter_contact,
        )
        db.add(occurrence)
        try:
            db.flush()
            tracking_token = occurrence.public_tracking_token
            db.add(
                AuditEvent(
                    actor_id=None,
                    entity_type="occurrence",
                    entity_id=occurrence.id,
                    action="occurrence.created_public",
                    new_state={
                        "equipment_id": str(equipment.id),
                        "environment_id": str(equipment.location_id),
                        "status": "open",
                        "priority": "normal",
                    },
                    reason="public equipment report",
                )
            )
            db.commit()
        except SQLAlchemyError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="public report unavailable",
            ) from error
    return PublicReportResponse(
        message="Se o formulário estiver associado a um equipamento ativo, sua comunicação foi recebida.",
        tracking_token=tracking_token,
    )


@app.get(
    "/api/public/occurrences/{tracking_token}",
    response_model=PublicTrackingResponse,
    tags=["comunicação pública"],
)
def public_track_occurrence(
    tracking_token: UUID,
    request: Request,
) -> PublicTrackingResponse:
    _enforce_public_rate_limit(request, "tracking")
    return PublicTrackingResponse(
        status="received",
        message="A comunicação foi recebida e será avaliada pela equipe responsável.",
    )


@app.get(
    "/api/occurrences",
    response_model=OccurrenceListResponse,
    tags=["ocorrências"],
)
def list_occurrences(
    status_filter: OccurrenceStatus | None = Query(default=None, alias="status"),
    priority: OccurrencePriority | None = None,
    equipment_id: UUID | None = None,
    environment_id: UUID | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    context: AuthContext = Depends(require_permission("occurrence:read")),
    db: Session = Depends(get_db),
) -> OccurrenceListResponse:
    filters = []
    if status_filter:
        filters.append(Occurrence.status == status_filter)
    if priority:
        filters.append(Occurrence.priority == priority)
    if equipment_id:
        filters.append(Occurrence.equipment_id == equipment_id)
    if environment_id:
        filters.append(Occurrence.environment_id == environment_id)
    if from_date:
        filters.append(
            Occurrence.created_at >= datetime.combine(from_date, datetime.min.time(), timezone.utc)
        )
    if to_date:
        filters.append(
            Occurrence.created_at < datetime.combine(
                to_date + timedelta(days=1), datetime.min.time(), timezone.utc
            )
        )
    total = db.scalar(select(func.count()).select_from(Occurrence).where(*filters)) or 0
    rows = db.scalars(
        select(Occurrence)
        .where(*filters)
        .order_by(Occurrence.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    include_contact = context.user.role in {"it", "administration"}
    return OccurrenceListResponse(
        items=[_occurrence_response(row, include_contact=include_contact) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/api/occurrences",
    response_model=OccurrenceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ocorrências"],
)
def create_internal_occurrence(
    payload: OccurrenceCreateRequest,
    context: AuthContext = Depends(require_permission("occurrence:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> OccurrenceResponse:
    equipment = db.get(Equipment, payload.equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    if equipment.status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inactive equipment cannot receive occurrences",
        )
    occurrence = Occurrence(
        equipment_id=equipment.id,
        environment_id=equipment.location_id,
        description=payload.description,
        status="open",
        priority=payload.priority,
        reporter_name=payload.reporter_name,
        reporter_contact=payload.reporter_contact,
    )
    db.add(occurrence)
    try:
        db.flush()
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="occurrence",
                entity_id=occurrence.id,
                action="occurrence.created",
                new_state=_occurrence_state(occurrence),
                reason=payload.reason,
            )
        )
        db.commit()
        db.refresh(occurrence)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="occurrence unavailable",
        ) from error
    return _occurrence_response(occurrence, include_contact=True)


@app.get(
    "/api/occurrences/{occurrence_id}",
    response_model=OccurrenceDetailResponse,
    tags=["ocorrências"],
)
def get_occurrence(
    occurrence_id: UUID,
    context: AuthContext = Depends(require_permission("occurrence:read")),
    db: Session = Depends(get_db),
) -> OccurrenceDetailResponse:
    occurrence = db.get(Occurrence, occurrence_id)
    if occurrence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="occurrence not found")
    comments = db.scalars(
        select(OccurrenceComment)
        .where(OccurrenceComment.occurrence_id == occurrence.id)
        .order_by(OccurrenceComment.created_at)
    ).all()
    history = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_type == "occurrence", AuditEvent.entity_id == occurrence.id)
        .order_by(AuditEvent.occurred_at)
    ).all()
    return OccurrenceDetailResponse(
        **_occurrence_response(
            occurrence, include_contact=context.user.role in {"it", "administration"}
        ).model_dump(),
        comments=[_comment_response(item) for item in comments],
        history=[_history_response(item) for item in history],
    )


@app.patch(
    "/api/occurrences/{occurrence_id}",
    response_model=OccurrenceResponse,
    tags=["ocorrências"],
)
def update_occurrence(
    occurrence_id: UUID,
    payload: OccurrenceUpdateRequest,
    context: AuthContext = Depends(require_permission("occurrence:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> OccurrenceResponse:
    occurrence = db.scalar(
        select(Occurrence).where(Occurrence.id == occurrence_id).with_for_update()
    )
    if occurrence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="occurrence not found")
    changes = payload.model_dump(exclude={"reason"}, exclude_unset=True)
    next_status = changes.get("status", occurrence.status)
    if next_status not in OCCURRENCE_STATUS_TRANSITIONS.get(occurrence.status, frozenset()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="occurrence status transition is not allowed",
        )
    if "assigned_to_id" in changes and changes["assigned_to_id"] is not None:
        assignee = db.get(InternalUser, changes["assigned_to_id"])
        if assignee is None or not assignee.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assignee not found")
    resolution_reason = changes.get("resolution_reason", occurrence.resolution_reason)
    if next_status == "closed":
        has_completed_maintenance = db.scalar(
            select(Maintenance.id).where(
                Maintenance.occurrence_id == occurrence.id,
                Maintenance.status == "completed",
            )
        )
        if not resolution_reason and has_completed_maintenance is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="closing occurrence requires completed maintenance or resolution reason",
            )
    previous_state = _occurrence_state(occurrence)
    for field, value in changes.items():
        setattr(occurrence, field, value)
    if next_status == "closed" and occurrence.closed_at is None:
        occurrence.closed_at = _now_utc()
        occurrence.closed_by_id = context.user.id
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="occurrence",
            entity_id=occurrence.id,
            action="occurrence.updated" if next_status != "closed" else "occurrence.closed",
            previous_state=previous_state,
            new_state=_occurrence_state(occurrence),
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(occurrence)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="occurrence unavailable",
        ) from error
    return _occurrence_response(occurrence, include_contact=True)


@app.post(
    "/api/occurrences/{occurrence_id}/comments",
    response_model=OccurrenceCommentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ocorrências"],
)
def add_occurrence_comment(
    occurrence_id: UUID,
    payload: OccurrenceCommentCreateRequest,
    context: AuthContext = Depends(require_permission("occurrence:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> OccurrenceCommentResponse:
    if db.get(Occurrence, occurrence_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="occurrence not found")
    comment = OccurrenceComment(
        occurrence_id=occurrence_id,
        author_id=context.user.id,
        body=payload.body,
    )
    db.add(comment)
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="occurrence",
            entity_id=occurrence_id,
            action="occurrence.comment_added",
            new_state={"comment_id": str(comment.id)},
            reason="internal comment added",
        )
    )
    try:
        db.commit()
        db.refresh(comment)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="comment unavailable",
        ) from error
    return _comment_response(comment)


@app.get(
    "/api/occurrences/{occurrence_id}/history",
    response_model=list[OccurrenceHistoryResponse],
    tags=["ocorrências"],
)
def occurrence_history(
    occurrence_id: UUID,
    _context: AuthContext = Depends(require_permission("occurrence:read")),
    db: Session = Depends(get_db),
) -> list[OccurrenceHistoryResponse]:
    if db.get(Occurrence, occurrence_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="occurrence not found")
    history = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_type == "occurrence", AuditEvent.entity_id == occurrence_id)
        .order_by(AuditEvent.occurred_at)
    ).all()
    return [_history_response(item) for item in history]


@app.get(
    "/api/maintenances",
    response_model=MaintenanceListResponse,
    tags=["manutenções"],
)
def list_maintenances(
    equipment_id: UUID | None = None,
    occurrence_id: UUID | None = None,
    kind: MaintenanceKind | None = None,
    status_filter: MaintenanceStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("maintenance:read")),
    db: Session = Depends(get_db),
) -> MaintenanceListResponse:
    filters = []
    if equipment_id:
        filters.append(Maintenance.equipment_id == equipment_id)
    if occurrence_id:
        filters.append(Maintenance.occurrence_id == occurrence_id)
    if kind:
        filters.append(Maintenance.kind == kind)
    if status_filter:
        filters.append(Maintenance.status == status_filter)
    total = db.scalar(select(func.count()).select_from(Maintenance).where(*filters)) or 0
    rows = db.scalars(
        select(Maintenance)
        .where(*filters)
        .order_by(Maintenance.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    items = []
    for row in rows:
        components = db.scalars(
            select(MaintenanceComponent)
            .where(MaintenanceComponent.maintenance_id == row.id)
            .order_by(MaintenanceComponent.created_at)
        ).all()
        items.append(_maintenance_response(row, components))
    return MaintenanceListResponse(items=items, total=total, limit=limit, offset=offset)


@app.post(
    "/api/maintenances",
    response_model=MaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["manutenções"],
)
def create_maintenance(
    payload: MaintenanceCreateRequest,
    context: AuthContext = Depends(require_permission("maintenance:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    equipment = db.get(Equipment, payload.equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    if equipment.status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inactive equipment cannot receive maintenance",
        )
    occurrence = None
    if payload.occurrence_id is not None:
        occurrence = db.get(Occurrence, payload.occurrence_id)
        if occurrence is None or occurrence.equipment_id != equipment.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="occurrence does not belong to equipment",
            )
    technician_id = payload.technician_id or context.user.id
    technician = db.get(InternalUser, technician_id)
    if technician is None or not technician.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="technician not found")
    maintenance = Maintenance(
        equipment_id=equipment.id,
        occurrence_id=occurrence.id if occurrence else None,
        kind=payload.kind,
        status="planned",
        technician_id=technician_id,
        scheduled_for=payload.scheduled_for,
        procedure=payload.procedure,
        result=payload.result,
    )
    db.add(maintenance)
    try:
        db.flush()
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="maintenance",
                entity_id=maintenance.id,
                action="maintenance.created",
                new_state={"status": "planned", "equipment_id": str(equipment.id)},
                reason=payload.reason,
            )
        )
        db.commit()
        db.refresh(maintenance)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="maintenance unavailable",
        ) from error
    return _maintenance_response(maintenance)


@app.get(
    "/api/maintenances/{maintenance_id}",
    response_model=MaintenanceResponse,
    tags=["manutenções"],
)
def get_maintenance(
    maintenance_id: UUID,
    _context: AuthContext = Depends(require_permission("maintenance:read")),
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    maintenance = db.get(Maintenance, maintenance_id)
    if maintenance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="maintenance not found")
    components = db.scalars(
        select(MaintenanceComponent)
        .where(MaintenanceComponent.maintenance_id == maintenance.id)
        .order_by(MaintenanceComponent.created_at)
    ).all()
    return _maintenance_response(maintenance, components)


@app.patch(
    "/api/maintenances/{maintenance_id}",
    response_model=MaintenanceResponse,
    tags=["manutenções"],
)
def update_maintenance(
    maintenance_id: UUID,
    payload: MaintenanceUpdateRequest,
    context: AuthContext = Depends(require_permission("maintenance:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenanceResponse:
    maintenance = db.scalar(
        select(Maintenance).where(Maintenance.id == maintenance_id).with_for_update()
    )
    if maintenance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="maintenance not found")
    changes = payload.model_dump(exclude={"reason"}, exclude_unset=True)
    next_status = changes.get("status", maintenance.status)
    if next_status not in MAINTENANCE_STATUS_TRANSITIONS.get(maintenance.status, frozenset()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="maintenance status transition is not allowed",
        )
    technician_id = changes.get("technician_id", maintenance.technician_id)
    if technician_id is not None:
        technician = db.get(InternalUser, technician_id)
        if technician is None or not technician.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="technician not found")
    if next_status == "completed":
        if technician_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="completed maintenance requires technician",
            )
        procedure = changes.get("procedure", maintenance.procedure)
        result = changes.get("result", maintenance.result)
        if not procedure or not result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="completed maintenance requires procedure and result",
            )

    previous_state = {
        "status": maintenance.status,
        "technician_id": str(maintenance.technician_id)
        if maintenance.technician_id
        else None,
        "procedure": maintenance.procedure,
        "result": maintenance.result,
    }
    maintenance_changes = {
        field: value for field, value in changes.items() if field != "next_maintenance_on"
    }
    for field, value in maintenance_changes.items():
        setattr(maintenance, field, value)
    if next_status == "in_progress" and maintenance.started_at is None:
        maintenance.started_at = _now_utc()
    if next_status == "completed" and maintenance.completed_at is None:
        maintenance.completed_at = _now_utc()
        equipment = db.scalar(
            select(Equipment).where(Equipment.id == maintenance.equipment_id).with_for_update()
        )
        if equipment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
        equipment.last_maintenance_on = maintenance.completed_at.date()
        if "next_maintenance_on" in changes:
            equipment.next_maintenance_on = changes["next_maintenance_on"]
        elif maintenance.kind == "preventive":
            equipment.next_maintenance_on = maintenance.completed_at.date() + timedelta(days=180)
        db.add(
            _equipment_audit(
                actor_id=context.user.id,
                equipment_id=equipment.id,
                action="equipment.maintenance_updated",
                reason=payload.reason,
                new_state={
                    "last_maintenance_on": equipment.last_maintenance_on.isoformat(),
                    "next_maintenance_on": (
                        equipment.next_maintenance_on.isoformat()
                        if equipment.next_maintenance_on
                        else None
                    ),
                },
            )
        )
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="maintenance",
            entity_id=maintenance.id,
            action="maintenance.completed" if next_status == "completed" else "maintenance.updated",
            previous_state=previous_state,
            new_state={"status": next_status},
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(maintenance)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="maintenance unavailable",
        ) from error
    components = db.scalars(
        select(MaintenanceComponent)
        .where(MaintenanceComponent.maintenance_id == maintenance.id)
        .order_by(MaintenanceComponent.created_at)
    ).all()
    return _maintenance_response(maintenance, components)


@app.post(
    "/api/maintenances/{maintenance_id}/components",
    response_model=MaintenanceComponentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["manutenções"],
)
def add_maintenance_component(
    maintenance_id: UUID,
    payload: MaintenanceComponentCreateRequest,
    context: AuthContext = Depends(require_permission("maintenance:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenanceComponentResponse:
    maintenance = db.get(Maintenance, maintenance_id)
    if maintenance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="maintenance not found")
    if maintenance.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cancelled maintenance cannot receive components",
        )
    component = MaintenanceComponent(
        maintenance_id=maintenance.id,
        component_name=payload.component_name,
        quantity=payload.quantity,
        observation=payload.observation,
    )
    db.add(component)
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="maintenance",
            entity_id=maintenance.id,
            action="maintenance.component_added",
            new_state={
                "component_name": component.component_name,
                "quantity": component.quantity,
            },
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(component)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="component unavailable",
        ) from error
    return _component_response(component)


def _plan_item_response(item: MaintenancePlanItem) -> MaintenancePlanItemResponse:
    return MaintenancePlanItemResponse(
        id=item.id,
        plan_id=item.plan_id,
        equipment_id=item.equipment_id,
        environment_id=item.environment_id,
        scheduled_for=item.scheduled_for,
        status=item.status,
        justification=item.justification,
        created_at=item.created_at,
    )


def _plan_response(
    plan: MaintenancePlan, items: list[MaintenancePlanItem] | None = None
) -> MaintenancePlanResponse:
    return MaintenancePlanResponse(
        id=plan.id,
        year=plan.year,
        version=plan.version,
        status=plan.status,
        capacity_monthly=plan.capacity_monthly,
        blackout_periods=plan.blackout_periods,
        summary=plan.summary,
        created_by_id=plan.created_by_id,
        approved_by_id=plan.approved_by_id,
        approved_at=plan.approved_at,
        published_at=plan.published_at,
        created_at=plan.created_at,
        items=[_plan_item_response(item) for item in (items or [])],
    )


def _alert_response(alert: MaintenanceAlert) -> MaintenanceAlertResponse:
    return MaintenanceAlertResponse(
        id=alert.id,
        equipment_id=alert.equipment_id,
        maintenance_id=alert.maintenance_id,
        kind=alert.kind,
        due_on=alert.due_on,
        idempotency_key=alert.idempotency_key,
        status=alert.status,
        generated_for=alert.generated_for,
        created_at=alert.created_at,
    )


def _delivery_response(delivery: NotificationDelivery) -> NotificationDeliveryResponse:
    return NotificationDeliveryResponse(
        id=delivery.id,
        alert_id=delivery.alert_id,
        channel=delivery.channel,
        recipient_label=delivery.recipient_label,
        idempotency_key=delivery.idempotency_key,
        status=delivery.status,
        attempts=delivery.attempts,
        last_error=delivery.last_error,
        sent_at=delivery.sent_at,
        created_at=delivery.created_at,
    )


def _warranty_response(warranty: EquipmentWarranty) -> WarrantyResponse:
    return WarrantyResponse(
        id=warranty.id,
        equipment_id=warranty.equipment_id,
        supplier=warranty.supplier,
        starts_on=warranty.starts_on,
        ends_on=warranty.ends_on,
        terms=warranty.terms,
        created_by_id=warranty.created_by_id,
        created_at=warranty.created_at,
    )


def _cost_response(cost: MaintenanceCost) -> MaintenanceCostResponse:
    return MaintenanceCostResponse(
        id=cost.id,
        maintenance_id=cost.maintenance_id,
        equipment_id=cost.equipment_id,
        amount=float(cost.amount),
        currency=cost.currency,
        source=cost.source,
        reference=cost.reference,
        note=cost.note,
        created_by_id=cost.created_by_id,
        created_at=cost.created_at,
    )


def _blackout_contains(candidate: date, blackout_periods: list[dict[str, object]]) -> bool:
    for period in blackout_periods:
        starts_on = date.fromisoformat(str(period["starts_on"]))
        ends_on = date.fromisoformat(str(period["ends_on"]))
        if starts_on <= candidate <= ends_on:
            return True
    return False


def _schedule_plan_item(
    *,
    target: date,
    year: int,
    capacity_monthly: dict[str, int],
    monthly_load: dict[str, int],
    blackout_periods: list[dict[str, object]],
) -> date | None:
    start = max(target, date(year, 1, 1))
    if start.year != year:
        return None
    for day_offset in range(366):
        candidate = start + timedelta(days=day_offset)
        if candidate.year != year:
            break
        month_key = str(candidate.month)
        if (
            not _blackout_contains(candidate, blackout_periods)
            and monthly_load[month_key] < capacity_monthly[month_key]
        ):
            monthly_load[month_key] += 1
            return candidate
    return None


def _plan_target_date(equipment: Equipment, year: int) -> date:
    if equipment.next_maintenance_on is not None:
        return equipment.next_maintenance_on
    if equipment.last_maintenance_on is not None:
        return equipment.last_maintenance_on + timedelta(days=365)
    return date(year, 1, 1)


def _plan_blackout_payload(
    periods: list[BlackoutPeriodRequest],
) -> list[dict[str, object]]:
    return [
        {
            "starts_on": period.starts_on.isoformat(),
            "ends_on": period.ends_on.isoformat(),
            "reason": period.reason,
        }
        for period in periods
    ]


def _simulate_plan_items(
    equipment_items: list[Equipment],
    *,
    year: int,
    capacity_monthly: dict[str, int],
    blackout_periods: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    monthly_load = {str(month): 0 for month in range(1, 13)}
    rows: list[dict[str, object]] = []
    ordered = sorted(
        equipment_items,
        key=lambda item: (
            _plan_target_date(item, year),
            str(item.location_id),
            item.asset_tag or "",
            str(item.id),
        ),
    )
    for equipment in ordered:
        target = _plan_target_date(equipment, year)
        scheduled_for = _schedule_plan_item(
            target=target,
            year=year,
            capacity_monthly=capacity_monthly,
            monthly_load=monthly_load,
            blackout_periods=blackout_periods,
        )
        if scheduled_for is None:
            item_status = "conflict" if target.year == year else "unallocated"
            justification = (
                "Não foi possível alocar dentro do ano: "
                f"capacidade/indisponibilidade para a data-alvo {target.isoformat()}."
            )
        else:
            item_status = "planned"
            justification = (
                "Alocação determinística por data-alvo, ambiente, identificador e "
                f"capacidade mensal; data-alvo={target.isoformat()}."
            )
        rows.append(
            {
                "equipment_id": equipment.id,
                "environment_id": equipment.location_id,
                "scheduled_for": scheduled_for,
                "status": item_status,
                "justification": justification,
            }
        )
    planned = sum(1 for row in rows if row["status"] == "planned")
    conflicts = len(rows) - planned
    summary: dict[str, object] = {
        "eligible": len(rows),
        "planned": planned,
        "conflicts": conflicts,
        "monthly_load": monthly_load,
        "policy": "computadores ativos recebem revisão preventiva anual quando há capacidade",
    }
    return rows, summary


@app.get(
    "/api/maintenance-plans",
    response_model=MaintenancePlanListResponse,
    tags=["planejamento"],
)
def list_maintenance_plans(
    year: int | None = Query(default=None, ge=2020, le=2100),
    status_filter: PlanStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("planning:read")),
    db: Session = Depends(get_db),
) -> MaintenancePlanListResponse:
    filters = []
    if year is not None:
        filters.append(MaintenancePlan.year == year)
    if status_filter:
        filters.append(MaintenancePlan.status == status_filter)
    total = db.scalar(select(func.count()).select_from(MaintenancePlan).where(*filters)) or 0
    plans = db.scalars(
        select(MaintenancePlan)
        .where(*filters)
        .order_by(MaintenancePlan.year.desc(), MaintenancePlan.version.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return MaintenancePlanListResponse(
        items=[
            _plan_response(
                plan,
                db.scalars(
                    select(MaintenancePlanItem)
                    .where(MaintenancePlanItem.plan_id == plan.id)
                    .order_by(MaintenancePlanItem.scheduled_for, MaintenancePlanItem.id)
                ).all(),
            )
            for plan in plans
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/api/maintenance-plans/simulate",
    response_model=MaintenancePlanResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["planejamento"],
)
def simulate_maintenance_plan(
    payload: MaintenancePlanCreateRequest,
    context: AuthContext = Depends(require_permission("planning:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenancePlanResponse:
    version = (
        db.scalar(
            select(func.max(MaintenancePlan.version)).where(MaintenancePlan.year == payload.year)
        )
        or 0
    ) + 1
    blackout_periods = _plan_blackout_payload(payload.blackout_periods)
    eligible = db.scalars(
        select(Equipment)
        .where(Equipment.kind == "computer", Equipment.status == "active")
        .order_by(Equipment.location_id, Equipment.asset_tag, Equipment.id)
    ).all()
    item_rows, summary = _simulate_plan_items(
        eligible,
        year=payload.year,
        capacity_monthly=payload.capacity_monthly,
        blackout_periods=blackout_periods,
    )
    plan = MaintenancePlan(
        year=payload.year,
        version=version,
        status="simulated",
        capacity_monthly=payload.capacity_monthly,
        blackout_periods=blackout_periods,
        summary=summary,
        created_by_id=context.user.id,
    )
    db.add(plan)
    try:
        db.flush()
        for row in item_rows:
            db.add(
                MaintenancePlanItem(
                    plan_id=plan.id,
                    equipment_id=row["equipment_id"],
                    environment_id=row["environment_id"],
                    scheduled_for=row["scheduled_for"],
                    status=row["status"],
                    justification=row["justification"],
                )
            )
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="maintenance_plan",
                entity_id=plan.id,
                action="maintenance_plan.simulated",
                new_state={"year": payload.year, "version": version, "summary": summary},
                reason=payload.reason,
            )
        )
        db.commit()
        db.refresh(plan)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="maintenance plan version already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="maintenance plan unavailable",
        ) from error
    items = db.scalars(
        select(MaintenancePlanItem)
        .where(MaintenancePlanItem.plan_id == plan.id)
        .order_by(MaintenancePlanItem.scheduled_for, MaintenancePlanItem.id)
    ).all()
    return _plan_response(plan, items)


@app.get(
    "/api/maintenance-plans/{plan_id}",
    response_model=MaintenancePlanResponse,
    tags=["planejamento"],
)
def get_maintenance_plan(
    plan_id: UUID,
    _context: AuthContext = Depends(require_permission("planning:read")),
    db: Session = Depends(get_db),
) -> MaintenancePlanResponse:
    plan = db.get(MaintenancePlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="maintenance plan not found")
    items = db.scalars(
        select(MaintenancePlanItem)
        .where(MaintenancePlanItem.plan_id == plan.id)
        .order_by(MaintenancePlanItem.scheduled_for, MaintenancePlanItem.id)
    ).all()
    return _plan_response(plan, items)


@app.post(
    "/api/maintenance-plans/{plan_id}/approve",
    response_model=MaintenancePlanResponse,
    tags=["planejamento"],
)
def approve_maintenance_plan(
    plan_id: UUID,
    payload: MaintenancePlanApprovalRequest,
    context: AuthContext = Depends(require_permission("planning:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenancePlanResponse:
    plan = db.scalar(select(MaintenancePlan).where(MaintenancePlan.id == plan_id).with_for_update())
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="maintenance plan not found")
    if plan.status != "simulated":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="only simulated plans can be approved")
    plan.status = "approved"
    plan.approved_by_id = context.user.id
    plan.approved_at = _now_utc()
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="maintenance_plan",
            entity_id=plan.id,
            action="maintenance_plan.approved",
            previous_state={"status": "simulated"},
            new_state={"status": "approved", "approved_by_id": str(context.user.id)},
            reason=payload.reason,
        )
    )
    _commit_or_service_unavailable(db)
    items = db.scalars(select(MaintenancePlanItem).where(MaintenancePlanItem.plan_id == plan.id)).all()
    return _plan_response(plan, items)


@app.post(
    "/api/maintenance-plans/{plan_id}/publish",
    response_model=MaintenancePlanResponse,
    tags=["planejamento"],
)
def publish_maintenance_plan(
    plan_id: UUID,
    payload: MaintenancePlanApprovalRequest,
    context: AuthContext = Depends(require_permission("planning:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenancePlanResponse:
    plan = db.scalar(select(MaintenancePlan).where(MaintenancePlan.id == plan_id).with_for_update())
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="maintenance plan not found")
    if plan.status != "approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="only approved plans can be published")
    plan.status = "published"
    plan.published_at = _now_utc()
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="maintenance_plan",
            entity_id=plan.id,
            action="maintenance_plan.published",
            previous_state={"status": "approved"},
            new_state={"status": "published"},
            reason=payload.reason,
        )
    )
    _commit_or_service_unavailable(db)
    items = db.scalars(select(MaintenancePlanItem).where(MaintenancePlanItem.plan_id == plan.id)).all()
    return _plan_response(plan, items)


@app.get(
    "/api/alerts",
    response_model=MaintenanceAlertListResponse,
    tags=["alertas"],
)
def list_maintenance_alerts(
    alert_status: AlertStatus | None = Query(default=None, alias="status"),
    kind: AlertKind | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("alert:read")),
    db: Session = Depends(get_db),
) -> MaintenanceAlertListResponse:
    filters = []
    if alert_status:
        filters.append(MaintenanceAlert.status == alert_status)
    if kind:
        filters.append(MaintenanceAlert.kind == kind)
    total = db.scalar(select(func.count()).select_from(MaintenanceAlert).where(*filters)) or 0
    alerts = db.scalars(
        select(MaintenanceAlert)
        .where(*filters)
        .order_by(MaintenanceAlert.due_on, MaintenanceAlert.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return MaintenanceAlertListResponse(
        items=[_alert_response(alert) for alert in alerts],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/api/alerts/generate",
    response_model=MaintenanceAlertGenerationResponse,
    tags=["alertas"],
)
def generate_maintenance_alerts(
    payload: MaintenanceAlertGenerateRequest,
    context: AuthContext = Depends(require_permission("alert:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenanceAlertGenerationResponse:
    as_of = payload.as_of or date.today()
    end_window = as_of + timedelta(days=payload.upcoming_days)
    equipment_items = db.scalars(
        select(Equipment)
        .where(
            Equipment.status != "inactive",
            Equipment.active.is_(True),
            Equipment.next_maintenance_on.is_not(None),
        )
    ).all()
    candidates: list[tuple[Equipment, str, date]] = []
    for equipment in equipment_items:
        due_on = equipment.next_maintenance_on
        if due_on is None:
            continue
        if due_on < as_of:
            candidates.append((equipment, "overdue", due_on))
        elif due_on <= end_window:
            candidates.append((equipment, "upcoming", due_on))

    created = 0
    for equipment, alert_kind, due_on in candidates:
        idempotency_key = f"maintenance:{equipment.id}:{alert_kind}:{due_on.isoformat()}"
        existing = db.scalar(
            select(MaintenanceAlert).where(MaintenanceAlert.idempotency_key == idempotency_key)
        )
        if existing is not None:
            continue
        maintenance_id = db.scalar(
            select(Maintenance.id)
            .where(
                Maintenance.equipment_id == equipment.id,
                Maintenance.scheduled_for == due_on,
                Maintenance.status != "cancelled",
            )
            .order_by(Maintenance.created_at.desc())
            .limit(1)
        )
        alert = MaintenanceAlert(
            equipment_id=equipment.id,
            maintenance_id=maintenance_id,
            kind=alert_kind,
            due_on=due_on,
            idempotency_key=idempotency_key,
            status="open",
            generated_for=as_of,
        )
        db.add(alert)
        db.flush()
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="maintenance_alert",
                entity_id=alert.id,
                action="maintenance_alert.generated",
                new_state={"kind": alert_kind, "due_on": due_on.isoformat()},
                reason=payload.reason,
            )
        )
        created += 1
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="alert generation conflicted with another run",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="alert generation unavailable",
        ) from error
    keys = [f"maintenance:{equipment.id}:{alert_kind}:{due_on.isoformat()}" for equipment, alert_kind, due_on in candidates]
    generated_alerts = db.scalars(
        select(MaintenanceAlert)
        .where(MaintenanceAlert.idempotency_key.in_(keys))
        .order_by(MaintenanceAlert.due_on)
    ).all() if keys else []
    return MaintenanceAlertGenerationResponse(
        created=created,
        items=[_alert_response(alert) for alert in generated_alerts],
    )


@app.post(
    "/api/alerts/{alert_id}/mock-dispatch",
    response_model=NotificationDeliveryResponse,
    tags=["alertas"],
)
def dispatch_mock_alert(
    alert_id: UUID,
    payload: NotificationDispatchRequest,
    context: AuthContext = Depends(require_permission("alert:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> NotificationDeliveryResponse:
    alert = db.get(MaintenanceAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="alert not found")
    idempotency_key = f"alert:{alert.id}:mock_email:{payload.recipient_label}"
    existing = db.scalar(
        select(NotificationDelivery).where(
            NotificationDelivery.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return _delivery_response(existing)
    delivery = NotificationDelivery(
        alert_id=alert.id,
        channel="mock_email",
        recipient_label=payload.recipient_label,
        idempotency_key=idempotency_key,
        status="sent",
        attempts=1,
        sent_at=_now_utc(),
    )
    alert.status = "dispatched"
    db.add(delivery)
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="maintenance_alert",
            entity_id=alert.id,
            action="notification.mock_dispatched",
            new_state={"channel": "mock_email", "recipient_label": payload.recipient_label},
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(delivery)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="notification already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="notification unavailable",
        ) from error
    return _delivery_response(delivery)


@app.get(
    "/api/notifications/deliveries",
    response_model=NotificationDeliveryListResponse,
    tags=["alertas"],
)
def list_notification_deliveries(
    delivery_status: Literal["queued", "sent", "failed"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("alert:read")),
    db: Session = Depends(get_db),
) -> NotificationDeliveryListResponse:
    filters = []
    if delivery_status:
        filters.append(NotificationDelivery.status == delivery_status)
    total = db.scalar(select(func.count()).select_from(NotificationDelivery).where(*filters)) or 0
    deliveries = db.scalars(
        select(NotificationDelivery)
        .where(*filters)
        .order_by(NotificationDelivery.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return NotificationDeliveryListResponse(
        items=[_delivery_response(item) for item in deliveries],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/dashboard/summary",
    response_model=DashboardResponse,
    tags=["painel gerencial"],
)
def dashboard_summary(
    period_start: date | None = Query(default=None, alias="from"),
    period_end: date | None = Query(default=None, alias="to"),
    kind: EquipmentKind | None = None,
    location_id: UUID | None = None,
    _context: AuthContext = Depends(require_permission("dashboard:read")),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    if period_start is not None and period_end is not None and period_end < period_start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="period end must not precede start")
    equipment_filters = []
    if kind:
        equipment_filters.append(Equipment.kind == kind)
    if location_id:
        equipment_filters.append(Equipment.location_id == location_id)
    total_equipment = db.scalar(select(func.count()).select_from(Equipment).where(*equipment_filters)) or 0
    functioning_equipment = db.scalar(
        select(func.count()).select_from(Equipment).where(*equipment_filters, Equipment.status == "active")
    ) or 0
    equipment_in_maintenance = db.scalar(
        select(func.count()).select_from(Equipment).where(*equipment_filters, Equipment.status == "maintenance")
    ) or 0
    today = date.today()
    overdue_filters = [*equipment_filters, Equipment.status != "inactive", Equipment.next_maintenance_on < today]
    overdue_maintenance = db.scalar(select(func.count()).select_from(Equipment).where(*overdue_filters)) or 0

    occurrence_filters = [Occurrence.status.in_(["open", "in_progress"])]
    if location_id:
        occurrence_filters.append(Occurrence.environment_id == location_id)
    if period_start:
        occurrence_filters.append(
            Occurrence.created_at >= datetime.combine(period_start, datetime.min.time(), timezone.utc)
        )
    if period_end:
        occurrence_filters.append(
            Occurrence.created_at < datetime.combine(period_end + timedelta(days=1), datetime.min.time(), timezone.utc)
        )
    if kind:
        occurrence_filters.append(
            Occurrence.equipment_id.in_(select(Equipment.id).where(Equipment.kind == kind))
        )
    open_occurrences = db.scalar(select(func.count()).select_from(Occurrence).where(*occurrence_filters)) or 0

    upcoming_end = period_end or (today + timedelta(days=30))
    upcoming_filters = [
        Equipment.status != "inactive",
        Equipment.next_maintenance_on >= (period_start or today),
        Equipment.next_maintenance_on <= upcoming_end,
        *equipment_filters,
    ]
    upcoming_maintenance = db.scalar(select(func.count()).select_from(Equipment).where(*upcoming_filters)) or 0
    return DashboardResponse(
        reference_at=_now_utc(),
        period_start=period_start,
        period_end=period_end,
        filters={"kind": kind, "location_id": str(location_id) if location_id else None},
        total_equipment=total_equipment,
        functioning_equipment=functioning_equipment,
        equipment_in_maintenance=equipment_in_maintenance,
        overdue_maintenance=overdue_maintenance,
        open_occurrences=open_occurrences,
        upcoming_maintenance=upcoming_maintenance,
        definitions={
            "total_equipment": "Equipamentos cadastrados conforme os filtros.",
            "functioning_equipment": "Equipamentos com situação ativa.",
            "equipment_in_maintenance": "Equipamentos com situação em manutenção.",
            "overdue_maintenance": "Equipamentos ativos cuja próxima manutenção já venceu.",
            "open_occurrences": "Ocorrências abertas ou em atendimento.",
            "upcoming_maintenance": "Equipamentos com próxima manutenção dentro da janela informada ou dos próximos 30 dias.",
        },
    )


@app.get(
    "/api/equipment/{equipment_id}/warranties",
    response_model=list[WarrantyResponse],
    tags=["garantias e relatórios"],
)
def list_equipment_warranties(
    equipment_id: UUID,
    _context: AuthContext = Depends(require_permission("warranty:read")),
    db: Session = Depends(get_db),
) -> list[WarrantyResponse]:
    if db.get(Equipment, equipment_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    warranties = db.scalars(
        select(EquipmentWarranty)
        .where(EquipmentWarranty.equipment_id == equipment_id)
        .order_by(EquipmentWarranty.starts_on.desc(), EquipmentWarranty.created_at.desc())
    ).all()
    return [_warranty_response(item) for item in warranties]


@app.post(
    "/api/equipment/{equipment_id}/warranties",
    response_model=WarrantyResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["garantias e relatórios"],
)
def create_equipment_warranty(
    equipment_id: UUID,
    payload: WarrantyCreateRequest,
    context: AuthContext = Depends(require_permission("warranty:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> WarrantyResponse:
    if db.get(Equipment, equipment_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="equipment not found")
    warranty = EquipmentWarranty(
        equipment_id=equipment_id,
        supplier=payload.supplier,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        terms=payload.terms,
        created_by_id=context.user.id,
    )
    db.add(warranty)
    try:
        db.flush()
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="equipment_warranty",
                entity_id=warranty.id,
                action="equipment_warranty.created",
                new_state={"equipment_id": str(equipment_id), "supplier": payload.supplier},
                reason=payload.reason,
            )
        )
        db.commit()
        db.refresh(warranty)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="warranty unavailable") from error
    return _warranty_response(warranty)


@app.get(
    "/api/costs",
    response_model=list[MaintenanceCostResponse],
    tags=["garantias e relatórios"],
)
def list_maintenance_costs(
    equipment_id: UUID | None = None,
    maintenance_id: UUID | None = None,
    _context: AuthContext = Depends(require_permission("cost:read")),
    db: Session = Depends(get_db),
) -> list[MaintenanceCostResponse]:
    filters = []
    if equipment_id:
        filters.append(MaintenanceCost.equipment_id == equipment_id)
    if maintenance_id:
        filters.append(MaintenanceCost.maintenance_id == maintenance_id)
    costs = db.scalars(
        select(MaintenanceCost).where(*filters).order_by(MaintenanceCost.created_at.desc())
    ).all()
    return [_cost_response(item) for item in costs]


@app.post(
    "/api/maintenances/{maintenance_id}/costs",
    response_model=MaintenanceCostResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["garantias e relatórios"],
)
def create_maintenance_cost(
    maintenance_id: UUID,
    payload: MaintenanceCostCreateRequest,
    context: AuthContext = Depends(require_permission("cost:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MaintenanceCostResponse:
    maintenance = db.get(Maintenance, maintenance_id)
    if maintenance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="maintenance not found")
    cost = MaintenanceCost(
        maintenance_id=maintenance.id,
        equipment_id=maintenance.equipment_id,
        amount=payload.amount,
        currency=payload.currency,
        source=payload.source,
        reference=payload.reference,
        note=payload.note,
        created_by_id=context.user.id,
    )
    db.add(cost)
    try:
        db.flush()
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="maintenance_cost",
                entity_id=cost.id,
                action="maintenance_cost.recorded",
                new_state={
                    "maintenance_id": str(maintenance.id),
                    "amount": str(payload.amount),
                    "currency": payload.currency,
                },
                reason=payload.reason,
            )
        )
        db.commit()
        db.refresh(cost)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="cost unavailable") from error
    return _cost_response(cost)


@app.get(
    "/api/components",
    response_model=ComponentHistoryListResponse,
    tags=["garantias e relatórios"],
)
def list_component_history(
    equipment_id: UUID | None = None,
    maintenance_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("report:read")),
    db: Session = Depends(get_db),
) -> ComponentHistoryListResponse:
    filters = []
    if maintenance_id:
        filters.append(MaintenanceComponent.maintenance_id == maintenance_id)
    if equipment_id:
        filters.append(Maintenance.equipment_id == equipment_id)
    join_query = select(MaintenanceComponent).join(
        Maintenance, Maintenance.id == MaintenanceComponent.maintenance_id
    )
    total_query = (
        select(func.count())
        .select_from(MaintenanceComponent)
        .join(Maintenance, Maintenance.id == MaintenanceComponent.maintenance_id)
        .where(*filters)
    )
    total = db.scalar(total_query) or 0
    components = db.scalars(
        join_query.where(*filters)
        .order_by(MaintenanceComponent.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    items = []
    for component in components:
        maintenance = db.get(Maintenance, component.maintenance_id)
        if maintenance is not None:
            items.append(
                ComponentHistoryResponse(
                    id=component.id,
                    maintenance_id=component.maintenance_id,
                    equipment_id=maintenance.equipment_id,
                    component_name=component.component_name,
                    quantity=component.quantity,
                    observation=component.observation,
                    created_at=component.created_at,
                )
            )
    return ComponentHistoryListResponse(items=items, total=total, limit=limit, offset=offset)


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _report_data(
    db: Session,
    *,
    from_date: date | None,
    to_date: date | None,
    equipment_id: UUID | None,
    environment_id: UUID | None,
    kind: EquipmentKind | None,
) -> ReportResponse:
    if from_date is not None and to_date is not None and to_date < from_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="report end must not precede start")
    equipment_filters = []
    if equipment_id:
        equipment_filters.append(Equipment.id == equipment_id)
    if environment_id:
        equipment_filters.append(Equipment.location_id == environment_id)
    if kind:
        equipment_filters.append(Equipment.kind == kind)
    equipment_items = db.scalars(select(Equipment).where(*equipment_filters).order_by(Equipment.asset_tag, Equipment.id)).all()
    rows: list[dict[str, object]] = []
    maintenance_count = 0
    component_count = 0
    warranty_count = 0
    total_cost = Decimal("0")
    for equipment in equipment_items:
        maintenance_filters = [Maintenance.equipment_id == equipment.id]
        if from_date:
            maintenance_filters.append(
                Maintenance.created_at >= datetime.combine(from_date, datetime.min.time(), timezone.utc)
            )
        if to_date:
            maintenance_filters.append(
                Maintenance.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time(), timezone.utc)
            )
        maintenance_items = db.scalars(select(Maintenance).where(*maintenance_filters)).all()
        maintenance_ids = [item.id for item in maintenance_items]
        equipment_maintenance_count = len(maintenance_items)
        equipment_component_count = 0
        if maintenance_ids:
            equipment_component_count = db.scalar(
                select(func.count()).select_from(MaintenanceComponent).where(MaintenanceComponent.maintenance_id.in_(maintenance_ids))
            ) or 0
        equipment_cost = db.scalar(
            select(func.coalesce(func.sum(MaintenanceCost.amount), 0)).where(
                MaintenanceCost.equipment_id == equipment.id,
                *([MaintenanceCost.created_at >= datetime.combine(from_date, datetime.min.time(), timezone.utc)] if from_date else []),
                *([MaintenanceCost.created_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time(), timezone.utc)] if to_date else []),
            )
        ) or 0
        equipment_warranty_count = db.scalar(
            select(func.count()).select_from(EquipmentWarranty).where(EquipmentWarranty.equipment_id == equipment.id)
        ) or 0
        maintenance_count += equipment_maintenance_count
        component_count += equipment_component_count
        warranty_count += equipment_warranty_count
        total_cost += Decimal(str(equipment_cost))
        rows.append(
            {
                "equipment_id": str(equipment.id),
                "asset_tag": equipment.asset_tag or "",
                "kind": equipment.kind,
                "status": equipment.status,
                "location_id": str(equipment.location_id),
                "maintenance_count": equipment_maintenance_count,
                "component_count": equipment_component_count,
                "warranty_count": equipment_warranty_count,
                "cost_total": float(equipment_cost),
            }
        )
    return ReportResponse(
        reference_at=_now_utc(),
        filters={
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
            "equipment_id": str(equipment_id) if equipment_id else None,
            "environment_id": str(environment_id) if environment_id else None,
            "kind": kind,
        },
        equipment_count=len(equipment_items),
        maintenance_count=maintenance_count,
        component_count=component_count,
        warranty_count=warranty_count,
        total_cost=float(total_cost),
        rows=rows,
    )


@app.get(
    "/api/reports/inventory",
    response_model=ReportResponse,
    tags=["garantias e relatórios"],
)
def inventory_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    equipment_id: UUID | None = None,
    environment_id: UUID | None = None,
    kind: EquipmentKind | None = None,
    _context: AuthContext = Depends(require_permission("report:read")),
    db: Session = Depends(get_db),
) -> ReportResponse:
    return _report_data(
        db,
        from_date=from_date,
        to_date=to_date,
        equipment_id=equipment_id,
        environment_id=environment_id,
        kind=kind,
    )


@app.get(
    "/api/reports/inventory.csv",
    tags=["garantias e relatórios"],
)
def inventory_report_csv(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    equipment_id: UUID | None = None,
    environment_id: UUID | None = None,
    kind: EquipmentKind | None = None,
    _context: AuthContext = Depends(require_permission("report:export")),
    db: Session = Depends(get_db),
) -> Response:
    report = _report_data(
        db,
        from_date=from_date,
        to_date=to_date,
        equipment_id=equipment_id,
        environment_id=environment_id,
        kind=kind,
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "equipment_id",
            "asset_tag",
            "kind",
            "status",
            "location_id",
            "maintenance_count",
            "component_count",
            "warranty_count",
            "cost_total",
        ],
    )
    writer.writeheader()
    for row in report.rows:
        writer.writerow({key: _csv_safe(row.get(key)) for key in writer.fieldnames})
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=inventario-relatorio.csv"},
    )


def _prediction_policy_response(policy: FailurePredictionPolicy) -> PredictionPolicyResponse:
    return PredictionPolicyResponse(
        id=policy.id,
        name=policy.name,
        version=policy.version,
        status=policy.status,
        baseline_version=policy.baseline_version,
        horizon_days=policy.horizon_days,
        min_history_count=policy.min_history_count,
        min_confidence=float(policy.min_confidence),
        evaluation_approved=policy.evaluation_approved,
        evaluation_summary=policy.evaluation_summary,
        created_by_id=policy.created_by_id,
        enabled_by_id=policy.enabled_by_id,
        enabled_at=policy.enabled_at,
        disabled_at=policy.disabled_at,
        disable_reason=policy.disable_reason,
        created_at=policy.created_at,
    )


def _prediction_evaluation_response(
    evaluation: PredictionEvaluation,
) -> PredictionEvaluationResponse:
    return PredictionEvaluationResponse(
        id=evaluation.id,
        policy_id=evaluation.policy_id,
        dataset_version=evaluation.dataset_version,
        run_key=evaluation.run_key,
        evaluated_for=evaluation.evaluated_for,
        sample_count=evaluation.sample_count,
        labeled_count=evaluation.labeled_count,
        baseline_precision=(
            float(evaluation.baseline_precision)
            if evaluation.baseline_precision is not None
            else None
        ),
        baseline_recall=(
            float(evaluation.baseline_recall)
            if evaluation.baseline_recall is not None
            else None
        ),
        heuristic_precision=(
            float(evaluation.heuristic_precision)
            if evaluation.heuristic_precision is not None
            else None
        ),
        heuristic_recall=(
            float(evaluation.heuristic_recall)
            if evaluation.heuristic_recall is not None
            else None
        ),
        false_positives=evaluation.false_positives,
        false_negatives=evaluation.false_negatives,
        abstentions=evaluation.abstentions,
        metrics=evaluation.metrics,
        evaluated_by_id=evaluation.evaluated_by_id,
        created_at=evaluation.created_at,
    )


def _failure_prediction_response(
    prediction: FailurePrediction,
) -> FailurePredictionResponse:
    return FailurePredictionResponse(
        id=prediction.id,
        policy_id=prediction.policy_id,
        equipment_id=prediction.equipment_id,
        generated_for=prediction.generated_for,
        horizon_end=prediction.horizon_end,
        score=float(prediction.score),
        confidence=float(prediction.confidence),
        risk_level=prediction.risk_level,
        status=prediction.status,
        rationale=prediction.rationale,
        feature_snapshot=prediction.feature_snapshot,
        idempotency_key=prediction.idempotency_key,
        decided_by_id=prediction.decided_by_id,
        decided_at=prediction.decided_at,
        decision_reason=prediction.decision_reason,
        created_at=prediction.created_at,
    )


def _prediction_notification_response(
    notification: PredictionNotification,
) -> PredictionNotificationResponse:
    return PredictionNotificationResponse(
        id=notification.id,
        prediction_id=notification.prediction_id,
        channel=notification.channel,
        recipient_label=notification.recipient_label,
        idempotency_key=notification.idempotency_key,
        status=notification.status,
        attempts=notification.attempts,
        last_error=notification.last_error,
        sent_at=notification.sent_at,
        created_by_id=notification.created_by_id,
        created_at=notification.created_at,
    )


def _prediction_score(
    *,
    policy: FailurePredictionPolicy,
    features: dict[str, object],
) -> tuple[float, float, str, dict[str, object]]:
    occurrence_count = int(features["occurrence_count"])
    corrective_count = int(features["corrective_maintenance_count"])
    overdue = bool(features["maintenance_overdue"])
    due_soon = bool(features["maintenance_due_within_horizon"])
    history_count = int(features["history_count"])
    score = min(
        1.0,
        occurrence_count * 0.20
        + corrective_count * 0.30
        + (0.20 if overdue else 0.0)
        + (0.15 if due_soon else 0.0),
    )
    confidence = min(1.0, history_count / max(1, policy.min_history_count * 2))
    if confidence < float(policy.min_confidence):
        risk_level = "abstain"
        explanation = "Abstenção: histórico insuficiente para o limiar de confiança."
    elif score >= 0.70:
        risk_level = "high"
        explanation = "Sinais determinísticos combinados superaram o limiar alto."
    elif score >= 0.40:
        risk_level = "medium"
        explanation = "Sinais determinísticos combinados superaram o limiar de atenção."
    else:
        risk_level = "low"
        explanation = "Sinais observados permaneceram abaixo do limiar de atenção."
    rationale = {
        "method": policy.baseline_version,
        "explanation": explanation,
        "signals": {
            "occurrence_count": occurrence_count,
            "corrective_maintenance_count": corrective_count,
            "maintenance_overdue": overdue,
            "maintenance_due_within_horizon": due_soon,
        },
        "thresholds": {
            "medium_score": 0.40,
            "high_score": 0.70,
            "minimum_confidence": float(policy.min_confidence),
        },
        "human_action_required": True,
        "does_not_change_state": True,
    }
    return score, confidence, risk_level, rationale


def _prediction_features(
    db: Session,
    *,
    equipment: Equipment,
    as_of: date,
    horizon_days: int,
    lookback_days: int = 365,
) -> dict[str, object]:
    lookback_start = as_of - timedelta(days=lookback_days)
    start_at = datetime.combine(lookback_start, datetime.min.time(), timezone.utc)
    end_at = datetime.combine(as_of + timedelta(days=1), datetime.min.time(), timezone.utc)
    occurrence_count = db.scalar(
        select(func.count())
        .select_from(Occurrence)
        .where(
            Occurrence.equipment_id == equipment.id,
            Occurrence.created_at >= start_at,
            Occurrence.created_at < end_at,
        )
    ) or 0
    corrective_count = db.scalar(
        select(func.count())
        .select_from(Maintenance)
        .where(
            Maintenance.equipment_id == equipment.id,
            Maintenance.kind == "corrective",
            Maintenance.status != "cancelled",
            Maintenance.created_at >= start_at,
            Maintenance.created_at < end_at,
        )
    ) or 0
    maintenance_overdue = bool(
        equipment.next_maintenance_on is not None
        and equipment.next_maintenance_on < as_of
    )
    maintenance_due_within_horizon = bool(
        equipment.next_maintenance_on is not None
        and as_of <= equipment.next_maintenance_on <= as_of + timedelta(days=horizon_days)
    )
    return {
        "lookback_days": lookback_days,
        "occurrence_count": int(occurrence_count),
        "corrective_maintenance_count": int(corrective_count),
        "maintenance_overdue": maintenance_overdue,
        "maintenance_due_within_horizon": maintenance_due_within_horizon,
        "history_count": int(occurrence_count) + int(corrective_count),
    }


_SYNTHETIC_PREDICTION_EVALUATION = (
    ({"occurrence_count": 0, "corrective_maintenance_count": 0, "maintenance_overdue": False, "maintenance_due_within_horizon": False, "history_count": 0}, 0),
    ({"occurrence_count": 1, "corrective_maintenance_count": 0, "maintenance_overdue": False, "maintenance_due_within_horizon": True, "history_count": 1}, 0),
    ({"occurrence_count": 2, "corrective_maintenance_count": 1, "maintenance_overdue": True, "maintenance_due_within_horizon": False, "history_count": 3}, 1),
    ({"occurrence_count": 3, "corrective_maintenance_count": 0, "maintenance_overdue": False, "maintenance_due_within_horizon": False, "history_count": 3}, 1),
    ({"occurrence_count": 0, "corrective_maintenance_count": 2, "maintenance_overdue": True, "maintenance_due_within_horizon": False, "history_count": 2}, 1),
    ({"occurrence_count": 0, "corrective_maintenance_count": 0, "maintenance_overdue": False, "maintenance_due_within_horizon": False, "history_count": 0}, 0),
    ({"occurrence_count": 1, "corrective_maintenance_count": 1, "maintenance_overdue": False, "maintenance_due_within_horizon": True, "history_count": 2}, 1),
    ({"occurrence_count": 2, "corrective_maintenance_count": 0, "maintenance_overdue": False, "maintenance_due_within_horizon": False, "history_count": 2}, 0),
)


def _safe_metric(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _evaluate_synthetic_policy(
    policy: FailurePredictionPolicy,
) -> dict[str, object]:
    results: list[tuple[int, int, str]] = []
    for features, label in _SYNTHETIC_PREDICTION_EVALUATION:
        score, confidence, risk_level, _rationale = _prediction_score(
            policy=policy, features=features
        )
        predicted = int(risk_level in {"high", "medium"})
        results.append((predicted, label, risk_level))
    true_positive = sum(predicted == 1 and label == 1 for predicted, label, _ in results)
    false_positive = sum(predicted == 1 and label == 0 for predicted, label, _ in results)
    false_negative = sum(predicted == 0 and label == 1 for predicted, label, _ in results)
    positive_count = sum(label for _, label, _ in results)
    predicted_positive = sum(predicted for predicted, _, _ in results)
    abstentions = sum(risk_level == "abstain" for _, _, risk_level in results)
    heuristic_precision = _safe_metric(true_positive, predicted_positive)
    heuristic_recall = _safe_metric(true_positive, positive_count)
    return {
        "sample_count": len(results),
        "labeled_count": positive_count,
        "baseline_precision": 0.0,
        "baseline_recall": 0.0,
        "heuristic_precision": heuristic_precision,
        "heuristic_recall": heuristic_recall,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "abstentions": abstentions,
        "metrics": {
            "dataset": "synthetic, sem dados pessoais ou externos",
            "dataset_version": "synthetic-v1",
            "positive_definition": "falha corretiva observada no conjunto sintético",
            "baseline": "sempre abstém e não recomenda ação",
            "benefit_over_baseline": bool(
                heuristic_recall is not None and heuristic_recall > 0.0
            ),
            "thresholds": {
                "medium_score": 0.40,
                "high_score": 0.70,
                "minimum_confidence": float(policy.min_confidence),
            },
            "reproducible": True,
            "limitations": [
                "conjunto sintético não prova desempenho operacional",
                "não há causalidade nem garantia de falha",
            ],
        },
    }


def _generate_failure_predictions(
    db: Session,
    *,
    policy: FailurePredictionPolicy,
    as_of: date,
    context: AuthContext,
    reason: str,
    action: str,
) -> PredictionGenerationResponse:
    equipment_items = db.scalars(
        select(Equipment)
        .where(Equipment.active.is_(True), Equipment.status != "inactive")
        .order_by(Equipment.id)
    ).all()
    generated: list[FailurePrediction] = []
    for equipment in equipment_items:
        features = _prediction_features(
            db,
            equipment=equipment,
            as_of=as_of,
            horizon_days=policy.horizon_days,
        )
        score, confidence, risk_level, rationale = _prediction_score(
            policy=policy, features=features
        )
        idempotency_key = (
            f"policy:{policy.id}:equipment:{equipment.id}:as_of:{as_of.isoformat()}"
        )
        existing = db.scalar(
            select(FailurePrediction).where(
                FailurePrediction.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            generated.append(existing)
            continue
        generated.append(
            FailurePrediction(
                policy_id=policy.id,
                equipment_id=equipment.id,
                generated_for=as_of,
                horizon_end=as_of + timedelta(days=policy.horizon_days),
                score=score,
                confidence=confidence,
                risk_level=risk_level,
                status="recommended",
                rationale=rationale,
                feature_snapshot=features,
                idempotency_key=idempotency_key,
            )
        )
    new_items = [item for item in generated if item.id is None]
    for item in new_items:
        db.add(item)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="failure_prediction_policy",
            entity_id=policy.id,
            action=action,
            new_state={
                "policy_id": str(policy.id),
                "as_of": as_of.isoformat(),
                "new_predictions": len(new_items),
                "recommendations": len(generated),
                "abstentions": sum(item.risk_level == "abstain" for item in generated),
            },
            reason=reason,
        )
    )
    try:
        db.commit()
        for item in generated:
            db.refresh(item)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction generation unavailable",
        ) from error
    return PredictionGenerationResponse(
        generated=len(new_items),
        abstained=sum(item.risk_level == "abstain" for item in generated),
        items=[_failure_prediction_response(item) for item in generated],
    )


@app.get(
    "/api/failure-predictions/policies",
    response_model=PredictionPolicyListResponse,
    tags=["previsões"],
)
def list_prediction_policies(
    policy_status: PredictionPolicyStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("prediction:read")),
    db: Session = Depends(get_db),
) -> PredictionPolicyListResponse:
    filters = []
    if policy_status:
        filters.append(FailurePredictionPolicy.status == policy_status)
    total = db.scalar(
        select(func.count()).select_from(FailurePredictionPolicy).where(*filters)
    ) or 0
    policies = db.scalars(
        select(FailurePredictionPolicy)
        .where(*filters)
        .order_by(FailurePredictionPolicy.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return PredictionPolicyListResponse(
        items=[_prediction_policy_response(item) for item in policies],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/api/failure-predictions/policies",
    response_model=PredictionPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["previsões"],
)
def create_prediction_policy(
    payload: PredictionPolicyCreateRequest,
    context: AuthContext = Depends(require_permission("prediction:manage")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PredictionPolicyResponse:
    policy = FailurePredictionPolicy(
        name=payload.name,
        version=payload.version,
        status="disabled",
        baseline_version=payload.baseline_version,
        horizon_days=payload.horizon_days,
        min_history_count=payload.min_history_count,
        min_confidence=payload.min_confidence,
        evaluation_approved=False,
        created_by_id=context.user.id,
    )
    db.add(policy)
    try:
        db.flush()
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="failure_prediction_policy",
                entity_id=policy.id,
                action="prediction_policy.created",
                new_state={
                    "name": policy.name,
                    "version": policy.version,
                    "baseline_version": policy.baseline_version,
                    "status": policy.status,
                },
                reason=payload.reason,
            )
        )
        db.commit()
        db.refresh(policy)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="prediction policy version already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction policy unavailable",
        ) from error
    return _prediction_policy_response(policy)


@app.post(
    "/api/failure-predictions/evaluate",
    response_model=PredictionEvaluationResponse,
    tags=["previsões"],
)
def evaluate_prediction_policy(
    payload: PredictionEvaluationRequest,
    context: AuthContext = Depends(require_permission("prediction:manage")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PredictionEvaluationResponse:
    policy = db.get(FailurePredictionPolicy, payload.policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prediction policy not found")
    evaluated_for = payload.evaluated_for or date.today()
    run_key = f"{payload.dataset_version}:{evaluated_for.isoformat()}:v{policy.version}"
    stats = _evaluate_synthetic_policy(policy)
    evaluation = db.scalar(
        select(PredictionEvaluation).where(
            PredictionEvaluation.policy_id == policy.id,
            PredictionEvaluation.run_key == run_key,
        )
    )
    if evaluation is None:
        evaluation = PredictionEvaluation(
            policy_id=policy.id,
            dataset_version=payload.dataset_version,
            run_key=run_key,
            evaluated_for=evaluated_for,
            sample_count=stats["sample_count"],
            labeled_count=stats["labeled_count"],
            baseline_precision=stats["baseline_precision"],
            baseline_recall=stats["baseline_recall"],
            heuristic_precision=stats["heuristic_precision"],
            heuristic_recall=stats["heuristic_recall"],
            false_positives=stats["false_positives"],
            false_negatives=stats["false_negatives"],
            abstentions=stats["abstentions"],
            metrics=stats["metrics"],
            evaluated_by_id=context.user.id,
        )
        db.add(evaluation)
    approved = bool(payload.approve_evaluation and stats["metrics"]["benefit_over_baseline"])
    policy.evaluation_approved = approved
    policy.evaluation_summary = {
        **stats,
        "evaluation_approved": approved,
        "approved_by_id": str(context.user.id) if approved else None,
    }
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="failure_prediction_policy",
            entity_id=policy.id,
            action="prediction_policy.evaluated",
            new_state={
                "dataset_version": payload.dataset_version,
                "run_key": run_key,
                "evaluation_approved": approved,
            },
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(evaluation)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction evaluation unavailable",
        ) from error
    return _prediction_evaluation_response(evaluation)


@app.post(
    "/api/failure-predictions/policies/{policy_id}/enable",
    response_model=PredictionPolicyResponse,
    tags=["previsões"],
)
def enable_prediction_policy(
    policy_id: UUID,
    payload: PredictionPolicyActionRequest,
    context: AuthContext = Depends(require_permission("prediction:manage")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PredictionPolicyResponse:
    policy = db.get(FailurePredictionPolicy, policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prediction policy not found")
    if not policy.evaluation_approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="prediction policy requires approved evaluation",
        )
    policy.status = "enabled"
    policy.enabled_by_id = context.user.id
    policy.enabled_at = _now_utc()
    policy.disabled_at = None
    policy.disable_reason = None
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="failure_prediction_policy",
            entity_id=policy.id,
            action="prediction_policy.enabled",
            new_state={"status": policy.status, "enabled_by_id": str(context.user.id)},
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(policy)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction policy unavailable",
        ) from error
    return _prediction_policy_response(policy)


@app.post(
    "/api/failure-predictions/policies/{policy_id}/disable",
    response_model=PredictionPolicyResponse,
    tags=["previsões"],
)
def disable_prediction_policy(
    policy_id: UUID,
    payload: PredictionPolicyActionRequest,
    context: AuthContext = Depends(require_permission("prediction:manage")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PredictionPolicyResponse:
    policy = db.get(FailurePredictionPolicy, policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prediction policy not found")
    policy.status = "disabled"
    policy.disabled_at = _now_utc()
    policy.disable_reason = payload.reason
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="failure_prediction_policy",
            entity_id=policy.id,
            action="prediction_policy.disabled",
            new_state={"status": policy.status},
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(policy)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction policy unavailable",
        ) from error
    return _prediction_policy_response(policy)


@app.get(
    "/api/failure-predictions",
    response_model=FailurePredictionListResponse,
    tags=["previsões"],
)
def list_failure_predictions(
    policy_id: UUID | None = None,
    prediction_status: PredictionStatus | None = Query(default=None, alias="status"),
    risk_level: PredictionRiskLevel | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("prediction:read")),
    db: Session = Depends(get_db),
) -> FailurePredictionListResponse:
    filters = []
    if policy_id:
        filters.append(FailurePrediction.policy_id == policy_id)
    if prediction_status:
        filters.append(FailurePrediction.status == prediction_status)
    if risk_level:
        filters.append(FailurePrediction.risk_level == risk_level)
    total = db.scalar(select(func.count()).select_from(FailurePrediction).where(*filters)) or 0
    predictions = db.scalars(
        select(FailurePrediction)
        .where(*filters)
        .order_by(FailurePrediction.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return FailurePredictionListResponse(
        items=[_failure_prediction_response(item) for item in predictions],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/api/failure-predictions/simulate",
    response_model=PredictionGenerationResponse,
    tags=["previsões"],
)
def simulate_failure_predictions(
    payload: PredictionSimulationRequest,
    context: AuthContext = Depends(require_permission("prediction:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PredictionGenerationResponse:
    policy = db.get(FailurePredictionPolicy, payload.policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prediction policy not found")
    return _generate_failure_predictions(
        db,
        policy=policy,
        as_of=payload.as_of or date.today(),
        context=context,
        reason=payload.reason,
        action="prediction.simulated",
    )


@app.post(
    "/api/failure-predictions/generate",
    response_model=PredictionGenerationResponse,
    tags=["previsões"],
)
def generate_failure_predictions(
    payload: PredictionSimulationRequest,
    context: AuthContext = Depends(require_permission("prediction:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PredictionGenerationResponse:
    policy = db.get(FailurePredictionPolicy, payload.policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prediction policy not found")
    if policy.status != "enabled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="prediction policy is disabled",
        )
    return _generate_failure_predictions(
        db,
        policy=policy,
        as_of=payload.as_of or date.today(),
        context=context,
        reason=payload.reason,
        action="prediction.generated",
    )


@app.post(
    "/api/failure-predictions/{prediction_id}/decision",
    response_model=FailurePredictionResponse,
    tags=["previsões"],
)
def decide_failure_prediction(
    prediction_id: UUID,
    payload: PredictionDecisionRequest,
    context: AuthContext = Depends(require_permission("prediction:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> FailurePredictionResponse:
    prediction = db.get(FailurePrediction, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prediction not found")
    if prediction.status != "recommended":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="prediction already decided",
        )
    prediction.status = payload.decision
    prediction.decided_by_id = context.user.id
    prediction.decided_at = _now_utc()
    prediction.decision_reason = payload.reason
    db.add(
        AuditEvent(
            actor_id=context.user.id,
            entity_type="failure_prediction",
            entity_id=prediction.id,
            action="prediction.decision",
            new_state={"status": prediction.status},
            reason=payload.reason,
        )
    )
    try:
        db.commit()
        db.refresh(prediction)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction decision unavailable",
        ) from error
    return _failure_prediction_response(prediction)


@app.post(
    "/api/failure-predictions/{prediction_id}/mock-notify",
    response_model=PredictionNotificationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["previsões"],
)
def mock_notify_failure_prediction(
    prediction_id: UUID,
    payload: PredictionMockNotificationRequest,
    context: AuthContext = Depends(require_permission("prediction:write")),
    _csrf_context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> PredictionNotificationResponse:
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="explicit confirmation is required",
        )
    prediction = db.get(FailurePrediction, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prediction not found")
    if prediction.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="prediction must be confirmed before notification",
        )
    idempotency_key = f"prediction:{prediction.id}:mock_email:{payload.recipient_label}"
    existing = db.scalar(
        select(PredictionNotification).where(
            PredictionNotification.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return _prediction_notification_response(existing)
    notification = PredictionNotification(
        prediction_id=prediction.id,
        channel="mock_email",
        recipient_label=payload.recipient_label,
        idempotency_key=idempotency_key,
        status="sent",
        attempts=1,
        sent_at=_now_utc(),
        created_by_id=context.user.id,
    )
    db.add(notification)
    try:
        db.flush()
        db.add(
            AuditEvent(
                actor_id=context.user.id,
                entity_type="failure_prediction",
                entity_id=prediction.id,
                action="prediction.notification_mock_dispatched",
                new_state={
                    "channel": "mock_email",
                    "recipient_label": payload.recipient_label,
                    "notification_id": str(notification.id),
                },
                reason=payload.reason,
            )
        )
        db.commit()
        db.refresh(notification)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="prediction notification already exists",
        ) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="prediction notification unavailable",
        ) from error
    return _prediction_notification_response(notification)


@app.get(
    "/api/failure-predictions/notifications",
    response_model=PredictionNotificationListResponse,
    tags=["previsões"],
)
def list_prediction_notifications(
    notification_status: Literal["queued", "sent", "failed"] | None = Query(
        default=None, alias="status"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    _context: AuthContext = Depends(require_permission("prediction:read")),
    db: Session = Depends(get_db),
) -> PredictionNotificationListResponse:
    filters = []
    if notification_status:
        filters.append(PredictionNotification.status == notification_status)
    total = db.scalar(
        select(func.count()).select_from(PredictionNotification).where(*filters)
    ) or 0
    notifications = db.scalars(
        select(PredictionNotification)
        .where(*filters)
        .order_by(PredictionNotification.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return PredictionNotificationListResponse(
        items=[_prediction_notification_response(item) for item in notifications],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/failure-predictions/monitoring",
    response_model=PredictionMonitoringResponse,
    tags=["previsões"],
)
def monitor_failure_predictions(
    _context: AuthContext = Depends(require_permission("prediction:read")),
    db: Session = Depends(get_db),
) -> PredictionMonitoringResponse:
    enabled_policy = db.scalar(
        select(FailurePredictionPolicy)
        .where(FailurePredictionPolicy.status == "enabled")
        .order_by(FailurePredictionPolicy.created_at.desc())
    )
    latest_evaluation = db.scalar(
        select(PredictionEvaluation).order_by(PredictionEvaluation.created_at.desc())
    )
    recommendation_count = db.scalar(select(func.count()).select_from(FailurePrediction)) or 0
    abstention_count = db.scalar(
        select(func.count())
        .select_from(FailurePrediction)
        .where(FailurePrediction.risk_level == "abstain")
    ) or 0
    confirmed_count = db.scalar(
        select(func.count())
        .select_from(FailurePrediction)
        .where(FailurePrediction.status == "confirmed")
    ) or 0
    rejected_count = db.scalar(
        select(func.count())
        .select_from(FailurePrediction)
        .where(FailurePrediction.status.in_(["rejected", "dismissed"]))
    ) or 0
    evaluation_response = (
        _prediction_evaluation_response(latest_evaluation)
        if latest_evaluation is not None
        else None
    )
    if latest_evaluation is None:
        degradation = {
            "status": "review_required",
            "degradation_detected": True,
            "reason": "nenhuma avaliação reproduzível registrada",
            "automatic_action": "none",
        }
    else:
        heuristic_recall = latest_evaluation.heuristic_recall
        baseline_recall = latest_evaluation.baseline_recall
        degraded = (
            heuristic_recall is None
            or baseline_recall is None
            or heuristic_recall <= baseline_recall
        )
        degradation = {
            "status": "review_required" if degraded else "within_baseline",
            "degradation_detected": degraded,
            "reason": (
                "métrica não supera o baseline"
                if degraded
                else "métrica reproduzível supera o baseline sintético"
            ),
            "automatic_action": "none",
        }
    return PredictionMonitoringResponse(
        reference_at=_now_utc(),
        enabled_policy_id=enabled_policy.id if enabled_policy else None,
        recommendation_count=recommendation_count,
        abstention_count=abstention_count,
        confirmed_count=confirmed_count,
        rejected_count=rejected_count,
        latest_evaluation=evaluation_response,
        degradation=degradation,
    )
