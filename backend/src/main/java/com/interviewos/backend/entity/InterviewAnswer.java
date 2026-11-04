package com.interviewos.backend.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;

@Entity
public class InterviewAnswer {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String candidateAnswer;

    @Column(nullable = false)
    private LocalDateTime submittedAt;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "interview_question_id", nullable = false)
    private InterviewQuestion interviewQuestion;

    protected InterviewAnswer() {
    }

    public InterviewAnswer(String candidateAnswer, InterviewQuestion interviewQuestion) {
        this.candidateAnswer = candidateAnswer;
        this.interviewQuestion = interviewQuestion;
        this.submittedAt = LocalDateTime.now();
    }

    public UUID getId() {
        return id;
    }

    public String getCandidateAnswer() {
        return candidateAnswer;
    }

    public LocalDateTime getSubmittedAt() {
        return submittedAt;
    }

    public InterviewQuestion getInterviewQuestion() {
        return interviewQuestion;
    }
}
