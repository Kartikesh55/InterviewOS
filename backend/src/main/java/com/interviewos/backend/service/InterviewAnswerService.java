package com.interviewos.backend.service;

import java.util.List;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.entity.EvaluationStatus;
import com.interviewos.backend.integration.ai.AiServiceClient;
import com.interviewos.backend.integration.ai.AnswerEvaluationRequest;
import com.interviewos.backend.integration.ai.AnswerEvaluationResponse;
import com.interviewos.backend.integration.ai.AiServiceException;

@Service
public class InterviewAnswerService {
    private static final Logger logger = LoggerFactory.getLogger(InterviewAnswerService.class);

    private final InterviewAnswerPersistenceService answerPersistenceService;
    private final InterviewEvaluationPersistenceService evaluationPersistenceService;
    private final AiServiceClient aiServiceClient;

    public InterviewAnswerService(
        InterviewAnswerPersistenceService answerPersistenceService,
        InterviewEvaluationPersistenceService evaluationPersistenceService,
        AiServiceClient aiServiceClient
    ) {
        this.answerPersistenceService = answerPersistenceService;
        this.evaluationPersistenceService = evaluationPersistenceService;
        this.aiServiceClient = aiServiceClient;
    }

    public InterviewAnswerResponse submitAnswer(
        UUID interviewId,
        UUID questionId,
        String candidateAnswer
    ) {
        PendingAnswerSubmission pending = answerPersistenceService.persistPendingAnswer(
            interviewId,
            questionId,
            candidateAnswer
        );

        AnswerEvaluationResponse evaluation;
        try {
            evaluation = aiServiceClient.evaluateAnswer(
                new AnswerEvaluationRequest(
                    pending.questionText(),
                    pending.candidateAnswer(),
                    pending.targetRole(),
                    pending.difficulty(),
                    pending.evaluationCriteria()
                )
            );
        } catch (AiServiceException exception) {
            logger.warn("Evaluation failed for persisted answer {}", pending.answerId(), exception);
            return answerPersistenceService.markFailed(pending.answerId());
        }

        if (!isValidCompletedEvaluation(evaluation)) {
            logger.warn("AI service returned an unsuccessful or incomplete evaluation for answer {}",
                pending.answerId());
            return answerPersistenceService.markFailed(pending.answerId());
        }
        return evaluationPersistenceService.persistEvaluation(pending.answerId(), evaluation);
    }

    private boolean isValidCompletedEvaluation(AnswerEvaluationResponse evaluation) {
        return evaluation != null
            && evaluation.evaluationStatus() == EvaluationStatus.COMPLETED
            && inScoreRange(evaluation.technicalAccuracy())
            && inScoreRange(evaluation.completeness())
            && inScoreRange(evaluation.clarity())
            && inScoreRange(evaluation.depth())
            && inScoreRange(evaluation.overallScore())
            && evaluation.criterionAssessments() != null
            && evaluation.criterionAssessments().stream().allMatch(item ->
                item != null
                    && item.criterion() != null
                    && !item.criterion().isBlank()
                    && item.status() != null
                    && item.evidence() != null
            )
            && evaluation.strengths() != null
            && evaluation.missingConcepts() != null
            && evaluation.feedback() != null
            && evaluation.suggestedFollowUpCriteria() != null
            && validCriteria(evaluation.suggestedFollowUpCriteria());
    }

    private boolean inScoreRange(double score) {
        return Double.isFinite(score) && score >= 0 && score <= 10;
    }

    private boolean validCriteria(List<String> criteria) {
        return criteria.stream().allMatch(item -> item != null && !item.isBlank());
    }
}
