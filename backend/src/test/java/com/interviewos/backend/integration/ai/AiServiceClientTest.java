package com.interviewos.backend.integration.ai;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class AiServiceClientTest {
    private MockRestServiceServer server;
    private AiServiceClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder()
            .baseUrl("http://localhost:8000");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new AiServiceClient(builder.build());
    }

    @Test
    void generatesQuestionsUsingPythonRequestAndResponseContract() {
        server.expect(requestTo("http://localhost:8000/api/ai/generate-questions"))
            .andExpect(method(HttpMethod.POST))
            .andExpect(content().contentType(APPLICATION_JSON))
            .andExpect(content().json("""
                {
                  "targetRole": "Backend Engineer",
                  "difficulty": "INTERMEDIATE",
                  "numberOfQuestions": 2
                }
                """, true))
            .andRespond(withSuccess("""
                {"questions":["What is a transaction?","Explain indexing."]}
                """, APPLICATION_JSON));

        QuestionGenerationResponse response = client.generateQuestions(
            new QuestionGenerationRequest("Backend Engineer", "INTERMEDIATE", 2)
        );

        assertEquals(
            List.of("What is a transaction?", "Explain indexing."),
            response.questions()
        );
        server.verify();
    }

    @Test
    void evaluatesAnswersUsingPythonRequestAndResponseContract() {
        server.expect(requestTo("http://localhost:8000/api/ai/evaluate-answer"))
            .andExpect(method(HttpMethod.POST))
            .andExpect(content().json("""
                {
                  "question": "Explain indexing.",
                  "candidateAnswer": "An index speeds up lookup.",
                  "targetRole": "Backend Engineer",
                  "difficulty": "INTERMEDIATE",
                  "evaluationCriteria": ["Index lookup"]
                }
                """, true))
            .andRespond(withSuccess("""
                {
                  "technicalAccuracy": 8.0,
                  "completeness": 7.5,
                  "clarity": 8.0,
                  "depth": 7.0,
                  "overallScore": 7.7,
                  "criterionAssessments": [
                    {
                      "criterion": "Index lookup",
                      "status": "COVERED",
                      "evidence": "speeds up lookup"
                    }
                  ],
                  "strengths": ["Index lookup"],
                  "missingConcepts": [],
                  "feedback": "Good explanation.",
                  "suggestedFollowUp": null
                }
                """, APPLICATION_JSON));

        AnswerEvaluationResponse response = client.evaluateAnswer(
            new AnswerEvaluationRequest(
                "Explain indexing.",
                "An index speeds up lookup.",
                "Backend Engineer",
                "INTERMEDIATE",
                List.of("Index lookup")
            )
        );

        assertEquals(7.7, response.overallScore());
        assertEquals("COVERED", response.criterionAssessments().getFirst().status());
        assertEquals("speeds up lookup", response.criterionAssessments().getFirst().evidence());
        assertEquals("Good explanation.", response.feedback());
        assertEquals(null, response.suggestedFollowUp());
        server.verify();
    }

    @Test
    void mapsUnsuccessfulPythonResponsesToBadGateway() {
        server.expect(requestTo("http://localhost:8000/api/ai/generate-questions"))
            .andRespond(withServerError());

        AiServiceException exception = assertThrows(
            AiServiceException.class,
            () -> client.generateQuestions(
                new QuestionGenerationRequest("Backend Engineer", "INTERMEDIATE", 2)
            )
        );

        assertEquals(HttpStatus.BAD_GATEWAY, exception.getStatus());
        assertEquals("AI service returned HTTP 500", exception.getMessage());
        server.verify();
    }

    @Test
    void mapsTimeoutsToGatewayTimeout() throws Exception {
        server.expect(requestTo("http://localhost:8000/api/ai/generate-questions"))
            .andRespond(withException(new SocketTimeoutException("timed out")));

        AiServiceException exception = assertThrows(
            AiServiceException.class,
            () -> client.generateQuestions(
                new QuestionGenerationRequest("Backend Engineer", "INTERMEDIATE", 2)
            )
        );

        assertEquals(HttpStatus.GATEWAY_TIMEOUT, exception.getStatus());
        assertEquals("AI service request timed out", exception.getMessage());
        server.verify();
    }

    @Test
    void mapsConnectionFailuresToBadGateway() throws Exception {
        server.expect(requestTo("http://localhost:8000/api/ai/generate-questions"))
            .andRespond(withException(new ConnectException("connection refused")));

        AiServiceException exception = assertThrows(
            AiServiceException.class,
            () -> client.generateQuestions(
                new QuestionGenerationRequest("Backend Engineer", "INTERMEDIATE", 2)
            )
        );

        assertEquals(HttpStatus.BAD_GATEWAY, exception.getStatus());
        assertEquals("AI service is unavailable", exception.getMessage());
        server.verify();
    }
}
