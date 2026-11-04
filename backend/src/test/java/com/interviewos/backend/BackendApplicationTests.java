package com.interviewos.backend;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.time.LocalDateTime;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;

import com.interviewos.backend.controller.AiController;
import com.interviewos.backend.controller.InterviewController;
import com.interviewos.backend.dto.InterviewAnswerResponse;
import com.interviewos.backend.dto.InterviewDetailsResponse;
import com.interviewos.backend.dto.InterviewQuestionResponse;
import com.interviewos.backend.dto.InterviewResponse;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.entity.InterviewStatus;
import com.interviewos.backend.exception.InvalidLifecycleTransitionException;
import com.interviewos.backend.exception.ResourceNotFoundException;
import com.interviewos.backend.integration.ai.QuestionGenerationRequest;
import com.interviewos.backend.integration.ai.QuestionGenerationResponse;
import com.interviewos.backend.integration.ai.GeneratedQuestion;
import com.interviewos.backend.service.InterviewService;

@WebMvcTest({AiController.class, InterviewController.class})
class BackendApplicationTests {
    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private InterviewService interviewService;

    @Test
    void generatesQuestionsThroughTheBackendEndpoint() throws Exception {
        given(interviewService.generateQuestions(any(QuestionGenerationRequest.class)))
            .willReturn(new QuestionGenerationResponse(List.of(
                new GeneratedQuestion(
                    "What is a transaction?",
                    List.of("Atomicity", "Consistency")
                )
            )));

        mockMvc.perform(post("/api/ai/questions")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "targetRole": "Backend Engineer",
                      "difficulty": "INTERMEDIATE",
                      "numberOfQuestions": 1
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.questions[0].questionText")
                .value("What is a transaction?"))
            .andExpect(jsonPath("$.questions[0].evaluationCriteria[0]").value("Atomicity"));
    }

    @Test
    void createsInterviewWithTheExistingResponseFields() throws Exception {
        UUID interviewId = UUID.randomUUID();
        given(interviewService.createInterview(
            "Backend Engineer",
            Difficulty.INTERMEDIATE,
            2
        )).willReturn(new InterviewResponse(
            interviewId,
            "Backend Engineer",
            Difficulty.INTERMEDIATE,
            2,
            InterviewStatus.CREATED,
            LocalDateTime.parse("2026-11-04T10:00:00")
        ));

        mockMvc.perform(post("/api/interviews")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "targetRole": "Backend Engineer",
                      "difficulty": "INTERMEDIATE",
                      "numberOfQuestions": 2
                    }
                    """))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.id").value(interviewId.toString()))
            .andExpect(jsonPath("$.targetRole").value("Backend Engineer"))
            .andExpect(jsonPath("$.difficulty").value("INTERMEDIATE"))
            .andExpect(jsonPath("$.numberOfQuestions").value(2))
            .andExpect(jsonPath("$.status").value("CREATED"));
    }

    @Test
    void generatesAndReturnsQuestionsForAnInterview() throws Exception {
        UUID interviewId = UUID.randomUUID();
        given(interviewService.generateQuestionsForInterview(interviewId))
            .willReturn(List.of(
                new InterviewQuestionResponse(
                    UUID.randomUUID(),
                    "Explain transactions.",
                    1
                )
            ));

        mockMvc.perform(post("/api/interviews/{interviewId}/questions", interviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].questionText").value("Explain transactions."))
            .andExpect(jsonPath("$[0].questionOrder").value(1));
    }

    @Test
    void submitsCandidateAnswerForInterviewQuestion() throws Exception {
        UUID interviewId = UUID.randomUUID();
        UUID questionId = UUID.randomUUID();
        given(interviewService.submitAnswer(
            interviewId,
            questionId,
            "A transaction groups operations."
        )).willReturn(new InterviewAnswerResponse(
            UUID.randomUUID(),
            questionId,
            "A transaction groups operations.",
            LocalDateTime.parse("2026-11-04T10:01:00")
        ));

        mockMvc.perform(post(
                "/api/interviews/{interviewId}/questions/{questionId}/answers",
                interviewId,
                questionId
            )
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"candidateAnswer":"A transaction groups operations."}
                    """))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.questionId").value(questionId.toString()))
            .andExpect(jsonPath("$.candidateAnswer")
                .value("A transaction groups operations."));
    }

    @Test
    void startsInterview() throws Exception {
        UUID interviewId = UUID.randomUUID();
        given(interviewService.startInterview(interviewId))
            .willReturn(new InterviewResponse(
                interviewId,
                "Backend Engineer",
                Difficulty.INTERMEDIATE,
                2,
                InterviewStatus.IN_PROGRESS,
                LocalDateTime.parse("2026-11-04T10:00:00")
            ));

        mockMvc.perform(post("/api/interviews/{interviewId}/start", interviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("IN_PROGRESS"));
    }

    @Test
    void retrievesInterviewDetailsAndCurrentQuestion() throws Exception {
        UUID interviewId = UUID.randomUUID();
        given(interviewService.getInterviewDetails(interviewId))
            .willReturn(new InterviewDetailsResponse(
                interviewId,
                "Backend Engineer",
                Difficulty.INTERMEDIATE,
                1,
                InterviewStatus.IN_PROGRESS,
                LocalDateTime.parse("2026-11-04T10:00:00"),
                1,
                List.of(new InterviewQuestionResponse(
                    UUID.randomUUID(),
                    "Explain transactions.",
                    1
                ))
            ));
        given(interviewService.getCurrentQuestion(interviewId))
            .willReturn(new InterviewQuestionResponse(
                UUID.randomUUID(),
                "Explain transactions.",
                1
            ));

        mockMvc.perform(get("/api/interviews/{interviewId}", interviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.currentQuestionOrder").value(1))
            .andExpect(jsonPath("$.questions[0].questionText")
                .value("Explain transactions."));
        mockMvc.perform(get(
                "/api/interviews/{interviewId}/current-question",
                interviewId
            ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.questionOrder").value(1));
    }

    @Test
    void advancesAndCompletesInterview() throws Exception {
        UUID interviewId = UUID.randomUUID();
        given(interviewService.advanceToNextQuestion(interviewId))
            .willReturn(new InterviewQuestionResponse(
                UUID.randomUUID(),
                "Second question?",
                2
            ));
        given(interviewService.completeInterview(interviewId))
            .willReturn(new InterviewResponse(
                interviewId,
                "Backend Engineer",
                Difficulty.INTERMEDIATE,
                2,
                InterviewStatus.COMPLETED,
                LocalDateTime.parse("2026-11-04T10:00:00")
            ));

        mockMvc.perform(post("/api/interviews/{interviewId}/next-question", interviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.questionOrder").value(2));
        mockMvc.perform(post("/api/interviews/{interviewId}/complete", interviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("COMPLETED"));
    }

    @Test
    void returnsConflictForInvalidLifecycleTransitionsAndNotFoundForMissingInterview()
        throws Exception {
        UUID interviewId = UUID.randomUUID();
        doThrow(new InvalidLifecycleTransitionException("Invalid transition"))
            .when(interviewService).startInterview(interviewId);
        doThrow(new ResourceNotFoundException("Interview not found"))
            .when(interviewService).completeInterview(interviewId);

        mockMvc.perform(post("/api/interviews/{interviewId}/start", interviewId))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.message").value("Invalid transition"));
        mockMvc.perform(post("/api/interviews/{interviewId}/complete", interviewId))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.message").value("Interview not found"));
    }
}
