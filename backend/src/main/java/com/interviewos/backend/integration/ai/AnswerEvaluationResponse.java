package com.interviewos.backend.integration.ai;

import java.util.List;

public record AnswerEvaluationResponse(
    double technicalAccuracy,
    double completeness,
    double clarity,
    double depth,
    double overallScore,
    List<CriterionAssessmentResponse> criterionAssessments,
    List<String> strengths,
    List<String> missingConcepts,
    String feedback,
    String suggestedFollowUp
) {
}
