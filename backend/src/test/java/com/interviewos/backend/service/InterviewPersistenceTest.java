package com.interviewos.backend.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyList;
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
import org.springframework.test.util.ReflectionTestUtils;

import com.interviewos.backend.dto.InterviewQuestionResponse;
import com.interviewos.backend.dto.InterviewResponse;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.InterviewAnswer;
import com.interviewos.backend.entity.InterviewQuestion;
import com.interviewos.backend.entity.EvaluationStatus;
import com.interviewos.backend.entity.InterviewStatus;
import com.interviewos.backend.exception.InvalidLifecycleTransitionException;
import com.interviewos.backend.exception.ResourceNotFoundException;
import com.interviewos.backend.integration.ai.AiServiceClient;
import com.interviewos.backend.integration.ai.GeneratedQuestion;
import com.interviewos.backend.integration.ai.QuestionGenerationRequest;
import com.interviewos.backend.integration.ai.QuestionGenerationResponse;
import com.interviewos.backend.repository.InterviewAnswerRepository;
import com.interviewos.backend.repository.InterviewQuestionRepository;
import com.interviewos.backend.repository.InterviewRepository;

@ExtendWith(MockitoExtension.class)
class InterviewPersistenceTest {
    @Mock
    private InterviewRepository interviewRepository;

    @Mock
    private InterviewQuestionRepository questionRepository;

    @Mock
    private InterviewAnswerRepository answerRepository;

    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private InterviewQuestionPersistenceService questionPersistenceService;

    @Mock
    private InterviewAnswerService answerService;

