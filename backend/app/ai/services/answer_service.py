import logging
import re
from typing import TypeAlias

from app.ai.llm import get_chat_model
from app.schemas.evaluation import (
    AnswerEvaluationDraft,
    AnswerEvaluationResponse,
    CriterionAssessment,
    CriterionAssessmentDraft,
)


logger = logging.getLogger(__name__)
Assessment: TypeAlias = CriterionAssessment | CriterionAssessmentDraft


def normalize_criterion(criterion: str) -> str:
    return " ".join(criterion.split()).casefold()


def validate_input_criteria(evaluation_criteria: list[str]) -> None:
    if not evaluation_criteria:
        raise ValueError("At least one evaluation criterion is required")
    normalized = [normalize_criterion(item) for item in evaluation_criteria]
    if any(not criterion for criterion in normalized):
        raise ValueError("Evaluation criteria must not be blank")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Evaluation criteria must not contain duplicates")


def find_verbatim_evidence(candidate_answer: str, evidence: str) -> str | None:
    words = evidence.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    match = re.search(pattern, candidate_answer, flags=re.IGNORECASE)
    return match.group(0) if match else None


def validate_criterion_assessments(
    assessments: list[Assessment],
    evaluation_criteria: list[str],
    candidate_answer: str,
) -> list[CriterionAssessment]:
    """Validate quote existence; semantic support remains an LLM judgment."""
    validate_input_criteria(evaluation_criteria)
    allowed = {normalize_criterion(item) for item in evaluation_criteria}
    by_criterion: dict[str, list[Assessment]] = {}
    for assessment in assessments:
        normalized = normalize_criterion(assessment.criterion)
        if normalized in allowed:
            by_criterion.setdefault(normalized, []).append(assessment)

    validated = []
    for criterion in evaluation_criteria:
        matches = by_criterion.get(normalize_criterion(criterion), [])
        if len(matches) != 1 or matches[0].status == "MISSING":
            validated.append(CriterionAssessment(criterion=criterion, status="MISSING"))
            continue
        evidence = find_verbatim_evidence(candidate_answer, matches[0].evidence)
        if evidence is None:
            validated.append(CriterionAssessment(criterion=criterion, status="MISSING"))
            continue
        validated.append(
            CriterionAssessment(
                criterion=criterion,
                status=matches[0].status,
                evidence=evidence,
            )
        )
    return validated


def calculate_completeness(assessments: list[CriterionAssessment]) -> float:
    if not assessments:
        raise ValueError("Cannot calculate completeness without criterion assessments")
    points = {"COVERED": 1.0, "PARTIALLY_COVERED": 0.5, "MISSING": 0.0}
    return round(sum(points[item.status] for item in assessments) / len(assessments) * 10, 2)


def build_strengths(assessments: list[CriterionAssessment]) -> list[str]:
    return [item.criterion for item in assessments if item.status == "COVERED"]


def build_feedback(assessments: list[CriterionAssessment]) -> str:
    partial = [item.criterion for item in assessments if item.status == "PARTIALLY_COVERED"]
    missing = [item.criterion for item in assessments if item.status == "MISSING"]
    messages = []
    if partial:
        messages.append(
            "Expand your explanation of the partially addressed criteria: "
            + "; ".join(partial)
            + "."
        )
    if missing:
        messages.append(
            "Address the criteria not demonstrated in the answer: "
            + "; ".join(missing)
            + "."
        )
    if not messages:
        messages.append(
            "All supplied criteria were addressed; continue supporting each "
            "explanation with clear technical reasoning."
        )
    return " ".join(messages)


def sanitize_follow_up(
    question: str | None,
    criteria: list[str] | None,
) -> tuple[str | None, list[str]]:
    if not question or not question.strip() or not criteria:
        return None, []
    cleaned = [" ".join(item.split()) if item else "" for item in criteria]
    normalized = [normalize_criterion(item) for item in cleaned]
    if any(not item for item in normalized) or len(set(normalized)) != len(normalized):
        return None, []
    return question.strip(), cleaned


