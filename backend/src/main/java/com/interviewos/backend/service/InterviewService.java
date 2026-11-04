package com.interviewos.backend.service;

import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.dto.InterviewQuestionResponse;
import com.interviewos.backend.dto.InterviewResponse;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.exception.ResourceNotFoundException;
import com.interviewos.backend.integration.ai.AiServiceClient;
import com.interviewos.backend.integration.ai.AnswerEvaluationRequest;
import com.interviewos.backend.integration.ai.AnswerEvaluationResponse;
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

        QuestionGenerationResponse generated = aiServiceClient.generateQuestions(
            new QuestionGenerationRequest(
                interview.getTargetRole(),
                interview.getDifficulty().name(),
                interview.getNumberOfQuestions()
            )
        );

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
}