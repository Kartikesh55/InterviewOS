package com.interviewos.backend.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import com.interviewos.backend.entity.CriterionAssessment;
import com.interviewos.backend.entity.EvaluationStatus;
import com.interviewos.backend.entity.InterviewAnswer;
import com.interviewos.backend.integration.ai.CriterionAssessmentResponse;

public record InterviewAnswerResponse(
    UUID id,
    UUID questionId,
    String candidateAnswer,
    LocalDateTime submittedAt,
    EvaluationStatus evaluationStatus,
    Double technicalAccuracy,
    Double completeness,
    Double clarity,
    Double depth,
    Double overallScore,
    List<CriterionAssessmentResponse> criterionAssessments,
    List<String> strengths,
    List<String> missingConcepts,
    String feedback,
    String suggestedFollowUp,
    List<String> suggestedFollowUpCriteria
) {
    public InterviewAnswerResponse(
        UUID id,
        UUID questionId,
        String candidateAnswer,
        LocalDateTime submittedAt
    ) {
        this(
            id, questionId, candidateAnswer, submittedAt, EvaluationStatus.PENDING,
            null, null, null, null, null, List.of(), List.of(), List.of(),
            null, null, List.of()
        );
    }

    public static InterviewAnswerResponse from(InterviewAnswer answer) {
        return new InterviewAnswerResponse(
            answer.getId(),
            answer.getInterviewQuestion().getId(),
            answer.getCandidateAnswer(),
            answer.getSubmittedAt(),
            answer.getEvaluationStatus(),
            answer.getTechnicalAccuracy(),
            answer.getCompleteness(),
            answer.getClarity(),
            answer.getDepth(),
            answer.getOverallScore(),
            answer.getCriterionAssessments().stream()
                .map(InterviewAnswerResponse::toResponse)
                .toList(),
            answer.getStrengths(),
            answer.getMissingConcepts(),
            answer.getFeedback(),
            answer.getSuggestedFollowUp(),
            answer.getSuggestedFollowUpCriteria()
        );
    }

    private static CriterionAssessmentResponse toResponse(CriterionAssessment assessment) {
        return new CriterionAssessmentResponse(
            assessment.getCriterion(),
            assessment.getStatus(),
            assessment.getEvidence()
        );
    }
}
