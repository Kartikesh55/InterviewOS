package com.interviewos.backend;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;

import com.interviewos.backend.controller.AiController;
import com.interviewos.backend.integration.ai.QuestionGenerationRequest;
import com.interviewos.backend.integration.ai.QuestionGenerationResponse;
import com.interviewos.backend.service.InterviewService;

@WebMvcTest(AiController.class)
class BackendApplicationTests {
    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private InterviewService interviewService;

    @Test
    void generatesQuestionsThroughTheBackendEndpoint() throws Exception {
        given(interviewService.generateQuestions(any(QuestionGenerationRequest.class)))
            .willReturn(new QuestionGenerationResponse(List.of("What is a transaction?")));

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
            .andExpect(jsonPath("$.questions[0]").value("What is a transaction?"));
    }
}
