package com.interviewos.backend.integration.ai;

import java.util.List;

import com.interviewos.backend.entity.EvaluationStatus;

public record AnswerEvaluationResponse(
    EvaluationStatus evaluationStatus,
    double technicalAccuracy,
    double completeness,
    double clarity,
    double depth,
    double overallScore,
    List<CriterionAssessmentResponse> criterionAssessments,
    List<String> strengths,
    List<String> missingConcepts,
    String feedback,
    String suggestedFollowUp,
    List<String> suggestedFollowUpCriteria
) {
    public AnswerEvaluationResponse(
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
        this(
            EvaluationStatus.COMPLETED,
            technicalAccuracy,
            completeness,
            clarity,
            depth,
            overallScore,
            criterionAssessments,
            strengths,
            missingConcepts,
            feedback,
            suggestedFollowUp,
            List.of()
        );
    }
}
