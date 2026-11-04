package com.interviewos.backend.service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.interviewos.backend.dto.InterviewQuestionResponse;
import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.InterviewQuestion;
import com.interviewos.backend.exception.ResourceNotFoundException;
import com.interviewos.backend.repository.InterviewQuestionRepository;
import com.interviewos.backend.repository.InterviewRepository;

@Service
public class InterviewQuestionPersistenceService {
    private final InterviewRepository interviewRepository;
    private final InterviewQuestionRepository questionRepository;

    public InterviewQuestionPersistenceService(
        InterviewRepository interviewRepository,
        InterviewQuestionRepository questionRepository
    ) {
        this.interviewRepository = interviewRepository;
        this.questionRepository = questionRepository;
    }

    @Transactional
    public List<InterviewQuestionResponse> persistGeneratedQuestions(
        UUID interviewId,
        List<String> questionTexts
    ) {
        Interview interview = interviewRepository.findByIdForUpdate(interviewId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Interview not found: " + interviewId
            ));

        List<InterviewQuestion> existingQuestions =
            questionRepository.findByInterview_IdOrderByQuestionOrderAsc(interviewId);
        if (!existingQuestions.isEmpty()) {
            return existingQuestions.stream()
                .map(InterviewQuestionResponse::from)
                .toList();
        }

        List<InterviewQuestion> questions = new ArrayList<>(questionTexts.size());
        for (int index = 0; index < questionTexts.size(); index++) {
            questions.add(new InterviewQuestion(questionTexts.get(index), index + 1, interview));
        }

        return questionRepository.saveAll(questions).stream()
            .map(InterviewQuestionResponse::from)
            .toList();
    }
}
