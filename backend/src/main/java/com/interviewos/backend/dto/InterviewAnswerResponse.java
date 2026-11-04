package com.interviewos.backend.dto;

import java.time.LocalDateTime;
import java.util.UUID;

import com.interviewos.backend.entity.InterviewAnswer;

public record InterviewAnswerResponse(
    UUID id,
    UUID questionId,
    String candidateAnswer,
    LocalDateTime submittedAt
) {
    public static InterviewAnswerResponse from(InterviewAnswer answer) {
        return new InterviewAnswerResponse(
            answer.getId(),
            answer.getInterviewQuestion().getId(),
            answer.getCandidateAnswer(),
            answer.getSubmittedAt()
        );
    }
}
