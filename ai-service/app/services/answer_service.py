import logging
import re

from langchain_ollama import ChatOllama

from app.models import (
    AnswerEvaluationDraft,
    AnswerEvaluationResponse,
    CriterionAssessment,
    CriterionAssessmentDraft,
)


logger = logging.getLogger(__name__)

llm = ChatOllama(
    model="qwen2.5:3b",
    temperature=0.1
)

structured_llm = llm.with_structured_output(
    AnswerEvaluationDraft,
    method="json_schema"
)


def _normalize_criterion(criterion: str) -> str:
    return " ".join(criterion.split()).casefold()


def _validate_input_criteria(evaluation_criteria: list[str]) -> None:
    if not evaluation_criteria:
        raise ValueError("At least one evaluation criterion is required")

    normalized_criteria = [_normalize_criterion(item) for item in evaluation_criteria]
    if any(not criterion for criterion in normalized_criteria):
        raise ValueError("Evaluation criteria must not be blank")
    if len(set(normalized_criteria)) != len(normalized_criteria):
        raise ValueError("Evaluation criteria must not contain duplicates")


def _find_verbatim_evidence(candidate_answer: str, evidence: str) -> str | None:
    """Return the matching source text, allowing only case and whitespace changes."""
    evidence_words = evidence.split()
    if not evidence_words:
        return None

    pattern = r"\s+".join(re.escape(word) for word in evidence_words)
    match = re.search(pattern, candidate_answer, flags=re.IGNORECASE)
    return match.group(0) if match else None


def validate_criterion_assessments(
    assessments: list[CriterionAssessmentDraft | CriterionAssessment],
    evaluation_criteria: list[str],
    candidate_answer: str
) -> list[CriterionAssessment]:
    """Rebuild source-ordered assessments and verify positive quotes.

    Quote validation confirms that evidence occurs in the answer; whether that
    evidence semantically satisfies a criterion remains an LLM judgment.
    """
    _validate_input_criteria(evaluation_criteria)

    assessments_by_criterion: dict[str, list[CriterionAssessmentDraft | CriterionAssessment]] = {}
    allowed_criteria = {_normalize_criterion(item) for item in evaluation_criteria}

    for assessment in assessments:
        normalized = _normalize_criterion(assessment.criterion)
        if normalized in allowed_criteria:
            assessments_by_criterion.setdefault(normalized, []).append(assessment)

    validated_assessments = []
    for criterion in evaluation_criteria:
        matches = assessments_by_criterion.get(_normalize_criterion(criterion), [])
        if len(matches) != 1:
            validated_assessments.append(
                CriterionAssessment(criterion=criterion, status="MISSING")
            )
            continue

        assessment = matches[0]
        if assessment.status == "MISSING":
            validated_assessments.append(
                CriterionAssessment(criterion=criterion, status="MISSING")
            )
            continue

        source_evidence = _find_verbatim_evidence(
            candidate_answer,
            assessment.evidence
        )
        if source_evidence is None:
            validated_assessments.append(
                CriterionAssessment(criterion=criterion, status="MISSING")
            )
            continue

        validated_assessments.append(
            CriterionAssessment(
                criterion=criterion,
                status=assessment.status,
                evidence=source_evidence
            )
        )

    return validated_assessments


def _completeness_score(assessments: list[CriterionAssessment]) -> float:
    status_scores = {
        "COVERED": 1.0,
        "PARTIALLY_COVERED": 0.5,
        "MISSING": 0.0,
    }
    return round(
        sum(status_scores[item.status] for item in assessments) / len(assessments) * 10,
        2
    )


def _build_strengths(assessments: list[CriterionAssessment]) -> list[str]:
    return [
        assessment.criterion
        for assessment in assessments
        if assessment.status == "COVERED"
    ]


def _build_feedback(assessments: list[CriterionAssessment]) -> str:
    partial = [
        item.criterion
        for item in assessments
        if item.status == "PARTIALLY_COVERED"
    ]
    missing = [
        item.criterion
        for item in assessments
        if item.status == "MISSING"
    ]

    feedback = []
    if partial:
        feedback.append(
            "Expand your explanation of the partially addressed criteria: "
            + "; ".join(partial)
            + "."
        )
    if missing:
        feedback.append(
            "Address the criteria not demonstrated in the answer: "
            + "; ".join(missing)
            + "."
        )
    if not partial and not missing:
        feedback.append(
            "All supplied criteria were addressed; continue supporting each "
            "explanation with clear technical reasoning."
        )
    return " ".join(feedback)


def _safe_fallback(error: Exception) -> AnswerEvaluationResponse:
    logger.error(
        "Answer evaluation failed; returning an explicit safe fallback",
        exc_info=(type(error), error, error.__traceback__)
    )
    # The public status enum has no "unverified" value, so omit assessments
    # rather than presenting evaluation failure as candidate omissions.
    return AnswerEvaluationResponse(
        technicalAccuracy=0,
        completeness=0,
        clarity=0,
        depth=0,
        overallScore=0,
        criterionAssessments=[],
        strengths=[],
        missingConcepts=[],
        feedback=(
            "Automated evaluation could not be completed. Scores and criteria "
            "are unverified; do not interpret this result as an assessment of "
            "the candidate. Please retry the evaluation."
        ),
        suggestedFollowUp=None
    )


def evaluate_answer(
    question: str,
    candidate_answer: str,
    target_role: str,
    difficulty: str,
    evaluation_criteria: list[str]
) -> AnswerEvaluationResponse:
    _validate_input_criteria(evaluation_criteria)
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
actionable feedback and, if useful, a technical follow-up question. Judge only
the supplied criteria.

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
        raw_evaluation = structured_llm.invoke(prompt)
        evaluation = AnswerEvaluationDraft.model_validate(raw_evaluation)
        if not evaluation.criterionAssessments:
            raise ValueError("LLM returned no criterion assessments")
    except Exception as error:
        return _safe_fallback(error)

    validated_assessments = validate_criterion_assessments(
        assessments=evaluation.criterionAssessments,
        evaluation_criteria=evaluation_criteria,
        candidate_answer=candidate_answer
    )
    completeness = _completeness_score(validated_assessments)
    overall_score = round(
        evaluation.technicalAccuracy * 0.40
        + completeness * 0.30
        + evaluation.clarity * 0.15
        + evaluation.depth * 0.15,
        2
    )
    missing_concepts = [
        assessment.criterion
        for assessment in validated_assessments
        if assessment.status == "MISSING"
    ]

    return AnswerEvaluationResponse(
        technicalAccuracy=evaluation.technicalAccuracy,
        completeness=completeness,
        clarity=evaluation.clarity,
        depth=evaluation.depth,
        overallScore=overall_score,
        criterionAssessments=validated_assessments,
        strengths=_build_strengths(validated_assessments),
        missingConcepts=missing_concepts,
        feedback=_build_feedback(validated_assessments),
        suggestedFollowUp=evaluation.suggestedFollowUp
    )
