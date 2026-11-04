package com.interviewos.backend.controller;

import java.util.List;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.PathVariable;

import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.dto.InterviewDetailsResponse;
import com.interviewos.backend.dto.InterviewQuestionResponse;
import com.interviewos.backend.dto.InterviewResponse;
import com.interviewos.backend.dto.SubmitAnswerRequest;
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

    @GetMapping("/{interviewId}")
    public InterviewDetailsResponse getInterviewDetails(
        @PathVariable UUID interviewId
    ) {
        return interviewService.getInterviewDetails(interviewId);
    }

    @PostMapping("/{interviewId}/start")
    public InterviewResponse startInterview(@PathVariable UUID interviewId)
    {
        return interviewService.startInterview(interviewId);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public InterviewResponse createInterview(@Valid @RequestBody CreateInterviewRequest request)
    {
        return interviewService.createInterview(
            request.targetRole(),
            request.difficulty(),
            request.numberOfQuestions()
        );
    }

    @PostMapping("/{interviewId}/questions")
    public List<InterviewQuestionResponse> generateQuestions(
        @PathVariable UUID interviewId
    )
    {
        return interviewService.generateQuestionsForInterview(interviewId);
    }

    @GetMapping("/{interviewId}/current-question")
    public InterviewQuestionResponse getCurrentQuestion(
        @PathVariable UUID interviewId
    ) {
        return interviewService.getCurrentQuestion(interviewId);
    }

    @PostMapping("/{interviewId}/next-question")
    public InterviewQuestionResponse advanceToNextQuestion(
        @PathVariable UUID interviewId
    ) {
        return interviewService.advanceToNextQuestion(interviewId);
    }

    @PostMapping("/{interviewId}/complete")
    public InterviewResponse completeInterview(@PathVariable UUID interviewId)
    {
        return interviewService.completeInterview(interviewId);
    }

    @PostMapping("/{interviewId}/questions/{questionId}/answers")
    @ResponseStatus(HttpStatus.CREATED)
    public InterviewAnswerResponse submitAnswer(
        @PathVariable UUID interviewId,
        @PathVariable UUID questionId,
        @Valid @RequestBody SubmitAnswerRequest request
    ) {
        return interviewService.submitAnswer(
            interviewId,
            questionId,
            request.candidateAnswer()
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