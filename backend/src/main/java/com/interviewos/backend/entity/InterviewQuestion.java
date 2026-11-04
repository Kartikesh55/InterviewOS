package com.interviewos.backend.entity;

import java.util.UUID;
import java.util.ArrayList;
import java.util.List;

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
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Enumerated;
import jakarta.persistence.EnumType;

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

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, columnDefinition = "varchar(32) default 'GENERATED'")
    private QuestionSource source = QuestionSource.GENERATED;

    @ElementCollection
    @CollectionTable(
        name = "interview_question_criteria",
        joinColumns = @JoinColumn(name = "interview_question_id")
    )
    @OrderColumn(name = "criterion_order")
    @Column(name = "criterion", nullable = false, columnDefinition = "TEXT")
    private List<String> evaluationCriteria = new ArrayList<>();

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "interview_id", nullable = false)
    private Interview interview;

    protected InterviewQuestion() {
    }

    public InterviewQuestion(String questionText, Integer questionOrder, Interview interview) {
        this(questionText, questionOrder, interview, List.of());
    }

    public InterviewQuestion(
        String questionText,
        Integer questionOrder,
        Interview interview,
        List<String> evaluationCriteria
    ) {
        this.questionText = questionText;
        this.questionOrder = questionOrder;
        this.interview = interview;
        this.evaluationCriteria = new ArrayList<>(evaluationCriteria);
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

    public QuestionSource getSource() {
        return source;
    }

    public List<String> getEvaluationCriteria() {
        return evaluationCriteria;
    }

    public void replaceWithFollowUp(String questionText, List<String> evaluationCriteria) {
        this.questionText = questionText;
        this.source = QuestionSource.FOLLOW_UP;
        this.evaluationCriteria.clear();
        this.evaluationCriteria.addAll(evaluationCriteria);
    }
}
