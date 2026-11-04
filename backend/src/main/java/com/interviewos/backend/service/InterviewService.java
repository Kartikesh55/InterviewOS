package com.interviewos.backend.service;

import java.util.List;
import java.util.Locale;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.interviewos.backend.dto.InterviewDetailsResponse;
import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.dto.InterviewQuestionResponse;
import com.interviewos.backend.dto.InterviewResponse;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.entity.InterviewStatus;
import com.interviewos.backend.exception.InvalidLifecycleTransitionException;
import com.interviewos.backend.exception.ResourceNotFoundException;
import com.interviewos.backend.integration.ai.AiServiceClient;
import com.interviewos.backend.integration.ai.AiServiceException;
import com.interviewos.backend.integration.ai.AnswerEvaluationRequest;
import com.interviewos.backend.integration.ai.AnswerEvaluationResponse;
import com.interviewos.backend.integration.ai.GeneratedQuestion;
import com.interviewos.backend.integration.ai.QuestionGenerationRequest;
import com.interviewos.backend.integration.ai.QuestionGenerationResponse;
import com.interviewos.backend.repository.InterviewQuestionRepository;
import com.interviewos.backend.repository.InterviewRepository;

@Service
public class InterviewService
{
    private final InterviewRepository interviewRepository;
    private final InterviewQuestionRepository questionRepository;
    private final AiServiceClient aiServiceClient;
    private final InterviewQuestionPersistenceService questionPersistenceService;
    private final InterviewAnswerService answerService;

    public InterviewService(
        InterviewRepository interviewRepository,
        InterviewQuestionRepository questionRepository,
        AiServiceClient aiServiceClient,
        InterviewQuestionPersistenceService questionPersistenceService,
        InterviewAnswerService answerService
    )
    {
        this.interviewRepository = interviewRepository;
        this.questionRepository = questionRepository;
        this.aiServiceClient = aiServiceClient;
        this.questionPersistenceService = questionPersistenceService;
        this.answerService = answerService;
    }

    public InterviewResponse createInterview(
        String targetRole,
        Difficulty difficulty,
        Integer numberOfQuestions
    )
    {
        Interview interview = new Interview(targetRole, difficulty, numberOfQuestions);

        return InterviewResponse.from(interviewRepository.save(interview));
    }

    public QuestionGenerationResponse generateQuestions(QuestionGenerationRequest request)
    {
        return aiServiceClient.generateQuestions(request);
    }

    public AnswerEvaluationResponse evaluateAnswer(AnswerEvaluationRequest request)
    {
        return aiServiceClient.evaluateAnswer(request);
    }

    public List<InterviewQuestionResponse> generateQuestionsForInterview(UUID interviewId)
    {
        Interview interview = interviewRepository.findById(interviewId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Interview not found: " + interviewId
            ));

        List<InterviewQuestionResponse> existingQuestions = questionRepository
            .findByInterview_IdOrderByQuestionOrderAsc(interviewId)
            .stream()
            .map(InterviewQuestionResponse::from)
            .toList();
        if (!existingQuestions.isEmpty()) {
            return existingQuestions;
        }
        if (interview.getStatus() != InterviewStatus.CREATED) {
            throw new InvalidLifecycleTransitionException(
                "Questions can only be generated for an interview in CREATED state"
            );
        }

        QuestionGenerationResponse generated = aiServiceClient.generateQuestions(
            new QuestionGenerationRequest(
                interview.getTargetRole(),
                interview.getDifficulty().name(),
                interview.getNumberOfQuestions()
            )
        );
        validateGeneratedQuestions(generated, interview.getNumberOfQuestions());

