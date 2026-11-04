import logging
import math
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.graphs.evaluation_graph import evaluation_graph
from app.ai.services.answer_service import (
    build_feedback,
    build_strengths,
    calculate_completeness,
    normalize_criterion,
    sanitize_follow_up,
    validate_criterion_assessments,
)
from app.core.exceptions import (
    InvalidEvaluation,
    LifecycleConflict,
    ResourceNotFound,
)
from app.models.interview import (
    AnswerFollowUpCriterion,
    AnswerMissingConcept,
    AnswerStrength,
    CriterionAssessment,
    CriterionStatus,
    EvaluationStatus,
    InterviewAnswer,
    InterviewStatus,
    QuestionCriterion,
    QuestionSource,
)
from app.repositories import (
    answer_repository,
    interview_repository,
    question_repository,
)
from app.schemas.answer import InterviewAnswerResponse
from app.schemas.evaluation import AnswerEvaluationResponse
from app.schemas.interview import InterviewReportResponse, InterviewQuestionReportResponse
from app.schemas.question import InterviewQuestionResponse
from app.services.mapping import answer_response, interview_response, question_response


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingSubmission:
    answer_id: UUID
    question_text: str
    candidate_answer: str
    target_role: str
    difficulty: str
    criteria: list[str]


def submit_answer(
    session: Session,
    interview_id: UUID,
    question_id: UUID,
    candidate_answer: str,
) -> InterviewAnswerResponse:
    if not candidate_answer.strip():
        raise ValueError("candidateAnswer must not be blank")

    with session.begin():
        interview = interview_repository.get_interview(
            session,
            interview_id,
            for_update=True,
        )
        if interview is None:
            raise ResourceNotFound(f"Interview not found: {interview_id}")
        if interview.status != InterviewStatus.IN_PROGRESS:
            raise LifecycleConflict(
                "Answers can only be submitted while the interview is IN_PROGRESS"
            )
        question = question_repository.get_question(
            session,
            interview_id,
            question_id,
            for_update=True,
        )
        if question is None:
            raise ResourceNotFound(f"Question not found for interview: {question_id}")
        if question.question_order != interview.current_question_order:
            raise LifecycleConflict(
                "Answers can only be submitted for the current question"
            )
        if answer_repository.get_answer_for_question(session, question_id) is not None:
            raise LifecycleConflict(
                "An answer has already been submitted for this question"
            )
        criteria = [item.criterion for item in question.criteria]
        if not criteria:
            raise LifecycleConflict("The current question has no evaluation criteria")

        answer = InterviewAnswer(
            candidate_answer=candidate_answer,
            question=question,
            evaluation_status=EvaluationStatus.PENDING,
        )
        session.add(answer)
        session.flush()
        pending = PendingSubmission(
            answer_id=answer.id,
            question_text=question.question_text,
            candidate_answer=answer.candidate_answer,
            target_role=interview.target_role,
            difficulty=interview.difficulty.value,
            criteria=criteria,
        )

    try:
        graph_result = evaluation_graph.invoke(
            {
                "question": pending.question_text,
                "candidate_answer": pending.candidate_answer,
                "target_role": pending.target_role,
                "difficulty": pending.difficulty,
                "evaluation_criteria": pending.criteria,
                "evaluation": None,
            }
        )
        raw_evaluation = AnswerEvaluationResponse.model_validate(
            graph_result["evaluation"]
        )
        evaluation = validate_evaluation(
            raw_evaluation,
            pending.criteria,
            pending.candidate_answer,
        )
        if evaluation.evaluationStatus != "COMPLETED":
            return _mark_failed(session, pending.answer_id)
    except Exception:
        logger.exception("Answer evaluation failed for persisted answer %s", pending.answer_id)
        return _mark_failed(session, pending.answer_id)

    with session.begin():
        interview = interview_repository.get_interview(
            session,
            interview_id,
            for_update=True,
        )
        answer = answer_repository.get_answer_for_question(
            session,
            question_id,
            for_update=True,
        )
        if interview is None or answer is None:
            raise RuntimeError("Persisted interview or answer disappeared during evaluation")
        _persist_evaluation(answer, evaluation)

        if _should_use_follow_up(session, interview, answer, evaluation):
            next_question = question_repository.get_question_at_order(
                session,
                interview_id,
                answer.question.question_order + 1,
                for_update=True,
            )
            if next_question is not None:
                _replace_with_follow_up(session, next_question, evaluation)
        session.flush()
        return answer_response(answer)


def validate_evaluation(
    evaluation: AnswerEvaluationResponse,
    original_criteria: list[str],
    candidate_answer: str,
) -> AnswerEvaluationResponse:
    if evaluation.evaluationStatus != "COMPLETED":
        return evaluation
    dimensions = (
        evaluation.technicalAccuracy,
        evaluation.clarity,
        evaluation.depth,
    )
    if not evaluation.criterionAssessments or any(
        score is None or not math.isfinite(score) or score < 0 or score > 10
        for score in dimensions
    ):
        raise InvalidEvaluation("AI evaluation was incomplete or contained invalid scores")
    if not evaluation.feedback.strip():
        raise InvalidEvaluation("AI evaluation did not include feedback")

    assessments = validate_criterion_assessments(
        evaluation.criterionAssessments,
        original_criteria,
        candidate_answer,
    )
    completeness = calculate_completeness(assessments)
    overall_score = round(
        evaluation.technicalAccuracy * 0.40
        + completeness * 0.30
        + evaluation.clarity * 0.15
        + evaluation.depth * 0.15,
        2,
    )
    suggested_follow_up, follow_up_criteria = sanitize_follow_up(
        evaluation.suggestedFollowUp,
        evaluation.suggestedFollowUpCriteria,
    )
    return evaluation.model_copy(
        update={
            "completeness": completeness,
            "overallScore": overall_score,
            "criterionAssessments": assessments,
            "strengths": build_strengths(assessments),
            "missingConcepts": [
                item.criterion for item in assessments if item.status == "MISSING"
            ],
            "feedback": build_feedback(assessments),
            "suggestedFollowUp": suggested_follow_up,
            "suggestedFollowUpCriteria": follow_up_criteria,
        }
    )


