package com.interviewos.backend.service;

import org.springframework.stereotype.Service;

import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.integration.ai.AiServiceClient;
import com.interviewos.backend.integration.ai.AnswerEvaluationRequest;
import com.interviewos.backend.integration.ai.AnswerEvaluationResponse;
import com.interviewos.backend.integration.ai.QuestionGenerationRequest;
import com.interviewos.backend.integration.ai.QuestionGenerationResponse;
import com.interviewos.backend.repository.InterviewRepository;

@Service
public class InterviewService
{
    private final InterviewRepository interviewRepository;
    private final AiServiceClient aiServiceClient;

    public InterviewService(
        InterviewRepository interviewRepository,
        AiServiceClient aiServiceClient
    )
    {
        this.interviewRepository = interviewRepository;
        this.aiServiceClient = aiServiceClient;
    }

    public Interview createInterview(String targetRole, Difficulty difficulty, Integer numberOfQuestions)
    {
        Interview interview = new Interview(targetRole, difficulty, numberOfQuestions);

        return interviewRepository.save(interview);
    }

    public QuestionGenerationResponse generateQuestions(QuestionGenerationRequest request)
    {
        return aiServiceClient.generateQuestions(request);
    }

    public AnswerEvaluationResponse evaluateAnswer(AnswerEvaluationRequest request)
    {
        return aiServiceClient.evaluateAnswer(request);
    }
}