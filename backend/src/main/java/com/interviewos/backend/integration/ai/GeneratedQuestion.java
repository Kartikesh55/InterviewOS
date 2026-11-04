package com.interviewos.backend.integration.ai;

import java.util.List;

public record GeneratedQuestion(
    String questionText,
    List<String> evaluationCriteria
) {
}
