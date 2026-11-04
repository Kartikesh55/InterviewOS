package com.interviewos.backend.integration.ai;

public record CriterionAssessmentResponse(
    String criterion,
    String status,
    String evidence
) {
}
