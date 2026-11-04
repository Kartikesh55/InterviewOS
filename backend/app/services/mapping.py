from app.models.interview import (
    Interview,
    InterviewAnswer,
    InterviewQuestion,
)
from app.schemas.answer import (
    CriterionAssessmentResponse,
    InterviewAnswerResponse,
)
from app.schemas.interview import InterviewResponse
from app.schemas.question import InterviewQuestionResponse


def interview_response(interview: Interview) -> InterviewResponse:
    return InterviewResponse(
        id=interview.id,
        target_role=interview.target_role,
        difficulty=interview.difficulty,
        number_of_questions=interview.number_of_questions,
        status=interview.status,
        created_at=interview.created_at,
    )


def question_response(question: InterviewQuestion) -> InterviewQuestionResponse:
    return InterviewQuestionResponse(
        id=question.id,
        question_text=question.question_text,
        question_order=question.question_order,
        source=question.source,
        evaluation_criteria=[item.criterion for item in question.criteria],
    )


def answer_response(answer: InterviewAnswer) -> InterviewAnswerResponse:
    return InterviewAnswerResponse(
        id=answer.id,
        question_id=answer.interview_question_id,
        candidate_answer=answer.candidate_answer,
        submitted_at=answer.submitted_at,
        evaluation_status=answer.evaluation_status,
        technical_accuracy=answer.technical_accuracy,
        completeness=answer.completeness,
        clarity=answer.clarity,
        depth=answer.depth,
        overall_score=answer.overall_score,
        criterion_assessments=[
            CriterionAssessmentResponse(
                criterion=item.criterion,
                status=item.status,
                evidence=item.evidence,
            )
            for item in answer.assessments
        ],
        strengths=[item.strength for item in answer.strengths],
        missing_concepts=[item.concept for item in answer.missing_concepts],
        feedback=answer.feedback,
        suggested_follow_up=answer.suggested_follow_up,
        suggested_follow_up_criteria=[
            item.criterion for item in answer.follow_up_criteria
        ],
    )
