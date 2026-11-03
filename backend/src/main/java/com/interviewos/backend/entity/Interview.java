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
}