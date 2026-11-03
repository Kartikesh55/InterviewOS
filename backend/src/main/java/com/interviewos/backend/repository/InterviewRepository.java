package com.interviewos.backend.repository;

import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.interviewos.backend.entity.Interview;

public interface InterviewRepository extends JpaRepository<Interview, UUID>
{
}