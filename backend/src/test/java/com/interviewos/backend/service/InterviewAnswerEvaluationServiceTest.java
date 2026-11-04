package com.interviewos.backend.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;

import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.entity.EvaluationStatus;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.InterviewAnswer;
import com.interviewos.backend.entity.InterviewQuestion;
import com.interviewos.backend.entity.InterviewStatus;
import com.interviewos.backend.entity.QuestionSource;
import com.interviewos.backend.exception.InvalidLifecycleTransitionException;
import com.interviewos.backend.integration.ai.AiServiceClient;
import com.interviewos.backend.integration.ai.AiServiceException;
import com.interviewos.backend.integration.ai.AnswerEvaluationRequest;
import com.interviewos.backend.integration.ai.AnswerEvaluationResponse;
import com.interviewos.backend.integration.ai.CriterionAssessmentResponse;
import com.interviewos.backend.repository.InterviewAnswerRepository;
import com.interviewos.backend.repository.InterviewQuestionRepository;
import com.interviewos.backend.repository.InterviewRepository;

@ExtendWith(MockitoExtension.class)
class InterviewAnswerEvaluationServiceTest {
    @Mock
    private InterviewRepository interviewRepository;

    @Mock
    private InterviewQuestionRepository questionRepository;

    @Mock
    private InterviewAnswerRepository answerRepository;

    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private InterviewAnswerPersistenceService answerPersistenceService;

    @Mock
    private InterviewEvaluationPersistenceService evaluationPersistenceService;

    @Test
    void evaluatesWithStoredQuestionCriteriaAndPersistsCompleteEvaluation() {
        UUID interviewId = UUID.randomUUID();
        UUID questionId = UUID.randomUUID();
        UUID answerId = UUID.randomUUID();
        List<String> storedCriteria = List.of("Atomicity", "Isolation");
        PendingAnswerSubmission pending = new PendingAnswerSubmission(
            answerId,
            "Explain transactions.",
            "They group database operations.",
            "Backend Engineer",
            "INTERMEDIATE",
            storedCriteria
        );
        AnswerEvaluationResponse evaluation = evaluation(
            6.5,
            List.of(assessment("Atomicity", "COVERED"), assessment("Isolation", "MISSING")),
            "How would you prevent a dirty read?",
            List.of("Isolation level", "Transaction behavior")
        );
        InterviewAnswerResponse persisted = new InterviewAnswerResponse(
            answerId,
            questionId,
            pending.candidateAnswer(),
            java.time.LocalDateTime.now(),
            EvaluationStatus.COMPLETED,
            8.0,
            5.0,
            8.0,
            7.0,
            7.1,
            evaluation.criterionAssessments(),
            evaluation.strengths(),
            evaluation.missingConcepts(),
            evaluation.feedback(),
            evaluation.suggestedFollowUp(),
            evaluation.suggestedFollowUpCriteria()
        );
        when(answerPersistenceService.persistPendingAnswer(
            interviewId,
            questionId,
            pending.candidateAnswer()
        )).thenReturn(pending);
        when(aiServiceClient.evaluateAnswer(any(AnswerEvaluationRequest.class)))
            .thenReturn(evaluation);
        when(evaluationPersistenceService.persistEvaluation(answerId, evaluation))
            .thenReturn(persisted);

        InterviewAnswerResponse result = new InterviewAnswerService(
            answerPersistenceService,
            evaluationPersistenceService,
            aiServiceClient
        ).submitAnswer(interviewId, questionId, pending.candidateAnswer());

        assertEquals(EvaluationStatus.COMPLETED, result.evaluationStatus());
        assertEquals("How would you prevent a dirty read?", result.suggestedFollowUp());
        org.mockito.ArgumentCaptor<AnswerEvaluationRequest> requestCaptor =
            org.mockito.ArgumentCaptor.forClass(AnswerEvaluationRequest.class);
        verify(aiServiceClient).evaluateAnswer(requestCaptor.capture());
        assertEquals("Explain transactions.", requestCaptor.getValue().question());
        assertEquals(pending.candidateAnswer(), requestCaptor.getValue().candidateAnswer());
        assertEquals("Backend Engineer", requestCaptor.getValue().targetRole());
        assertEquals("INTERMEDIATE", requestCaptor.getValue().difficulty());
        assertEquals(storedCriteria, requestCaptor.getValue().evaluationCriteria());
        verify(evaluationPersistenceService).persistEvaluation(answerId, evaluation);
    }

