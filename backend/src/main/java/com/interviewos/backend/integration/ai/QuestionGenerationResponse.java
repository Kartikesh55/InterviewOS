package com.interviewos.backend.integration.ai;

import java.util.List;

public record QuestionGenerationResponse(List<GeneratedQuestion> questions) {
}
