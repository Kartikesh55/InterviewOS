package com.interviewos.backend.integration.ai;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record QuestionGenerationRequest(
    @NotBlank String targetRole,
    @NotBlank String difficulty,
    @NotNull @Min(1) @Max(20) Integer numberOfQuestions
) {
}
