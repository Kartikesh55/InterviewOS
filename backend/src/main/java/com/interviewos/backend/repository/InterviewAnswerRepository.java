package com.interviewos.backend.repository;

import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.interviewos.backend.entity.InterviewAnswer;

public interface InterviewAnswerRepository extends JpaRepository<InterviewAnswer, UUID> {
}