def safe_fallback(error: Exception) -> AnswerEvaluationResponse:
    logger.error(
        "Answer evaluation failed; returning an explicit safe fallback",
        exc_info=(type(error), error, error.__traceback__),
    )
    return AnswerEvaluationResponse(
        evaluationStatus="FAILED",
        feedback=(
            "Automated evaluation could not be completed. Scores and criteria "
            "are unverified; do not interpret this result as an assessment of "
            "the candidate. Please retry the evaluation."
        ),
    )


def evaluate_answer(
    question: str,
    candidate_answer: str,
    target_role: str,
    difficulty: str,
    evaluation_criteria: list[str],
) -> AnswerEvaluationResponse:
    validate_input_criteria(evaluation_criteria)
    if not candidate_answer.strip():
        raise ValueError("Candidate answer must not be blank")

    prompt = f"""
You are an experienced and fair technical interviewer.

Evaluate the candidate's technical accuracy, clarity, and depth on a 0-10 scale.
For each supplied evaluation criterion, return exactly one assessment with:
- criterion: the original criterion, unchanged
- status: COVERED, PARTIALLY_COVERED, or MISSING
- evidence: a direct quote copied from the candidate's answer for positive
  assessments; use an empty string when the criterion is MISSING
- rationale: a concise explanation of why the answer demonstrates, partially
  addresses, or does not meaningfully address the criterion

Separately, return suggestedFollowUpCriteria: specific, non-empty criteria for
evaluating the suggested follow-up question; return an empty list if no
follow-up is given.

Use these status definitions:
- COVERED: the candidate demonstrates the concept with a sufficiently correct
  explanation.
- PARTIALLY_COVERED: the candidate mentions or explains only part of the
  concept, or gives an incomplete explanation.
- MISSING: the candidate does not meaningfully address the concept.

Do not treat keyword mentions or verbatim phrases alone as proof of coverage.
The rationale must explain the actual substance of the answer, not merely
repeat the evidence quote. Do not return strengths, completeness, overall
scores, missing concepts, or criteria that were not supplied. Provide
actionable feedback and, if useful, a technical follow-up question. Any
suggested follow-up and its criteria must be directly related: each criterion
must describe an assessable part of the suggested follow-up question. Do not
provide criteria for the original question as follow-up criteria. Judge only
the supplied evaluation criteria for the candidate's current answer.

Target role: {target_role}
Difficulty: {difficulty}

QUESTION:
{question}

CANDIDATE ANSWER:
{candidate_answer}

SUPPLIED EVALUATION CRITERIA:
{chr(10).join(f"- {criterion}" for criterion in evaluation_criteria)}

Return only the structured response matching the required schema.
"""
    try:
        structured_llm = get_chat_model().with_structured_output(
            AnswerEvaluationDraft,
            method="json_schema",
        )
        evaluation = AnswerEvaluationDraft.model_validate(
            structured_llm.invoke(prompt)
        )
        if not evaluation.criterionAssessments:
            raise ValueError("LLM returned no criterion assessments")
    except Exception as error:
        return safe_fallback(error)

    assessments = validate_criterion_assessments(
        evaluation.criterionAssessments,
        evaluation_criteria,
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
    suggested_follow_up, suggested_follow_up_criteria = sanitize_follow_up(
        evaluation.suggestedFollowUp,
        evaluation.suggestedFollowUpCriteria,
    )
    return AnswerEvaluationResponse(
        evaluationStatus="COMPLETED",
        technicalAccuracy=evaluation.technicalAccuracy,
        completeness=completeness,
        clarity=evaluation.clarity,
        depth=evaluation.depth,
        overallScore=overall_score,
        criterionAssessments=assessments,
        strengths=build_strengths(assessments),
        missingConcepts=[
            item.criterion for item in assessments if item.status == "MISSING"
        ],
        feedback=build_feedback(assessments),
        suggestedFollowUp=suggested_follow_up,
        suggestedFollowUpCriteria=suggested_follow_up_criteria,
    )
