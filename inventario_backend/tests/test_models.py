from inventario_backend.models import Base


def test_initial_domain_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "audit_events",
        "environments",
        "equipment",
        "equipment_warranties",
        "failure_prediction_policies",
        "failure_predictions",
        "internal_users",
        "maintenances",
        "maintenance_components",
        "maintenance_alerts",
        "maintenance_costs",
        "maintenance_plan_items",
        "maintenance_plans",
        "movements",
        "notification_deliveries",
        "occurrences",
        "occurrence_comments",
        "prediction_evaluations",
        "prediction_notifications",
        "user_sessions",
    }


def test_asset_tag_and_public_tokens_are_unique() -> None:
    equipment_constraints = Base.metadata.tables["equipment"].constraints
    occurrence_constraints = Base.metadata.tables["occurrences"].constraints

    assert any(
        constraint.columns.keys() == ["asset_tag"]
        and constraint.__class__.__name__ == "UniqueConstraint"
        for constraint in equipment_constraints
    )
    assert any(
        constraint.columns.keys() == ["public_tracking_token"]
        and constraint.__class__.__name__ == "UniqueConstraint"
        for constraint in occurrence_constraints
    )
