package com.interviewos.backend.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Column;
import jakarta.persistence.Enumerated;
import jakarta.persistence.EnumType;
import jakarta.persistence.OneToMany;
import jakarta.persistence.CascadeType;
import java.util.ArrayList;
import java.util.List;

@Entity
public class Interview
{
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String targetRole;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Difficulty difficulty;

    @Column(nullable = false)
    private Integer numberOfQuestions;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private InterviewStatus status;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column
    private Integer currentQuestionOrder;

    @OneToMany(mappedBy = "interview", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<InterviewQuestion> questions = new ArrayList<>();

    public Interview()
    {
    }

    public Interview(String targetRole, Difficulty difficulty, Integer numberOfQuestions)
    {
        this.targetRole = targetRole;
        this.difficulty = difficulty;
        this.numberOfQuestions = numberOfQuestions;
        this.status = InterviewStatus.CREATED;
        this.createdAt = LocalDateTime.now();
    }

    public UUID getId()
    {
        return id;
    }

    public String getTargetRole()
    {
        return targetRole;
    }

    public Difficulty getDifficulty()
    {
        return difficulty;
    }

    public Integer getNumberOfQuestions()
    {
        return numberOfQuestions;
    }

    public InterviewStatus getStatus()
    {
        return status;
    }

    public LocalDateTime getCreatedAt()
    {
        return createdAt;
    }

    public List<InterviewQuestion> getQuestions()
    {
        return questions;
    }

    public Integer getCurrentQuestionOrder()
    {
        return currentQuestionOrder;
    }

    public void start()
    {
        if (status != InterviewStatus.CREATED) {
            throw new IllegalStateException("Only CREATED interviews can be started");
        }
        status = InterviewStatus.IN_PROGRESS;
        currentQuestionOrder = 1;
    }

    public void advanceQuestion(int questionCount)
    {
        if (status != InterviewStatus.IN_PROGRESS) {
            throw new IllegalStateException("Only IN_PROGRESS interviews can advance");
        }
        if (currentQuestionOrder == null || currentQuestionOrder >= questionCount) {
            throw new IllegalStateException("There is no next question");
        }
        currentQuestionOrder++;
    }

    public void complete()
    {
        if (status != InterviewStatus.IN_PROGRESS) {
            throw new IllegalStateException("Only IN_PROGRESS interviews can be completed");
        }
        status = InterviewStatus.COMPLETED;
    }
}