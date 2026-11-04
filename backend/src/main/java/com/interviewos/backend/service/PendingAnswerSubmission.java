package com.interviewos.backend.service;

import java.util.List;
import java.util.UUID;

public record PendingAnswerSubmission(
    UUID answerId,
    String questionText,
    String candidateAnswer,
    String targetRole,
    String difficulty,
    List<String> evaluationCriteria
) {
}
