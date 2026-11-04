package com.interviewos.backend.exception;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.interviewos.backend.integration.ai.AiServiceException;

@RestControllerAdvice
public class GlobalExceptionHandler
{
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ValidationErrorResponse> handleValidationErrors(
        MethodArgumentNotValidException exception)
    {
        List<String> errors = exception.getBindingResult()
            .getFieldErrors()
            .stream()
            .map(error -> error.getDefaultMessage())
            .toList();

        ValidationErrorResponse response = new ValidationErrorResponse(
            "Validation failed",
            errors
        );

        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(response);
    }

    @ExceptionHandler(AiServiceException.class)
    public ResponseEntity<ValidationErrorResponse> handleAiServiceErrors(
        AiServiceException exception)
    {
        ValidationErrorResponse response = new ValidationErrorResponse(
            exception.getMessage(),
            List.of()
        );

        return ResponseEntity.status(exception.getStatus()).body(response);
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ValidationErrorResponse> handleNotFound(
        ResourceNotFoundException exception)
    {
        ValidationErrorResponse response = new ValidationErrorResponse(
            exception.getMessage(),
            List.of()
        );

        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
    }

    public record ValidationErrorResponse(
        String message,
        List<String> errors
    )
    {
    }
}