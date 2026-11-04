package com.interviewos.backend.repository;

import java.util.UUID;

import jakarta.persistence.LockModeType;

import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.interviewos.backend.entity.Interview;

public interface InterviewRepository extends JpaRepository<Interview, UUID>
{
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select interview from Interview interview where interview.id = :id")
    java.util.Optional<Interview> findByIdForUpdate(@Param("id") UUID id);
}