package com.interviewos.backend.integration.ai;

import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class AiServiceClient {
    private final RestClient restClient;

    public AiServiceClient(RestClient aiServiceRestClient) {
        this.restClient = aiServiceRestClient;
    }

    public QuestionGenerationResponse generateQuestions(QuestionGenerationRequest request) {
        return post(
            "/api/ai/generate-questions",
            request,
            QuestionGenerationResponse.class
        );
    }

    public AnswerEvaluationResponse evaluateAnswer(AnswerEvaluationRequest request) {
        return post(
            "/api/ai/evaluate-answer",
            request,
            AnswerEvaluationResponse.class
        );
    }

    private <T> T post(String path, Object request, Class<T> responseType) {
        try {
            T response = restClient.post()
                .uri(path)
                .body(request)
                .retrieve()
                .body(responseType);
            if (response == null) {
                throw new AiServiceException(
                    HttpStatus.BAD_GATEWAY,
                    "AI service returned an empty response",
                    null
                );
            }
            return response;
        } catch (AiServiceException exception) {
            throw exception;
        } catch (ResourceAccessException exception) {
            boolean timeout = hasTimeoutCause(exception);
            throw new AiServiceException(
                timeout ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY,
                timeout ? "AI service request timed out" : "AI service is unavailable",
                exception
            );
        } catch (RestClientResponseException exception) {
            throw new AiServiceException(
                HttpStatus.BAD_GATEWAY,
                "AI service returned HTTP " + exception.getStatusCode().value(),
                exception
            );
        } catch (RestClientException exception) {
            throw new AiServiceException(
                HttpStatus.BAD_GATEWAY,
                "AI service request failed",
                exception
            );
        }
    }

    private boolean hasTimeoutCause(Throwable throwable) {
        for (Throwable cause = throwable; cause != null; cause = cause.getCause()) {
            if (cause instanceof SocketTimeoutException
                || cause instanceof HttpTimeoutException) {
                return true;
            }
        }
        return false;
    }
}
