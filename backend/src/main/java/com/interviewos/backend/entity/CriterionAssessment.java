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

@Entity
public class CriterionAssessment {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String criterion;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String evidence;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "interview_answer_id", nullable = false)
    private InterviewAnswer answer;

    protected CriterionAssessment() {
    }

    public CriterionAssessment(
        String criterion,
        String status,
        String evidence,
        InterviewAnswer answer
    ) {
        this.criterion = criterion;
        this.status = status;
        this.evidence = evidence == null ? "" : evidence;
        this.answer = answer;
    }

    public String getCriterion() {
        return criterion;
    }

    public String getStatus() {
        return status;
    }

    public String getEvidence() {
        return evidence;
    }
}
