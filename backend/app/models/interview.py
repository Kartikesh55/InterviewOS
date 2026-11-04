import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Difficulty(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class InterviewStatus(StrEnum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class EvaluationStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QuestionSource(StrEnum):
    GENERATED = "GENERATED"
    FOLLOW_UP = "FOLLOW_UP"


class CriterionStatus(StrEnum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    MISSING = "MISSING"


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, _dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Interview(Base):
    __tablename__ = "interview"
    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name="interview_difficulty_check",
        ),
        CheckConstraint(
            "status IN ('CREATED', 'IN_PROGRESS', 'COMPLETED')",
            name="interview_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    target_role: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty", native_enum=False, length=32),
        nullable=False,
    )
    number_of_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status", native_enum=False, length=32),
        nullable=False,
        default=InterviewStatus.CREATED,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    current_question_order: Mapped[int | None] = mapped_column(Integer)

    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.question_order",
        lazy="selectin",
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_question"
    __table_args__ = (
        UniqueConstraint(
            "interview_id",
            "question_order",
            name="uk_interview_question_order",
        ),
        CheckConstraint(
            "source IN ('GENERATED', 'FOLLOW_UP')",
            name="interview_question_source_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[QuestionSource] = mapped_column(
        Enum(QuestionSource, name="question_source", native_enum=False, length=32),
        nullable=False,
        default=QuestionSource.GENERATED,
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interview: Mapped[Interview] = relationship(back_populates="questions")
    criteria: Mapped[list["QuestionCriterion"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionCriterion.criterion_order",
        lazy="selectin",
    )
    answers: Mapped[list["InterviewAnswer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class QuestionCriterion(Base):
    __tablename__ = "interview_question_criteria"
    __table_args__ = (
        CheckConstraint(
            "criterion_order >= 0",
            name="interview_question_criteria_criterion_order_check",
        ),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        "interview_question_id",
        ForeignKey("interview_question.id", ondelete="CASCADE"),
        primary_key=True,
    )
    criterion_order: Mapped[int] = mapped_column(Integer, primary_key=True)
    criterion: Mapped[str] = mapped_column(Text, nullable=False)

    question: Mapped[InterviewQuestion] = relationship(back_populates="criteria")


class InterviewAnswer(Base):
    __tablename__ = "interview_answer"
    __table_args__ = (
        UniqueConstraint(
            "interview_question_id",
            name="uk_interview_answer_question",
        ),
        CheckConstraint(
            "evaluation_status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name="interview_answer_evaluation_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_answer: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    evaluation_status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, name="evaluation_status", native_enum=False, length=32),
        nullable=False,
        default=EvaluationStatus.PENDING,
    )
    technical_accuracy: Mapped[float | None] = mapped_column(Float)
    completeness: Mapped[float | None] = mapped_column(Float)
    clarity: Mapped[float | None] = mapped_column(Float)
    depth: Mapped[float | None] = mapped_column(Float)
    overall_score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)
    suggested_follow_up: Mapped[str | None] = mapped_column(Text)
    interview_question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_question.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question: Mapped[InterviewQuestion] = relationship(back_populates="answers")
    assessments: Mapped[list["CriterionAssessment"]] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        order_by="CriterionAssessment.assessment_order",
        lazy="selectin",
    )
    strengths: Mapped[list["AnswerStrength"]] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        order_by="AnswerStrength.strength_order",
        lazy="selectin",
    )
    missing_concepts: Mapped[list["AnswerMissingConcept"]] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        order_by="AnswerMissingConcept.concept_order",
        lazy="selectin",
    )
    follow_up_criteria: Mapped[list["AnswerFollowUpCriterion"]] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        order_by="AnswerFollowUpCriterion.criterion_order",
        lazy="selectin",
    )


class CriterionAssessment(Base):
    __tablename__ = "criterion_assessment"
    __table_args__ = (
        CheckConstraint(
            "status IN ('COVERED', 'PARTIALLY_COVERED', 'MISSING')",
            name="criterion_assessment_status_check",
        ),
        CheckConstraint(
            "assessment_order >= 0",
            name="criterion_assessment_assessment_order_check",
        ),
        UniqueConstraint(
            "interview_answer_id",
            "assessment_order",
            name="uk_criterion_assessment_answer_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    criterion: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CriterionStatus] = mapped_column(
        Enum(CriterionStatus, name="criterion_status", native_enum=False, length=32),
        nullable=False,
    )
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assessment_order: Mapped[int] = mapped_column(Integer, nullable=False)
    interview_answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_answer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    answer: Mapped[InterviewAnswer] = relationship(back_populates="assessments")


class AnswerStrength(Base):
    __tablename__ = "interview_answer_strengths"
    __table_args__ = (
        CheckConstraint(
            "strength_order >= 0",
            name="interview_answer_strengths_strength_order_check",
        ),
    )

    answer_id: Mapped[uuid.UUID] = mapped_column(
        "interview_answer_id",
        ForeignKey("interview_answer.id", ondelete="CASCADE"),
        primary_key=True,
    )
    strength_order: Mapped[int] = mapped_column(Integer, primary_key=True)
    strength: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[InterviewAnswer] = relationship(back_populates="strengths")


class AnswerMissingConcept(Base):
    __tablename__ = "interview_answer_missing_concepts"
    __table_args__ = (
        CheckConstraint(
            "concept_order >= 0",
            name="interview_answer_missing_concepts_concept_order_check",
        ),
    )

    answer_id: Mapped[uuid.UUID] = mapped_column(
        "interview_answer_id",
        ForeignKey("interview_answer.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_order: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[InterviewAnswer] = relationship(back_populates="missing_concepts")


class AnswerFollowUpCriterion(Base):
    __tablename__ = "interview_answer_follow_up_criteria"
    __table_args__ = (
        CheckConstraint(
            "criterion_order >= 0",
            name="interview_answer_follow_up_criteria_criterion_order_check",
        ),
    )

    answer_id: Mapped[uuid.UUID] = mapped_column(
        "interview_answer_id",
        ForeignKey("interview_answer.id", ondelete="CASCADE"),
        primary_key=True,
    )
    criterion_order: Mapped[int] = mapped_column(Integer, primary_key=True)
    criterion: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[InterviewAnswer] = relationship(back_populates="follow_up_criteria")
