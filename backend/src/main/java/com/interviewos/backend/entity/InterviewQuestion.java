package com.interviewos.backend.entity;

import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
    uniqueConstraints = @UniqueConstraint(
        name = "uk_interview_question_order",
        columnNames = {"interview_id", "question_order"}
    )
)
public class InterviewQuestion {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "question_text", nullable = false, columnDefinition = "TEXT")
    private String questionText;

    @Column(name = "question_order", nullable = false)
    private Integer questionOrder;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "interview_id", nullable = false)
    private Interview interview;

    protected InterviewQuestion() {
    }

    public InterviewQuestion(String questionText, Integer questionOrder, Interview interview) {
        this.questionText = questionText;
        this.questionOrder = questionOrder;
        this.interview = interview;
    }

    public UUID getId() {
        return id;
    }

    public String getQuestionText() {
        return questionText;
    }

    public Integer getQuestionOrder() {
        return questionOrder;
    }

    public Interview getInterview() {
        return interview;
    }
}
