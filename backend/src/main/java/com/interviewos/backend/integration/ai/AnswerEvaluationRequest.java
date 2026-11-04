package com.interviewos.backend.integration.ai;

import java.util.List;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;

public record AnswerEvaluationRequest(
    @NotBlank String question,
    @NotBlank String candidateAnswer,
    @NotBlank String targetRole,
    @NotBlank String difficulty,
    @NotEmpty List<@NotBlank String> evaluationCriteria
) {
}
