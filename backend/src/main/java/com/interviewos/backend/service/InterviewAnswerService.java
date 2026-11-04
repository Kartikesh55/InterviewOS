package com.interviewos.backend.service;

import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.entity.InterviewAnswer;
import com.interviewos.backend.entity.InterviewQuestion;
import com.interviewos.backend.exception.ResourceNotFoundException;
import com.interviewos.backend.repository.InterviewAnswerRepository;
import com.interviewos.backend.repository.InterviewQuestionRepository;
import com.interviewos.backend.repository.InterviewRepository;

@Service
public class InterviewAnswerService {
    private final InterviewRepository interviewRepository;
    private final InterviewQuestionRepository questionRepository;
    private final InterviewAnswerRepository answerRepository;

    public InterviewAnswerService(
        InterviewRepository interviewRepository,
        InterviewQuestionRepository questionRepository,
        InterviewAnswerRepository answerRepository
    ) {
        this.interviewRepository = interviewRepository;
        this.questionRepository = questionRepository;
        this.answerRepository = answerRepository;
    }

    @Transactional
    public InterviewAnswerResponse submitAnswer(
        UUID interviewId,
        UUID questionId,
        String candidateAnswer
    ) {
        if (!interviewRepository.existsById(interviewId)) {
            throw new ResourceNotFoundException("Interview not found: " + interviewId);
        }

        InterviewQuestion question = questionRepository
            .findByIdAndInterview_Id(questionId, interviewId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Question not found for interview: " + questionId
            ));

        InterviewAnswer answer = answerRepository.save(
            new InterviewAnswer(candidateAnswer, question)
        );
        return InterviewAnswerResponse.from(answer);
    }
}
