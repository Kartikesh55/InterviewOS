package com.interviewos.backend.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.InterviewStatus;

public record InterviewDetailsResponse(
    UUID id,
    String targetRole,
    Difficulty difficulty,
    Integer numberOfQuestions,
    InterviewStatus status,
    LocalDateTime createdAt,
    Integer currentQuestionOrder,
    List<InterviewQuestionResponse> questions
) {
    public static InterviewDetailsResponse from(
        Interview interview,
        List<InterviewQuestionResponse> questions
    ) {
        return new InterviewDetailsResponse(
            interview.getId(),
            interview.getTargetRole(),
            interview.getDifficulty(),
            interview.getNumberOfQuestions(),
            interview.getStatus(),
            interview.getCreatedAt(),
            interview.getCurrentQuestionOrder(),
            questions
        );
    }
}
