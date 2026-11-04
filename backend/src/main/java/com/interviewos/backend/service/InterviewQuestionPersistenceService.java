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
import com.interviewos.backend.integration.ai.GeneratedQuestion;
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
        List<GeneratedQuestion> generatedQuestions
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

        List<InterviewQuestion> questions = new ArrayList<>(generatedQuestions.size());
        for (int index = 0; index < generatedQuestions.size(); index++) {
            GeneratedQuestion generated = generatedQuestions.get(index);
            if (generated.questionText() == null || generated.questionText().isBlank()
                || generated.evaluationCriteria() == null
                || generated.evaluationCriteria().isEmpty()
                || generated.evaluationCriteria().stream().anyMatch(
                    criterion -> criterion == null || criterion.isBlank()
                )) {
                throw new IllegalArgumentException(
                    "Generated questions must include text and evaluation criteria"
                );
            }
            questions.add(new InterviewQuestion(
                generated.questionText(),
                index + 1,
                interview,
                generated.evaluationCriteria()
            ));
        }

        return questionRepository.saveAll(questions).stream()
            .map(InterviewQuestionResponse::from)
            .toList();
    }
}
