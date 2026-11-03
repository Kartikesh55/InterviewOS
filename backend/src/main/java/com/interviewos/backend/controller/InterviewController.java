package com.interviewos.backend.controller;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.ResponseStatus;

import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.service.InterviewService;
import jakarta.validation.Valid;
@RestController
@RequestMapping("/api/interviews")
public class InterviewController
{
    private final InterviewService interviewService;

    public InterviewController(InterviewService interviewService)
    {
        this.interviewService = interviewService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Interview createInterview(@Valid @RequestBody CreateInterviewRequest request)
    {
        return interviewService.createInterview(
            request.targetRole(),
            request.difficulty(),
            request.numberOfQuestions()
        );
    }

    public record CreateInterviewRequest(
    @jakarta.validation.constraints.NotBlank(message = "Target role is required")
    String targetRole,

    @jakarta.validation.constraints.NotNull(message = "Difficulty is required")
    Difficulty difficulty,

    @jakarta.validation.constraints.NotNull(message = "Number of questions is required")
    @jakarta.validation.constraints.Min(value = 1, message = "At least 1 question is required")
    @jakarta.validation.constraints.Max(value = 20, message = "Maximum 20 questions are allowed")
    Integer numberOfQuestions
)
{
}
}