    @Test
    void retainsPersistedAnswerAndMarksEvaluationFailedWhenAiCallFails() {
        UUID interviewId = UUID.randomUUID();
        UUID questionId = UUID.randomUUID();
        UUID answerId = UUID.randomUUID();
        PendingAnswerSubmission pending = new PendingAnswerSubmission(
            answerId,
            "Stored question?",
            "Persisted answer",
            "Backend Engineer",
            "INTERMEDIATE",
            List.of("Criterion")
        );
        InterviewAnswerResponse failed = new InterviewAnswerResponse(
            answerId,
            questionId,
            pending.candidateAnswer(),
            java.time.LocalDateTime.now(),
            EvaluationStatus.FAILED,
            null,
            null,
            null,
            null,
            null,
            List.of(),
            List.of(),
            List.of(),
            null,
            null,
            List.of()
        );
        when(answerPersistenceService.persistPendingAnswer(
            interviewId,
            questionId,
            pending.candidateAnswer()
        )).thenReturn(pending);
        when(aiServiceClient.evaluateAnswer(any(AnswerEvaluationRequest.class)))
            .thenThrow(new AiServiceException(
                HttpStatus.BAD_GATEWAY,
                "AI service unavailable",
                new RuntimeException("connection failed")
            ));
        when(answerPersistenceService.markFailed(answerId)).thenReturn(failed);

        InterviewAnswerResponse result = new InterviewAnswerService(
            answerPersistenceService,
            evaluationPersistenceService,
            aiServiceClient
        ).submitAnswer(interviewId, questionId, pending.candidateAnswer());

        assertEquals(EvaluationStatus.FAILED, result.evaluationStatus());
        assertEquals("Persisted answer", result.candidateAnswer());
        verify(answerPersistenceService).persistPendingAnswer(
            interviewId,
            questionId,
            "Persisted answer"
        );
        verify(answerPersistenceService).markFailed(answerId);
        verify(evaluationPersistenceService, never()).persistEvaluation(any(), any());
    }

    @Test
    void refusesAnswersForNonCurrentQuestionsAndCompletedInterviews() {
        UUID interviewId = UUID.randomUUID();
        UUID questionId = UUID.randomUUID();
        Interview inProgress = inProgressInterview(1, 2);
        InterviewQuestion otherQuestion = question("Second?", 2, inProgress, List.of("Criterion"));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(inProgress));
        when(questionRepository.findByIdAndInterview_Id(questionId, interviewId))
            .thenReturn(Optional.of(otherQuestion));

