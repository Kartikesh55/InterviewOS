package com.interviewos.backend.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.interviewos.backend.entity.InterviewQuestion;

public interface InterviewQuestionRepository extends JpaRepository<InterviewQuestion, UUID> {
    List<InterviewQuestion> findByInterview_IdOrderByQuestionOrderAsc(UUID interviewId);

    Optional<InterviewQuestion> findByIdAndInterview_Id(UUID questionId, UUID interviewId);
}
