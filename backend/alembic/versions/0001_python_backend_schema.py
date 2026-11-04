"""Adopt the existing Hibernate schema and establish the Python-owned schema.

Revision ID: 0001_python_backend_schema
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from app.core.config import get_settings


revision = "0001_python_backend_schema"
down_revision = None
branch_labels = None
depends_on = None

EXPECTED_TABLES = {
    "interview",
    "interview_question",
    "interview_question_criteria",
    "interview_answer",
    "criterion_assessment",
    "interview_answer_strengths",
    "interview_answer_missing_concepts",
    "interview_answer_follow_up_criteria",
}


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    if "interview" in existing_tables:
        missing_tables = EXPECTED_TABLES - existing_tables
        if missing_tables:
            raise RuntimeError(
                "Existing InterviewOS schema is incomplete; refusing to create "
                f"overlapping tables: {', '.join(sorted(missing_tables))}"
            )
        _validate_existing_columns(bind)
        _make_timestamps_timezone_aware(bind)
        _add_missing_checks(bind)
    elif EXPECTED_TABLES.intersection(existing_tables):
        raise RuntimeError(
            "A partial InterviewOS schema exists without the interview table; "
            "inspect and repair it before running this migration."
        )
    else:
        _create_schema()

    _create_missing_indexes(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "interview" not in tables:
        return
    for table_name, column_name in (
        ("interview", "created_at"),
        ("interview_answer", "submitted_at"),
    ):
        column = next(
            item
            for item in inspector.get_columns(table_name)
            if item["name"] == column_name
        )
        if isinstance(column["type"], sa.DateTime) and column["type"].timezone:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.DateTime(timezone=False),
                postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
            )
    # Tables and rows are intentionally retained; this migration adopts existing
    # application data and cannot safely infer whether a table was pre-existing.


def _validate_existing_columns(bind) -> None:
    inspector = inspect(bind)
    required = {
        "interview": {
            "id", "target_role", "difficulty", "number_of_questions", "status",
            "created_at", "current_question_order",
        },
        "interview_question": {
            "id", "question_text", "question_order", "source", "interview_id",
        },
        "interview_question_criteria": {
            "interview_question_id", "criterion_order", "criterion",
        },
        "interview_answer": {
            "id", "candidate_answer", "submitted_at", "evaluation_status",
            "technical_accuracy", "completeness", "clarity", "depth",
            "overall_score", "feedback", "suggested_follow_up",
            "interview_question_id",
        },
        "criterion_assessment": {
            "id", "criterion", "status", "evidence", "interview_answer_id",
        },
        "interview_answer_strengths": {
            "interview_answer_id", "strength_order", "strength",
        },
        "interview_answer_missing_concepts": {
            "interview_answer_id", "concept_order", "concept",
        },
        "interview_answer_follow_up_criteria": {
            "interview_answer_id", "criterion_order", "criterion",
        },
    }
    for table_name, required_columns in required.items():
        present = {column["name"] for column in inspector.get_columns(table_name)}
        missing = required_columns - present
        if missing:
            raise RuntimeError(
                f"Existing table {table_name} is missing required columns: "
                f"{', '.join(sorted(missing))}"
            )


def _make_timestamps_timezone_aware(bind) -> None:
    inspector = inspect(bind)
    legacy_timezone = get_settings().legacy_timestamp_timezone
    if "'" in legacy_timezone or not legacy_timezone.strip():
        raise RuntimeError("LEGACY_TIMESTAMP_TIMEZONE must be a valid PostgreSQL timezone")
    for table_name, column_name in (
        ("interview", "created_at"),
        ("interview_answer", "submitted_at"),
    ):
        column = next(
            item
            for item in inspector.get_columns(table_name)
            if item["name"] == column_name
        )
        if isinstance(column["type"], sa.DateTime) and not column["type"].timezone:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.DateTime(timezone=False),
                type_=sa.DateTime(timezone=True),
                postgresql_using=(
                    f"{column_name} AT TIME ZONE '{legacy_timezone}'"
                ),
            )


def _add_missing_checks(bind) -> None:
    inspector = inspect(bind)
    checks = {
        "criterion_assessment": (
            "criterion_assessment_status_check",
            "status IN ('COVERED', 'PARTIALLY_COVERED', 'MISSING')",
        ),
    }
    for table_name, (name, condition) in checks.items():
        present = {item["name"] for item in inspector.get_check_constraints(table_name)}
        if name not in present:
            op.create_check_constraint(name, table_name, condition)


def _create_missing_indexes(bind) -> None:
    inspector = inspect(bind)
    indexes = {
        "interview_question": ("ix_interview_question_interview_id", ["interview_id"]),
        "interview_answer": (
            "ix_interview_answer_interview_question_id",
            ["interview_question_id"],
        ),
        "criterion_assessment": (
            "ix_criterion_assessment_interview_answer_id",
            ["interview_answer_id"],
        ),
    }
    for table_name, (name, columns) in indexes.items():
        present = {item["name"] for item in inspector.get_indexes(table_name)}
        if name not in present:
            op.create_index(name, table_name, columns, unique=False)


def _create_schema() -> None:
    op.create_table(
        "interview",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_role", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("number_of_questions", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="CREATED",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_question_order", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name="interview_difficulty_check",
        ),
        sa.CheckConstraint(
            "status IN ('CREATED', 'IN_PROGRESS', 'COMPLETED')",
            name="interview_status_check",
        ),
        sa.PrimaryKeyConstraint("id", name="interview_pkey"),
    )
    op.create_table(
        "interview_question",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.String(length=32),
            server_default="GENERATED",
            nullable=False,
        ),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "source IN ('GENERATED', 'FOLLOW_UP')",
            name="interview_question_source_check",
        ),
        sa.ForeignKeyConstraint(
            ["interview_id"],
            ["interview.id"],
            name="fk_interview_question_interview_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="interview_question_pkey"),
        sa.UniqueConstraint(
            "interview_id",
            "question_order",
            name="uk_interview_question_order",
        ),
    )
    op.create_index(
        "ix_interview_question_interview_id",
        "interview_question",
        ["interview_id"],
    )
    op.create_table(
        "interview_question_criteria",
        sa.Column("interview_question_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_order", sa.Integer(), nullable=False),
        sa.Column("criterion", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "criterion_order >= 0",
            name="interview_question_criteria_criterion_order_check",
        ),
        sa.ForeignKeyConstraint(
            ["interview_question_id"],
            ["interview_question.id"],
            name="fk_interview_question_criteria_question_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "interview_question_id",
            "criterion_order",
            name="interview_question_criteria_pkey",
        ),
    )
    op.create_table(
        "interview_answer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_answer", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "evaluation_status",
            sa.String(length=32),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("technical_accuracy", sa.Float(), nullable=True),
        sa.Column("completeness", sa.Float(), nullable=True),
        sa.Column("clarity", sa.Float(), nullable=True),
        sa.Column("depth", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("suggested_follow_up", sa.Text(), nullable=True),
        sa.Column("interview_question_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "evaluation_status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name="interview_answer_evaluation_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["interview_question_id"],
            ["interview_question.id"],
            name="fk_interview_answer_question_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="interview_answer_pkey"),
        sa.UniqueConstraint(
            "interview_question_id",
            name="uk_interview_answer_question",
        ),
    )
    op.create_index(
        "ix_interview_answer_interview_question_id",
        "interview_answer",
        ["interview_question_id"],
    )
    op.create_table(
        "criterion_assessment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("criterion", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("interview_answer_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('COVERED', 'PARTIALLY_COVERED', 'MISSING')",
            name="criterion_assessment_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["interview_answer_id"],
            ["interview_answer.id"],
            name="fk_criterion_assessment_answer_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="criterion_assessment_pkey"),
    )
    op.create_index(
        "ix_criterion_assessment_interview_answer_id",
        "criterion_assessment",
        ["interview_answer_id"],
    )
    op.create_table(
        "interview_answer_strengths",
        sa.Column("interview_answer_id", sa.Uuid(), nullable=False),
        sa.Column("strength_order", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "strength_order >= 0",
            name="interview_answer_strengths_strength_order_check",
        ),
        sa.ForeignKeyConstraint(
            ["interview_answer_id"],
            ["interview_answer.id"],
            name="fk_interview_answer_strengths_answer_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "interview_answer_id",
            "strength_order",
            name="interview_answer_strengths_pkey",
        ),
    )
    op.create_table(
        "interview_answer_missing_concepts",
        sa.Column("interview_answer_id", sa.Uuid(), nullable=False),
        sa.Column("concept_order", sa.Integer(), nullable=False),
        sa.Column("concept", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "concept_order >= 0",
            name="interview_answer_missing_concepts_concept_order_check",
        ),
        sa.ForeignKeyConstraint(
            ["interview_answer_id"],
            ["interview_answer.id"],
            name="fk_interview_answer_missing_concepts_answer_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "interview_answer_id",
            "concept_order",
            name="interview_answer_missing_concepts_pkey",
        ),
    )
    op.create_table(
        "interview_answer_follow_up_criteria",
        sa.Column("interview_answer_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_order", sa.Integer(), nullable=False),
        sa.Column("criterion", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "criterion_order >= 0",
            name="interview_answer_follow_up_criteria_criterion_order_check",
        ),
        sa.ForeignKeyConstraint(
            ["interview_answer_id"],
            ["interview_answer.id"],
            name="fk_interview_answer_follow_up_criteria_answer_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "interview_answer_id",
            "criterion_order",
            name="interview_answer_follow_up_criteria_pkey",
        ),
    )
