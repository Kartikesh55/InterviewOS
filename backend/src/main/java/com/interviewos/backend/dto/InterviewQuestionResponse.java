package com.interviewos.backend.dto;

import java.util.UUID;

import com.interviewos.backend.entity.InterviewQuestion;

public record InterviewQuestionResponse(
    UUID id,
    String questionText,
    Integer questionOrder
) {
    public static InterviewQuestionResponse from(InterviewQuestion question) {
        return new InterviewQuestionResponse(
            question.getId(),
            question.getQuestionText(),
            question.getQuestionOrder()
        );
    }
}
