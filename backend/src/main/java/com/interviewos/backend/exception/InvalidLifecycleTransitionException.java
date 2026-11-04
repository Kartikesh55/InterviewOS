package com.interviewos.backend.exception;

public class InvalidLifecycleTransitionException extends RuntimeException {
    public InvalidLifecycleTransitionException(String message) {
        super(message);
    }
}
