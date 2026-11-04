package com.interviewos.backend.service;

import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.entity.CriterionAssessment;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.InterviewAnswer;
import com.interviewos.backend.entity.InterviewQuestion;
import com.interviewos.backend.entity.InterviewStatus;
import com.interviewos.backend.integration.ai.AnswerEvaluationResponse;
import com.interviewos.backend.integration.ai.CriterionAssessmentResponse;
import com.interviewos.backend.repository.InterviewAnswerRepository;
import com.interviewos.backend.repository.InterviewQuestionRepository;
import com.interviewos.backend.repository.InterviewRepository;

@Service
public class InterviewEvaluationPersistenceService {
    private final InterviewRepository interviewRepository;
    private final InterviewQuestionRepository questionRepository;
    private final InterviewAnswerRepository answerRepository;

    public InterviewEvaluationPersistenceService(
        InterviewRepository interviewRepository,
        InterviewQuestionRepository questionRepository,
        InterviewAnswerRepository answerRepository
    ) {
        this.interviewRepository = interviewRepository;
        this.questionRepository = questionRepository;
        this.answerRepository = answerRepository;
    }

    @Transactional
    public InterviewAnswerResponse persistEvaluation(
        UUID answerId,
        AnswerEvaluationResponse evaluation
    ) {
        InterviewAnswer answer = answerRepository.findByIdForUpdate(answerId)
            .orElseThrow(() -> new IllegalStateException("Persisted answer was not found"));
        InterviewQuestion answeredQuestion = answer.getInterviewQuestion();
        Interview interview = interviewRepository.findByIdForUpdate(
            answeredQuestion.getInterview().getId()
        ).orElseThrow(() -> new IllegalStateException("Interview for answer was not found"));

        List<CriterionAssessment> assessments = evaluation.criterionAssessments().stream()
            .map(item -> toEntity(item, answer))
            .toList();
        answer.completeEvaluation(
            evaluation.technicalAccuracy(),
            evaluation.completeness(),
            evaluation.clarity(),
            evaluation.depth(),
            evaluation.overallScore(),
            assessments,
            evaluation.strengths(),
            evaluation.missingConcepts(),
            evaluation.feedback(),
            evaluation.suggestedFollowUp(),
            evaluation.suggestedFollowUpCriteria()
        );

        if (shouldUseFollowUp(interview, answeredQuestion, evaluation)) {
            InterviewQuestion nextQuestion = questionRepository
                .findByInterview_IdAndQuestionOrder(
                    interview.getId(),
                    answeredQuestion.getQuestionOrder() + 1
                )
                .orElse(null);
            if (nextQuestion != null) {
                nextQuestion.replaceWithFollowUp(
                    evaluation.suggestedFollowUp().trim(),
                    evaluation.suggestedFollowUpCriteria()
                );
            }
        }
        return InterviewAnswerResponse.from(answer);
    }

    private boolean shouldUseFollowUp(
        Interview interview,
        InterviewQuestion answeredQuestion,
        AnswerEvaluationResponse evaluation
    ) {
        if (interview.getStatus() != InterviewStatus.IN_PROGRESS
            || interview.getCurrentQuestionOrder() == null
            || !interview.getCurrentQuestionOrder().equals(answeredQuestion.getQuestionOrder())
            || answeredQuestion.getQuestionOrder() >= interview.getNumberOfQuestions()
            || evaluation.suggestedFollowUp() == null
            || evaluation.suggestedFollowUp().isBlank()
            || !hasValidFollowUpCriteria(evaluation.suggestedFollowUpCriteria())) {
            return false;
        }

        boolean needsFollowUp = evaluation.overallScore() < 7.0
            || evaluation.criterionAssessments().stream().anyMatch(assessment ->
                "MISSING".equals(assessment.status())
                    || "PARTIALLY_COVERED".equals(assessment.status())
            );
        return needsFollowUp
            && questionRepository.findByInterview_IdAndQuestionOrder(
                interview.getId(),
                answeredQuestion.getQuestionOrder() + 1
            ).isPresent();
    }

    private boolean hasValidFollowUpCriteria(List<String> criteria) {
        if (criteria == null || criteria.isEmpty()) {
            return false;
        }
        return criteria.stream().allMatch(item -> item != null && !item.isBlank())
            && criteria.stream()
                .map(item -> item.trim().replaceAll("\\s+", " ").toLowerCase())
                .distinct()
                .count() == criteria.size();
    }

    private CriterionAssessment toEntity(
        CriterionAssessmentResponse response,
        InterviewAnswer answer
    ) {
        return new CriterionAssessment(
            response.criterion(),
            response.status(),
            response.evidence(),
            answer
        );
    }
}
