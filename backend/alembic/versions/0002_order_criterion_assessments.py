"""Persist deterministic source order for criterion assessments.

Revision ID: 0002_order_criterion_assessments
Revises: 0001_python_backend_schema
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0002_order_criterion_assessments"
down_revision = "0001_python_backend_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {
        item["name"] for item in inspect(bind).get_columns("criterion_assessment")
    }
    if "assessment_order" not in columns:
        op.add_column(
            "criterion_assessment",
            sa.Column("assessment_order", sa.Integer(), nullable=True),
        )
        op.execute(
            """
            WITH ranked AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY interview_answer_id
                           ORDER BY criterion, id
                       ) - 1 AS position
                FROM criterion_assessment
            )
            UPDATE criterion_assessment AS assessment
            SET assessment_order = ranked.position
            FROM ranked
            WHERE assessment.id = ranked.id
            """
        )
        op.alter_column(
            "criterion_assessment",
            "assessment_order",
            existing_type=sa.Integer(),
            nullable=False,
        )
    checks = {
        item["name"]
        for item in inspect(bind).get_check_constraints("criterion_assessment")
    }
    if "criterion_assessment_assessment_order_check" not in checks:
        op.create_check_constraint(
            "criterion_assessment_assessment_order_check",
            "criterion_assessment",
            "assessment_order >= 0",
        )
    unique_constraints = {
        item["name"]
        for item in inspect(bind).get_unique_constraints("criterion_assessment")
    }
    if "uk_criterion_assessment_answer_order" not in unique_constraints:
        op.create_unique_constraint(
            "uk_criterion_assessment_answer_order",
            "criterion_assessment",
            ["interview_answer_id", "assessment_order"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    checks = {
        item["name"]
        for item in inspect(bind).get_check_constraints("criterion_assessment")
    }
    if "criterion_assessment_assessment_order_check" in checks:
        op.drop_constraint(
            "criterion_assessment_assessment_order_check",
            "criterion_assessment",
            type_="check",
        )
    unique_constraints = {
        item["name"]
        for item in inspect(bind).get_unique_constraints("criterion_assessment")
    }
    if "uk_criterion_assessment_answer_order" in unique_constraints:
        op.drop_constraint(
            "uk_criterion_assessment_answer_order",
            "criterion_assessment",
            type_="unique",
        )
    columns = {
        item["name"] for item in inspect(bind).get_columns("criterion_assessment")
    }
    if "assessment_order" in columns:
        op.drop_column("criterion_assessment", "assessment_order")