        InterviewAnswerPersistenceService service = new InterviewAnswerPersistenceService(
            interviewRepository,
            questionRepository,
            answerRepository
        );
        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> service.persistPendingAnswer(interviewId, questionId, "Answer")
        );

        Interview completed = inProgressInterview(1, 1);
        completed.complete();
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(completed));
        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> service.persistPendingAnswer(interviewId, questionId, "Answer")
        );
    }

    @Test
    void preventsDuplicateAnswerSubmissionForAQuestion() {
        UUID interviewId = UUID.randomUUID();
        UUID questionId = UUID.randomUUID();
        Interview interview = inProgressInterview(1, 1);
        InterviewQuestion current = question("Current?", 1, interview, List.of("Criterion"));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByIdAndInterview_Id(questionId, interviewId))
            .thenReturn(Optional.of(current));
        when(answerRepository.existsByInterviewQuestion_Id(questionId)).thenReturn(true);

        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> new InterviewAnswerPersistenceService(
                interviewRepository,
                questionRepository,
                answerRepository
            ).persistPendingAnswer(interviewId, questionId, "A second answer")
        );
    }

    @Test
    void lowScoreUsesValidFollowUpToReplaceNextQuestionWithoutIncreasingCount() {
        Interview interview = inProgressInterview(1, 2);
        UUID interviewId = setId(interview);
        InterviewQuestion answeredQuestion = question(
            "Original first?",
            1,
            interview,
            List.of("Criterion")
        );
        InterviewQuestion scheduledNext = question(
            "Original second?",
            2,
            interview,
            List.of("Next criterion")
        );
        InterviewAnswer answer = answer(answeredQuestion);
        when(answerRepository.findByIdForUpdate(answer.getId())).thenReturn(Optional.of(answer));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdAndQuestionOrder(interviewId, 2))
            .thenReturn(Optional.of(scheduledNext));

        InterviewAnswerResponse result = evaluationPersistence().persistEvaluation(
            answer.getId(),
            evaluation(
                6.5,
                List.of(assessment("Criterion", "COVERED")),
                "Explain how isolation prevents dirty reads.",
                List.of("Isolation behavior")
            )
        );

        assertEquals(EvaluationStatus.COMPLETED, result.evaluationStatus());
        assertEquals(6.5, result.overallScore());
        assertEquals(8.0, result.technicalAccuracy());
        assertEquals(5.0, result.completeness());
        assertEquals(8.0, result.clarity());
        assertEquals(7.0, result.depth());
        assertEquals("Actionable feedback", result.feedback());
        assertEquals("Explain how isolation prevents dirty reads.", result.suggestedFollowUp());
        assertEquals(List.of("Isolation behavior"), result.suggestedFollowUpCriteria());
        assertEquals("Criterion", result.criterionAssessments().getFirst().criterion());
        assertEquals(QuestionSource.FOLLOW_UP, scheduledNext.getSource());
        assertEquals("Explain how isolation prevents dirty reads.", scheduledNext.getQuestionText());
        assertEquals(List.of("Isolation behavior"), scheduledNext.getEvaluationCriteria());
        assertEquals(
            2,
            List.of(answeredQuestion, scheduledNext).size(),
            "Follow-up replaces the scheduled row instead of adding a question"
        );
    }

    @Test
    void partialOrMissingCriterionSelectsFollowUpEvenWithHighOverallScore() {
        Interview interview = inProgressInterview(1, 2);
        UUID interviewId = setId(interview);
        InterviewQuestion answeredQuestion = question("Current?", 1, interview, List.of("C"));
        InterviewQuestion scheduledNext = question("Next?", 2, interview, List.of("N"));
        InterviewAnswer answer = answer(answeredQuestion);
        when(answerRepository.findByIdForUpdate(answer.getId())).thenReturn(Optional.of(answer));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdAndQuestionOrder(interviewId, 2))
            .thenReturn(Optional.of(scheduledNext));

        evaluationPersistence().persistEvaluation(
            answer.getId(),
            evaluation(
                9.0,
                List.of(assessment("C", "PARTIALLY_COVERED")),
                "Explain the omitted part.",
                List.of("Missing explanation")
            )
        );

        assertEquals(QuestionSource.FOLLOW_UP, scheduledNext.getSource());
    }

    @Test
    void goodAnswerContinuesNormallyAndInvalidFollowUpDoesNotReplaceNextQuestion() {
        Interview interview = inProgressInterview(1, 2);
        UUID interviewId = setId(interview);
        InterviewQuestion answeredQuestion = question("Current?", 1, interview, List.of("C"));
        InterviewQuestion scheduledNext = question("Scheduled next?", 2, interview, List.of("N"));
        InterviewAnswer answer = answer(answeredQuestion);
        when(answerRepository.findByIdForUpdate(answer.getId())).thenReturn(Optional.of(answer));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));

        evaluationPersistence().persistEvaluation(
            answer.getId(),
            evaluation(
                9.0,
                List.of(assessment("C", "COVERED")),
                "A proposed follow-up?",
                List.of("Criterion")
            )
        );

        assertEquals(QuestionSource.GENERATED, scheduledNext.getSource());

        InterviewAnswer secondAnswer = answer(question("Current?", 1, interview, List.of("C")));
        ReflectionTestUtils.setField(secondAnswer, "id", UUID.randomUUID());
        when(answerRepository.findByIdForUpdate(secondAnswer.getId()))
            .thenReturn(Optional.of(secondAnswer));
        evaluationPersistence().persistEvaluation(
            secondAnswer.getId(),
            evaluation(5.0, List.of(assessment("C", "MISSING")), "   ", List.of())
        );
        assertEquals(QuestionSource.GENERATED, scheduledNext.getSource());
    }

    @Test
    void noFollowUpIsInsertedAfterFinalQuestion() {
        Interview interview = inProgressInterview(2, 2);
        UUID interviewId = setId(interview);
        InterviewQuestion answeredQuestion = question("Final?", 2, interview, List.of("C"));
        InterviewAnswer answer = answer(answeredQuestion);
        when(answerRepository.findByIdForUpdate(answer.getId())).thenReturn(Optional.of(answer));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));

        evaluationPersistence().persistEvaluation(
            answer.getId(),
            evaluation(
                2.0,
                List.of(assessment("C", "MISSING")),
                "Final follow-up?",
                List.of("Criterion")
            )
        );

        verify(questionRepository, never())
            .findByInterview_IdAndQuestionOrder(interviewId, 3);
    }

    @Test
    void followUpCriteriaMustBeNonEmptyAndUnique() {
        Interview interview = inProgressInterview(1, 2);
        UUID interviewId = setId(interview);
        InterviewQuestion answeredQuestion = question("Current?", 1, interview, List.of("C"));
        InterviewQuestion scheduledNext = question("Next?", 2, interview, List.of("N"));
        InterviewAnswer answer = answer(answeredQuestion);
        when(answerRepository.findByIdForUpdate(answer.getId())).thenReturn(Optional.of(answer));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));

        evaluationPersistence().persistEvaluation(
            answer.getId(),
            evaluation(2.0, List.of(assessment("C", "MISSING")), "Follow up?", List.of(" ", "C"))
        );

        assertEquals(QuestionSource.GENERATED, scheduledNext.getSource());
    }

    private InterviewEvaluationPersistenceService evaluationPersistence() {
        return new InterviewEvaluationPersistenceService(
            interviewRepository,
            questionRepository,
            answerRepository
        );
    }

    private AnswerEvaluationResponse evaluation(
        double overallScore,
        List<CriterionAssessmentResponse> assessments,
        String followUp,
        List<String> followUpCriteria
    ) {
        return new AnswerEvaluationResponse(
            EvaluationStatus.COMPLETED,
            8.0,
            5.0,
            8.0,
            7.0,
            overallScore,
            assessments,
            List.of("A strength"),
            List.of(),
            "Actionable feedback",
            followUp,
            followUpCriteria
        );
    }

    private CriterionAssessmentResponse assessment(String criterion, String status) {
        return new CriterionAssessmentResponse(criterion, status, "Verbatim evidence");
    }

    private Interview inProgressInterview(int currentOrder, int maxQuestions) {
        Interview interview = new Interview(
            "Backend Engineer",
            Difficulty.INTERMEDIATE,
            maxQuestions
        );
        interview.start();
        for (int order = 1; order < currentOrder; order++) {
            interview.advanceQuestion(maxQuestions);
        }
        return interview;
    }

    private InterviewQuestion question(
        String text,
        int order,
        Interview interview,
        List<String> criteria
    ) {
        return new InterviewQuestion(text, order, interview, criteria);
    }

    private InterviewAnswer answer(InterviewQuestion question) {
        InterviewAnswer answer = new InterviewAnswer("Candidate answer", question);
        ReflectionTestUtils.setField(answer, "id", UUID.randomUUID());
        return answer;
    }

    private UUID setId(Interview interview) {
        UUID id = UUID.randomUUID();
        ReflectionTestUtils.setField(interview, "id", id);
        return id;
    }
}
