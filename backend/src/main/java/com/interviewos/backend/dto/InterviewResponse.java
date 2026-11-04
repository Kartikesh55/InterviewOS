package com.interviewos.backend.dto;

import java.time.LocalDateTime;
import java.util.UUID;

import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.InterviewStatus;

public record InterviewResponse(
    UUID id,
    String targetRole,
    Difficulty difficulty,
    Integer numberOfQuestions,
    InterviewStatus status,
    LocalDateTime createdAt
) {
    public static InterviewResponse from(Interview interview) {
        return new InterviewResponse(
            interview.getId(),
            interview.getTargetRole(),
            interview.getDifficulty(),
            interview.getNumberOfQuestions(),
            interview.getStatus(),
            interview.getCreatedAt()
        );
    }
}
