package com.interviewos.backend.dto;

import jakarta.validation.constraints.NotBlank;

public record SubmitAnswerRequest(@NotBlank String candidateAnswer) {
}
