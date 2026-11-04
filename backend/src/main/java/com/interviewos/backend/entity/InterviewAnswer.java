package com.interviewos.backend.entity;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import jakarta.persistence.CascadeType;
import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Enumerated;
import jakarta.persistence.EnumType;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(uniqueConstraints = @UniqueConstraint(
    name = "uk_interview_answer_question",
    columnNames = "interview_question_id"
))
public class InterviewAnswer {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String candidateAnswer;

    @Column(nullable = false)
    private LocalDateTime submittedAt;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, columnDefinition = "varchar(32) default 'PENDING'")
    private EvaluationStatus evaluationStatus;

    private Double technicalAccuracy;
    private Double completeness;
    private Double clarity;
    private Double depth;
    private Double overallScore;

    @Column(columnDefinition = "TEXT")
    private String feedback;

    @Column(columnDefinition = "TEXT")
    private String suggestedFollowUp;

    @ElementCollection
    @CollectionTable(
        name = "interview_answer_strengths",
        joinColumns = @JoinColumn(name = "interview_answer_id")
    )
    @OrderColumn(name = "strength_order")
    @Column(name = "strength", nullable = false, columnDefinition = "TEXT")
    private List<String> strengths = new ArrayList<>();

    @ElementCollection
    @CollectionTable(
        name = "interview_answer_missing_concepts",
        joinColumns = @JoinColumn(name = "interview_answer_id")
    )
    @OrderColumn(name = "concept_order")
    @Column(name = "concept", nullable = false, columnDefinition = "TEXT")
    private List<String> missingConcepts = new ArrayList<>();

    @ElementCollection
    @CollectionTable(
        name = "interview_answer_follow_up_criteria",
        joinColumns = @JoinColumn(name = "interview_answer_id")
    )
    @OrderColumn(name = "criterion_order")
    @Column(name = "criterion", nullable = false, columnDefinition = "TEXT")
    private List<String> suggestedFollowUpCriteria = new ArrayList<>();

    @OneToMany(mappedBy = "answer", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<CriterionAssessment> criterionAssessments = new ArrayList<>();

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "interview_question_id", nullable = false)
    private InterviewQuestion interviewQuestion;

    protected InterviewAnswer() {
    }

    public InterviewAnswer(String candidateAnswer, InterviewQuestion interviewQuestion) {
        this.candidateAnswer = candidateAnswer;
        this.interviewQuestion = interviewQuestion;
        this.submittedAt = LocalDateTime.now();
        this.evaluationStatus = EvaluationStatus.PENDING;
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

    public EvaluationStatus getEvaluationStatus() {
        return evaluationStatus;
    }

    public Double getTechnicalAccuracy() {
        return technicalAccuracy;
    }

    public Double getCompleteness() {
        return completeness;
    }

    public Double getClarity() {
        return clarity;
    }

    public Double getDepth() {
        return depth;
    }

    public Double getOverallScore() {
        return overallScore;
    }

    public String getFeedback() {
        return feedback;
    }

    public String getSuggestedFollowUp() {
        return suggestedFollowUp;
    }

    public List<String> getStrengths() {
        return strengths;
    }

    public List<String> getMissingConcepts() {
        return missingConcepts;
    }

    public List<String> getSuggestedFollowUpCriteria() {
        return suggestedFollowUpCriteria;
    }

    public List<CriterionAssessment> getCriterionAssessments() {
        return criterionAssessments;
    }

    public void completeEvaluation(
        double technicalAccuracy,
        double completeness,
        double clarity,
        double depth,
        double overallScore,
        List<CriterionAssessment> criterionAssessments,
        List<String> strengths,
        List<String> missingConcepts,
        String feedback,
        String suggestedFollowUp,
        List<String> suggestedFollowUpCriteria
    ) {
        this.technicalAccuracy = technicalAccuracy;
        this.completeness = completeness;
        this.clarity = clarity;
        this.depth = depth;
        this.overallScore = overallScore;
        this.criterionAssessments.clear();
        this.criterionAssessments.addAll(criterionAssessments);
        this.strengths.clear();
        this.strengths.addAll(strengths);
        this.missingConcepts.clear();
        this.missingConcepts.addAll(missingConcepts);
        this.feedback = feedback;
        this.suggestedFollowUp = suggestedFollowUp;
        this.suggestedFollowUpCriteria.clear();
        this.suggestedFollowUpCriteria.addAll(suggestedFollowUpCriteria);
        this.evaluationStatus = EvaluationStatus.COMPLETED;
    }

    public void failEvaluation() {
        this.evaluationStatus = EvaluationStatus.FAILED;
    }
}
