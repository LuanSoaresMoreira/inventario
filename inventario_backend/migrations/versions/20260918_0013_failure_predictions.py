"""Adiciona recomendações determinísticas e notificações mock de falhas."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0013"
down_revision: str | None = "20260918_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "failure_prediction_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("baseline_version", sa.String(length=80), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("min_history_count", sa.Integer(), nullable=False),
        sa.Column("min_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("evaluation_approved", sa.Boolean(), nullable=False),
        sa.Column("evaluation_summary", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("enabled_by_id", sa.Uuid(), nullable=True),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disable_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('disabled', 'enabled', 'retired')",
            name="ck_failure_prediction_policies_status",
        ),
        sa.CheckConstraint(
            "horizon_days BETWEEN 1 AND 365",
            name="ck_failure_prediction_policies_horizon",
        ),
        sa.CheckConstraint(
            "min_history_count BETWEEN 0 AND 1000",
            name="ck_failure_prediction_policies_history",
        ),
        sa.CheckConstraint(
            "min_confidence >= 0 AND min_confidence <= 1",
            name="ck_failure_prediction_policies_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["enabled_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name", "version", name="uq_failure_prediction_policies_name_version"
        ),
    )
    op.create_index(
        "ix_failure_prediction_policies_status",
        "failure_prediction_policies",
        ["status"],
    )

    op.create_table(
        "failure_predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("generated_for", sa.Date(), nullable=False),
        sa.Column("horizon_end", sa.Date(), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.JSON(), nullable=False),
        sa.Column("feature_snapshot", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "risk_level IN ('high', 'medium', 'low', 'abstain')",
            name="ck_failure_predictions_risk_level",
        ),
        sa.CheckConstraint(
            "status IN ('recommended', 'confirmed', 'rejected', 'dismissed')",
            name="ck_failure_predictions_status",
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_failure_predictions_score"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_failure_predictions_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["failure_prediction_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_failure_predictions_idempotency"),
    )
    op.create_index(
        "ix_failure_predictions_policy_created",
        "failure_predictions",
        ["policy_id", "created_at"],
    )
    op.create_index(
        "ix_failure_predictions_equipment_status",
        "failure_predictions",
        ["equipment_id", "status"],
    )

    op.create_table(
        "prediction_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("run_key", sa.String(length=255), nullable=False),
        sa.Column("evaluated_for", sa.Date(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("labeled_count", sa.Integer(), nullable=False),
        sa.Column("baseline_precision", sa.Numeric(5, 4), nullable=True),
        sa.Column("baseline_recall", sa.Numeric(5, 4), nullable=True),
        sa.Column("heuristic_precision", sa.Numeric(5, 4), nullable=True),
        sa.Column("heuristic_recall", sa.Numeric(5, 4), nullable=True),
        sa.Column("false_positives", sa.Integer(), nullable=False),
        sa.Column("false_negatives", sa.Integer(), nullable=False),
        sa.Column("abstentions", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("evaluated_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["failure_prediction_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["evaluated_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_id", "run_key", name="uq_prediction_evaluations_policy_run"
        ),
    )
    op.create_index(
        "ix_prediction_evaluations_policy_evaluated",
        "prediction_evaluations",
        ["policy_id", "created_at"],
    )

    op.create_table(
        "prediction_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("prediction_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recipient_label", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "channel IN ('mock_email')",
            name="ck_prediction_notifications_channel",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'sent', 'failed')",
            name="ck_prediction_notifications_status",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"], ["failure_predictions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_prediction_notifications_idempotency"
        ),
    )
    op.create_index(
        "ix_prediction_notifications_status_created",
        "prediction_notifications",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prediction_notifications_status_created",
        table_name="prediction_notifications",
    )
    op.drop_table("prediction_notifications")
    op.drop_index(
        "ix_prediction_evaluations_policy_evaluated",
        table_name="prediction_evaluations",
    )
    op.drop_table("prediction_evaluations")
    op.drop_index(
        "ix_failure_predictions_equipment_status",
        table_name="failure_predictions",
    )
    op.drop_index(
        "ix_failure_predictions_policy_created",
        table_name="failure_predictions",
    )
    op.drop_table("failure_predictions")
    op.drop_index(
        "ix_failure_prediction_policies_status",
        table_name="failure_prediction_policies",
    )
    op.drop_table("failure_prediction_policies")
