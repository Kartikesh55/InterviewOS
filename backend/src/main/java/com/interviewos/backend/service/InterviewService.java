package com.interviewos.backend.service;

import org.springframework.stereotype.Service;

import com.interviewos.backend.entity.Interview;
import com.interviewos.backend.entity.Difficulty;
import com.interviewos.backend.repository.InterviewRepository;

@Service
public class InterviewService
{
    private final InterviewRepository interviewRepository;

    public InterviewService(InterviewRepository interviewRepository)
    {
        this.interviewRepository = interviewRepository;
    }

    public Interview createInterview(String targetRole, Difficulty difficulty, Integer numberOfQuestions)
    {
        Interview interview = new Interview(targetRole, difficulty, numberOfQuestions);

        return interviewRepository.save(interview);
    }
}