        return questionPersistenceService.persistGeneratedQuestions(
            interviewId,
            generated.questions()
        );
    }

    public InterviewAnswerResponse submitAnswer(
        UUID interviewId,
        UUID questionId,
        String candidateAnswer
    ) {
        return answerService.submitAnswer(interviewId, questionId, candidateAnswer);
    }

    @Transactional
    public InterviewResponse startInterview(UUID interviewId)
    {
        Interview interview = findInterviewForUpdate(interviewId);
        int questionCount = questionRepository
            .findByInterview_IdOrderByQuestionOrderAsc(interviewId)
            .size();
        if (questionCount == 0) {
            throw new InvalidLifecycleTransitionException(
                "Generate questions before starting the interview"
            );
        }
        transition(interview::start);
        return InterviewResponse.from(interview);
    }

    @Transactional(readOnly = true)
    public InterviewDetailsResponse getInterviewDetails(UUID interviewId)
    {
        Interview interview = findInterview(interviewId);
        List<InterviewQuestionResponse> questions = questionRepository
            .findByInterview_IdOrderByQuestionOrderAsc(interviewId)
            .stream()
            .map(InterviewQuestionResponse::from)
            .toList();
        return InterviewDetailsResponse.from(interview, questions);
    }

    @Transactional(readOnly = true)
    public InterviewQuestionResponse getCurrentQuestion(UUID interviewId)
    {
        Interview interview = findInterview(interviewId);
        if (interview.getStatus() != InterviewStatus.IN_PROGRESS) {
            throw new InvalidLifecycleTransitionException(
                "Current question is available only while the interview is IN_PROGRESS"
            );
        }
        if (interview.getCurrentQuestionOrder() == null) {
            throw new InvalidLifecycleTransitionException(
                "The interview has no current question"
            );
        }
        return questionRepository
            .findByInterview_IdAndQuestionOrder(
                interviewId,
                interview.getCurrentQuestionOrder()
            )
            .map(InterviewQuestionResponse::from)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Current question not found for interview: " + interviewId
            ));
    }

    @Transactional
    public InterviewQuestionResponse advanceToNextQuestion(UUID interviewId)
    {
        Interview interview = findInterviewForUpdate(interviewId);
        List<InterviewQuestionResponse> questions = questionRepository
            .findByInterview_IdOrderByQuestionOrderAsc(interviewId)
            .stream()
            .map(InterviewQuestionResponse::from)
            .toList();
        if (questions.isEmpty()) {
            throw new InvalidLifecycleTransitionException(
                "The interview has no questions to advance through"
            );
        }
        transition(() -> interview.advanceQuestion(questions.size()));
        return questionRepository
            .findByInterview_IdAndQuestionOrder(
                interviewId,
                interview.getCurrentQuestionOrder()
            )
            .map(InterviewQuestionResponse::from)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Next question not found for interview: " + interviewId
            ));
    }

    @Transactional
    public InterviewResponse completeInterview(UUID interviewId)
    {
        Interview interview = findInterviewForUpdate(interviewId);
        transition(interview::complete);
        return InterviewResponse.from(interview);
    }

    private Interview findInterview(UUID interviewId)
    {
        return interviewRepository.findById(interviewId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Interview not found: " + interviewId
            ));
    }

    private Interview findInterviewForUpdate(UUID interviewId)
    {
        return interviewRepository.findByIdForUpdate(interviewId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Interview not found: " + interviewId
            ));
    }

    private void transition(Runnable operation)
    {
        try {
            operation.run();
        } catch (IllegalStateException exception) {
            throw new InvalidLifecycleTransitionException(exception.getMessage());
        }
    }

    private void validateGeneratedQuestions(
        QuestionGenerationResponse generated,
        int maximumQuestionCount
    ) {
        if (generated == null
            || generated.questions() == null
            || generated.questions().size() != maximumQuestionCount
            || generated.questions().stream().anyMatch(this::hasInvalidQuestion)) {
            throw new AiServiceException(
                HttpStatus.BAD_GATEWAY,
                "AI service returned invalid questions or evaluation criteria",
                null
            );
        }
    }

    private boolean hasInvalidQuestion(GeneratedQuestion question) {
        return question == null
            || question.questionText() == null
            || question.questionText().isBlank()
            || question.evaluationCriteria() == null
            || question.evaluationCriteria().isEmpty()
            || question.evaluationCriteria().stream().anyMatch(
                criterion -> criterion == null || criterion.isBlank()
            )
            || question.evaluationCriteria().stream()
                .map(criterion -> criterion.trim().replaceAll("\\s+", " ")
                    .toLowerCase(Locale.ROOT))
                .distinct()
                .count() != question.evaluationCriteria().size();
    }
}