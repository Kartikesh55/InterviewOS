package com.interviewos.backend.dto;

import java.util.UUID;
import java.util.List;

import com.interviewos.backend.entity.InterviewQuestion;
import com.interviewos.backend.entity.QuestionSource;

public record InterviewQuestionResponse(
    UUID id,
    String questionText,
    Integer questionOrder,
    QuestionSource source,
    List<String> evaluationCriteria
) {
    public InterviewQuestionResponse(UUID id, String questionText, Integer questionOrder) {
        this(id, questionText, questionOrder, QuestionSource.GENERATED, List.of());
    }

    public static InterviewQuestionResponse from(InterviewQuestion question) {
        return new InterviewQuestionResponse(
            question.getId(),
            question.getQuestionText(),
            question.getQuestionOrder(),
            question.getSource(),
            question.getEvaluationCriteria()
        );
    }
}
