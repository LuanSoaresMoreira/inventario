"""Adiciona resolução e comentários internos de ocorrências."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0007"
down_revision: str | None = "20260918_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("occurrences", sa.Column("resolution_reason", sa.Text(), nullable=True))
    op.add_column(
        "occurrences", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("occurrences", sa.Column("closed_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_occurrences_closed_by_id",
        "occurrences",
        "internal_users",
        ["closed_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "occurrence_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["occurrences.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["internal_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_occurrence_comments_occurrence",
        "occurrence_comments",
        ["occurrence_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_occurrence_comments_occurrence", table_name="occurrence_comments")
    op.drop_table("occurrence_comments")
    op.drop_constraint("fk_occurrences_closed_by_id", "occurrences", type_="foreignkey")
    op.drop_column("occurrences", "closed_by_id")
    op.drop_column("occurrences", "closed_at")
    op.drop_column("occurrences", "resolution_reason")