    @Test
    void persistsGeneratedQuestionsInOrderAndAssociatesThemWithInterview() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 2);
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of());
        when(questionRepository.saveAll(anyList()))
            .thenAnswer(invocation -> invocation.getArgument(0));

        List<InterviewQuestionResponse> persisted =
            new InterviewQuestionPersistenceService(interviewRepository, questionRepository)
                .persistGeneratedQuestions(
                    interviewId,
                    List.of(
                        new GeneratedQuestion(
                            "Explain transactions.",
                            List.of("Atomicity", "Isolation")
                        ),
                        new GeneratedQuestion(
                            "What is an index?",
                            List.of("Lookup performance", "Write trade-offs")
                        )
                    )
                );

        assertEquals(2, persisted.size());
        assertEquals("Explain transactions.", persisted.get(0).questionText());
        assertEquals(1, persisted.get(0).questionOrder());
        assertEquals(
            List.of("Atomicity", "Isolation"),
            persisted.get(0).evaluationCriteria()
        );
        assertEquals("What is an index?", persisted.get(1).questionText());
        assertEquals(2, persisted.get(1).questionOrder());

        org.mockito.ArgumentCaptor<List<InterviewQuestion>> captor =
            org.mockito.ArgumentCaptor.forClass(List.class);
        verify(questionRepository).saveAll(captor.capture());
        assertSame(interview, captor.getValue().get(0).getInterview());
        assertSame(interview, captor.getValue().get(1).getInterview());
        assertEquals(
            List.of("Atomicity", "Isolation"),
            captor.getValue().get(0).getEvaluationCriteria()
        );
    }

    @Test
    void returnsExistingQuestionsWhenGenerationWasAlreadyPersisted() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 1);
        InterviewQuestion existing =
            new InterviewQuestion("Existing question?", 1, interview);
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of(existing));

        List<InterviewQuestionResponse> result =
            new InterviewQuestionPersistenceService(interviewRepository, questionRepository)
                .persistGeneratedQuestions(
                    interviewId,
                    List.of(new GeneratedQuestion("New question?", List.of("Specific criterion")))
                );

        assertEquals(1, result.size());
        assertEquals("Existing question?", result.getFirst().questionText());
        verify(questionRepository, never()).saveAll(anyList());
    }

    @Test
    void rejectsQuestionPersistenceForUnknownInterview() {
        UUID interviewId = UUID.randomUUID();
        when(interviewRepository.findByIdForUpdate(interviewId)).thenReturn(Optional.empty());

        assertThrows(
            ResourceNotFoundException.class,
            () -> new InterviewQuestionPersistenceService(
                interviewRepository,
                questionRepository
            ).persistGeneratedQuestions(
                interviewId,
                List.of(new GeneratedQuestion("Question", List.of("Criterion")))
            )
        );
    }

    @Test
    void persistsAnswerAgainstTheRequestedInterviewQuestion() {
        UUID interviewId = UUID.randomUUID();
        UUID questionId = UUID.randomUUID();
        Interview interview = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 1);
        InterviewQuestion question = new InterviewQuestion(
            "Explain transactions.",
            1,
            interview,
            List.of("Atomicity", "Isolation")
        );
        ReflectionTestUtils.setField(question, "id", questionId);

        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interviewInProgressAt(1)));
        when(questionRepository.findByIdAndInterview_Id(questionId, interviewId))
            .thenReturn(Optional.of(question));
        when(answerRepository.save(org.mockito.ArgumentMatchers.any(InterviewAnswer.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        PendingAnswerSubmission pending = new InterviewAnswerPersistenceService(
            interviewRepository,
            questionRepository,
            answerRepository
        ).persistPendingAnswer(interviewId, questionId, "A transaction groups operations.");

        assertEquals("A transaction groups operations.", pending.candidateAnswer());
        assertEquals("Explain transactions.", pending.questionText());
        assertEquals(List.of("Atomicity", "Isolation"), pending.evaluationCriteria());
        org.mockito.ArgumentCaptor<InterviewAnswer> answerCaptor =
            org.mockito.ArgumentCaptor.forClass(InterviewAnswer.class);
        verify(answerRepository).save(answerCaptor.capture());
        assertSame(question, answerCaptor.getValue().getInterviewQuestion());
        assertNotNull(answerCaptor.getValue().getSubmittedAt());
    }

    @Test
    void rejectsAnswersForUnknownInterviewOrQuestion() {
        UUID interviewId = UUID.randomUUID();
        UUID questionId = UUID.randomUUID();
        InterviewAnswerPersistenceService service = new InterviewAnswerPersistenceService(
            interviewRepository,
            questionRepository,
            answerRepository
        );
        when(interviewRepository.findByIdForUpdate(interviewId)).thenReturn(Optional.empty());

        assertThrows(
            ResourceNotFoundException.class,
            () -> service.persistPendingAnswer(interviewId, questionId, "Answer")
        );

        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interviewInProgressAt(1)));
        when(questionRepository.findByIdAndInterview_Id(questionId, interviewId))
            .thenReturn(Optional.empty());
        assertThrows(
            ResourceNotFoundException.class,
            () -> service.persistPendingAnswer(interviewId, questionId, "Answer")
        );
    }

    @Test
    void marksPersistedAnswerFailedWithoutRemovingCandidateText() {
        UUID answerId = UUID.randomUUID();
        InterviewAnswer answer = new InterviewAnswer(
            "Persist this answer even if evaluation fails.",
            new InterviewQuestion(
                "Question?",
                1,
                new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 1),
                List.of("Criterion")
            )
        );
        ReflectionTestUtils.setField(answer, "id", answerId);
        when(answerRepository.findByIdForUpdate(answerId)).thenReturn(Optional.of(answer));

        var response = new InterviewAnswerPersistenceService(
            interviewRepository,
            questionRepository,
            answerRepository
        ).markFailed(answerId);

        assertEquals(EvaluationStatus.FAILED, response.evaluationStatus());
        assertEquals(
            "Persist this answer even if evaluation fails.",
            response.candidateAnswer()
        );
    }

    @Test
    void interviewScopedGenerationUsesStoredQuestionsAndDoesNotCallAiAgain() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 1);
        InterviewQuestion existing = new InterviewQuestion("Existing question?", 1, interview);
        when(interviewRepository.findById(interviewId)).thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of(existing));

        InterviewService service = new InterviewService(
            interviewRepository,
            questionRepository,
            aiServiceClient,
            questionPersistenceService,
            answerService
        );
        List<InterviewQuestionResponse> result = service.generateQuestionsForInterview(interviewId);

        assertEquals("Existing question?", result.getFirst().questionText());
        verify(aiServiceClient, never()).generateQuestions(
            org.mockito.ArgumentMatchers.any(QuestionGenerationRequest.class)
        );
    }

    @Test
    void interviewScopedGenerationCallsAiThenPersistsTheReturnedQuestions() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 1);
        when(interviewRepository.findById(interviewId)).thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of());
        when(aiServiceClient.generateQuestions(
            org.mockito.ArgumentMatchers.any(QuestionGenerationRequest.class)
        )).thenReturn(new QuestionGenerationResponse(List.of(
            new GeneratedQuestion("Generated question?", List.of("Correctness"))
        )));
        List<InterviewQuestionResponse> persisted = List.of(
            new InterviewQuestionResponse(UUID.randomUUID(), "Generated question?", 1)
        );
        when(questionPersistenceService.persistGeneratedQuestions(
            interviewId,
            List.of(new GeneratedQuestion("Generated question?", List.of("Correctness")))
        )).thenReturn(persisted);

        InterviewService service = new InterviewService(
            interviewRepository,
            questionRepository,
            aiServiceClient,
            questionPersistenceService,
            answerService
        );
        List<InterviewQuestionResponse> result = service.generateQuestionsForInterview(interviewId);

        assertEquals(persisted, result);
        verify(aiServiceClient).generateQuestions(
            new QuestionGenerationRequest("Backend Engineer", "INTERMEDIATE", 1)
        );
        verify(questionPersistenceService).persistGeneratedQuestions(
            interviewId,
            List.of(new GeneratedQuestion("Generated question?", List.of("Correctness")))
        );
    }

    @Test
    void standaloneQuestionGenerationRemainsAvailable() {
        QuestionGenerationRequest request =
            new QuestionGenerationRequest("Backend Engineer", "INTERMEDIATE", 1);
        QuestionGenerationResponse response =
            new QuestionGenerationResponse(List.of(
                new GeneratedQuestion("Generated question?", List.of("Correctness"))
            ));
        when(aiServiceClient.generateQuestions(request)).thenReturn(response);

        InterviewService service = new InterviewService(
            interviewRepository,
            questionRepository,
            aiServiceClient,
            questionPersistenceService,
            answerService
        );

        assertEquals(response, service.generateQuestions(request));
    }

    @Test
    void startsCreatedInterviewAtItsFirstPersistedQuestion() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 2);
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of(
                new InterviewQuestion("First?", 1, interview),
                new InterviewQuestion("Second?", 2, interview)
            ));

        InterviewResponse response = lifecycleService().startInterview(interviewId);

        assertEquals(InterviewStatus.IN_PROGRESS, response.status());
        assertEquals(1, interview.getCurrentQuestionOrder());
    }

    @Test
    void doesNotStartInterviewWithoutPersistedQuestions() {
        UUID interviewId = UUID.randomUUID();
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(new Interview(
                "Backend Engineer",
                Difficulty.INTERMEDIATE,
                2
            )));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of());

        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> lifecycleService().startInterview(interviewId)
        );
    }

    @Test
    void rejectsStartingInterviewOutsideCreatedState() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = inProgressInterview();
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));

        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> lifecycleService().startInterview(interviewId)
        );
    }

    @Test
    void retrievesDetailsWithPersistedQuestionsAndCurrentProgress() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = inProgressInterview();
        List<InterviewQuestion> questions = List.of(
            new InterviewQuestion("First?", 1, interview),
            new InterviewQuestion("Second?", 2, interview)
        );
        when(interviewRepository.findById(interviewId)).thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(questions);

        var details = lifecycleService().getInterviewDetails(interviewId);

        assertEquals(InterviewStatus.IN_PROGRESS, details.status());
        assertEquals(1, details.currentQuestionOrder());
        assertEquals(List.of("First?", "Second?"), details.questions().stream()
            .map(InterviewQuestionResponse::questionText)
            .toList());
    }

    @Test
    void retrievesAndAdvancesCurrentQuestionInOrder() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = inProgressInterview();
        when(interviewRepository.findById(interviewId)).thenReturn(Optional.of(interview));
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of(
                new InterviewQuestion("First?", 1, interview),
                new InterviewQuestion("Second?", 2, interview)
            ));
        when(questionRepository.findByInterview_IdAndQuestionOrder(interviewId, 1))
            .thenReturn(Optional.of(new InterviewQuestion("First?", 1, interview)));
        when(questionRepository.findByInterview_IdAndQuestionOrder(interviewId, 2))
            .thenReturn(Optional.of(new InterviewQuestion("Second?", 2, interview)));

        assertEquals("First?", lifecycleService().getCurrentQuestion(interviewId).questionText());
        assertEquals(
            "Second?",
            lifecycleService().advanceToNextQuestion(interviewId).questionText()
        );
        assertEquals(2, interview.getCurrentQuestionOrder());
    }

    @Test
    void preventsAdvancingPastFinalQuestionWithoutChangingCurrentIndex() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = inProgressInterview();
        interview.advanceQuestion(2);
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of(
                new InterviewQuestion("First?", 1, interview),
                new InterviewQuestion("Second?", 2, interview)
            ));

        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> lifecycleService().advanceToNextQuestion(interviewId)
        );
        assertEquals(2, interview.getCurrentQuestionOrder());
    }

    @Test
    void completesOnlyAnInProgressInterview() {
        UUID interviewId = UUID.randomUUID();
        Interview interview = inProgressInterview();
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(interview));

        InterviewResponse response = lifecycleService().completeInterview(interviewId);

        assertEquals(InterviewStatus.COMPLETED, response.status());
    }

    @Test
    void rejectsCompletionBeforeStartAndStartingCompletedInterview() {
        UUID interviewId = UUID.randomUUID();
        Interview created = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 1);
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(created));
        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> lifecycleService().completeInterview(interviewId)
        );

        Interview completed = inProgressInterview();
        completed.complete();
        when(interviewRepository.findByIdForUpdate(interviewId))
            .thenReturn(Optional.of(completed));
        when(questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId))
            .thenReturn(List.of(new InterviewQuestion("Question?", 1, completed)));
        assertThrows(
            InvalidLifecycleTransitionException.class,
            () -> lifecycleService().startInterview(interviewId)
        );
    }

    @Test
    void lifecycleOperationsReturnNotFoundForUnknownInterviewOrQuestion() {
        UUID interviewId = UUID.randomUUID();
        when(interviewRepository.findByIdForUpdate(interviewId)).thenReturn(Optional.empty());
        assertThrows(
            ResourceNotFoundException.class,
            () -> lifecycleService().startInterview(interviewId)
        );

        when(interviewRepository.findById(interviewId)).thenReturn(Optional.empty());
        assertThrows(
            ResourceNotFoundException.class,
            () -> lifecycleService().getInterviewDetails(interviewId)
        );

        Interview interview = inProgressInterview();
        when(interviewRepository.findById(interviewId)).thenReturn(Optional.of(interview));
        when(questionRepository.findByInterview_IdAndQuestionOrder(interviewId, 1))
            .thenReturn(Optional.empty());
        assertThrows(
            ResourceNotFoundException.class,
            () -> lifecycleService().getCurrentQuestion(interviewId)
        );
    }

    private InterviewService lifecycleService() {
        return new InterviewService(
            interviewRepository,
            questionRepository,
            aiServiceClient,
            questionPersistenceService,
            answerService
        );
    }

    private Interview inProgressInterview() {
        Interview interview = new Interview("Backend Engineer", Difficulty.INTERMEDIATE, 2);
        interview.start();
        return interview;
    }

    private Interview interviewInProgressAt(int questionOrder) {
        Interview interview = inProgressInterview();
        while (interview.getCurrentQuestionOrder() < questionOrder) {
            interview.advanceQuestion(questionOrder);
        }
        return interview;
    }
}
