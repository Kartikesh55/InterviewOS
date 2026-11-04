package com.interviewos.backend.repository;

import java.util.UUID;

import jakarta.persistence.LockModeType;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.interviewos.backend.entity.InterviewAnswer;

public interface InterviewAnswerRepository extends JpaRepository<InterviewAnswer, UUID> {
    boolean existsByInterviewQuestion_Id(UUID questionId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select answer from InterviewAnswer answer where answer.id = :id")
    java.util.Optional<InterviewAnswer> findByIdForUpdate(@Param("id") UUID id);
}
