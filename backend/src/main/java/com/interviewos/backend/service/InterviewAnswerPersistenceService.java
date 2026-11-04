package com.interviewos.backend.service;

import java.util.UUID;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.entity.EvaluationStatus;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.InterviewAnswer;
import com.interviewos.backend.entity.InterviewQuestion;
import com.interviewos.backend.entity.InterviewStatus;
import com.interviewos.backend.exception.InvalidLifecycleTransitionException;
import com.interviewos.backend.exception.ResourceNotFoundException;
import com.interviewos.backend.repository.InterviewAnswerRepository;
import com.interviewos.backend.repository.InterviewQuestionRepository;
import com.interviewos.backend.repository.InterviewRepository;

@Service
public class InterviewAnswerPersistenceService {
    private final InterviewRepository interviewRepository;
    private final InterviewQuestionRepository questionRepository;
    private final InterviewAnswerRepository answerRepository;

    public InterviewAnswerPersistenceService(
        InterviewRepository interviewRepository,
        InterviewQuestionRepository questionRepository,
        InterviewAnswerRepository answerRepository
    ) {
        this.interviewRepository = interviewRepository;
        this.questionRepository = questionRepository;
        this.answerRepository = answerRepository;
    }

    @Transactional
    public PendingAnswerSubmission persistPendingAnswer(
        UUID interviewId,
        UUID questionId,
        String candidateAnswer
    ) {
        Interview interview = interviewRepository.findByIdForUpdate(interviewId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Interview not found: " + interviewId
            ));
        if (interview.getStatus() != InterviewStatus.IN_PROGRESS) {
            throw new InvalidLifecycleTransitionException(
                "Answers can only be submitted while the interview is IN_PROGRESS"
            );
        }

        InterviewQuestion question = questionRepository
            .findByIdAndInterview_Id(questionId, interviewId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Question not found for interview: " + questionId
            ));
        if (!question.getQuestionOrder().equals(interview.getCurrentQuestionOrder())) {
            throw new InvalidLifecycleTransitionException(
                "Answers can only be submitted for the current question"
            );
        }
        if (question.getEvaluationCriteria().isEmpty()) {
            throw new InvalidLifecycleTransitionException(
                "The current question has no evaluation criteria"
            );
        }
        if (answerRepository.existsByInterviewQuestion_Id(questionId)) {
            throw new InvalidLifecycleTransitionException(
                "An answer has already been submitted for this question"
            );
        }

        InterviewAnswer answer = answerRepository.save(
            new InterviewAnswer(candidateAnswer, question)
        );
        return new PendingAnswerSubmission(
            answer.getId(),
            question.getQuestionText(),
            answer.getCandidateAnswer(),
            interview.getTargetRole(),
            interview.getDifficulty().name(),
            List.copyOf(question.getEvaluationCriteria())
        );
    }

    @Transactional
    public InterviewAnswerResponse markFailed(UUID answerId) {
        InterviewAnswer answer = answerRepository.findByIdForUpdate(answerId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Answer not found: " + answerId
            ));
        if (answer.getEvaluationStatus() == EvaluationStatus.PENDING) {
            answer.failEvaluation();
        }
        return InterviewAnswerResponse.from(answer);
    }
}