def _persist_evaluation(
    answer: InterviewAnswer,
    evaluation: AnswerEvaluationResponse,
) -> None:
    criteria = [item.criterion for item in answer.question.criteria]
    normalized_criteria = [normalize_criterion(item) for item in criteria]
    if (
        len(evaluation.criterionAssessments) != len(criteria)
        or [
            normalize_criterion(item.criterion)
            for item in evaluation.criterionAssessments
        ]
        != normalized_criteria
    ):
        raise InvalidEvaluation("AI evaluation criteria do not match stored criteria")

    completeness = calculate_completeness(evaluation.criterionAssessments)
    overall_score = round(
        evaluation.technicalAccuracy * 0.40
        + completeness * 0.30
        + evaluation.clarity * 0.15
        + evaluation.depth * 0.15,
        2,
    )
    answer.evaluation_status = EvaluationStatus.COMPLETED
    answer.technical_accuracy = evaluation.technicalAccuracy
    answer.completeness = completeness
    answer.clarity = evaluation.clarity
    answer.depth = evaluation.depth
    answer.overall_score = overall_score
    answer.feedback = build_feedback(evaluation.criterionAssessments)
    answer.suggested_follow_up = evaluation.suggestedFollowUp
    answer.assessments = [
        CriterionAssessment(
            criterion=item.criterion,
            status=CriterionStatus(item.status),
            evidence=item.evidence,
            assessment_order=index,
        )
        for index, item in enumerate(evaluation.criterionAssessments)
    ]
    answer.strengths = [
        AnswerStrength(strength_order=index, strength=strength)
        for index, strength in enumerate(build_strengths(evaluation.criterionAssessments))
    ]
    answer.missing_concepts = [
        AnswerMissingConcept(concept_order=index, concept=item.criterion)
        for index, item in enumerate(evaluation.criterionAssessments)
        if item.status == CriterionStatus.MISSING
    ]
    follow_up_criteria = evaluation.suggestedFollowUpCriteria
    answer.follow_up_criteria = [
        AnswerFollowUpCriterion(criterion_order=index, criterion=criterion)
        for index, criterion in enumerate(follow_up_criteria)
    ]


def _should_use_follow_up(
    session: Session,
    interview,
    answer: InterviewAnswer,
    evaluation: AnswerEvaluationResponse,
) -> bool:
    question = answer.question
    if (
        interview.status != InterviewStatus.IN_PROGRESS
        or interview.current_question_order != question.question_order
        or question.question_order + 1 > interview.number_of_questions
        or question.question_order >= interview.number_of_questions
        or not evaluation.suggestedFollowUp
        or not evaluation.suggestedFollowUp.strip()
    ):
        return False
    criteria = evaluation.suggestedFollowUpCriteria
    normalized = [normalize_criterion(item) for item in criteria]
    if not criteria or any(not item for item in normalized):
        return False
    if len(set(normalized)) != len(normalized):
        return False
    needs_follow_up = (
        evaluation.overallScore is not None and evaluation.overallScore < 7.0
    )
    needs_follow_up = needs_follow_up or any(
        item.status in {"MISSING", "PARTIALLY_COVERED"}
        for item in evaluation.criterionAssessments
    )
    if not needs_follow_up:
        return False
    return (
        question_repository.get_question_at_order(
            session,
            interview.id,
            question.question_order + 1,
        )
        is not None
    )


def _replace_with_follow_up(
    session: Session,
    question,
    evaluation: AnswerEvaluationResponse,
) -> None:
    question.question_text = evaluation.suggestedFollowUp.strip()
    question.source = QuestionSource.FOLLOW_UP
    question.criteria.clear()
    session.flush()
    question.criteria.extend([
        QuestionCriterion(criterion_order=index, criterion=criterion.strip())
        for index, criterion in enumerate(evaluation.suggestedFollowUpCriteria)
    ])


def _mark_failed(session: Session, answer_id: UUID) -> InterviewAnswerResponse:
    with session.begin():
        answer = session.scalar(
            select(InterviewAnswer)
            .where(InterviewAnswer.id == answer_id)
            .with_for_update()
        )
        if answer is None:
            raise ResourceNotFound(f"Answer not found: {answer_id}")
        if answer.evaluation_status == EvaluationStatus.PENDING:
            answer.evaluation_status = EvaluationStatus.FAILED
        session.flush()
        return answer_response(answer)


def get_interview_report(
    session: Session,
    interview_id: UUID,
) -> InterviewReportResponse:
    interview = interview_repository.get_interview(
        session,
        interview_id,
        with_questions=True,
    )
    if interview is None:
        raise ResourceNotFound(f"Interview not found: {interview_id}")
    questions = []
    for question in interview.questions:
        answers = answer_repository.list_answers_for_question(session, question.id)
        questions.append(
            InterviewQuestionReportResponse(
                **question_response(question).model_dump(),
                answers=[answer_response(answer) for answer in answers],
            )
        )
    details = InterviewReportResponse(
        **interview_response(interview).model_dump(),
        current_question_order=interview.current_question_order,
        questions=questions,
    )
    return details
