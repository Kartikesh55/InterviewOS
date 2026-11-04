package com.interviewos.backend.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.interviewos.backend.integration.ai.QuestionGenerationRequest;
import com.interviewos.backend.integration.ai.QuestionGenerationResponse;
import com.interviewos.backend.service.InterviewService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/ai")
public class AiController {
    private final InterviewService interviewService;

    public AiController(InterviewService interviewService) {
        this.interviewService = interviewService;
    }

    @PostMapping("/questions")
    public QuestionGenerationResponse generateQuestions(
        @Valid @RequestBody QuestionGenerationRequest request
    ) {
        return interviewService.generateQuestions(request);
    }
}
