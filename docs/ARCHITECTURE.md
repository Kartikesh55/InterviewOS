
# InterviewOS – System Architecture

## 1. Project Overview

InterviewOS is an adaptive AI-powered technical interview platform.
It simulates technical interviews, evaluates candidate responses,
generates adaptive follow-up questions, and provides performance reports.

## 2. Technology Stack

- Frontend: React, TypeScript, Tailwind CSS
- Backend: Java, Spring Boot
- AI Service: Python, LangGraph
- Database: PostgreSQL
- Containerization: Docker

## 3. System Components

### Frontend
Responsible for:
- Dashboard and interview configuration
- Interview interaction interface
- Displaying questions and collecting answers
- Showing evaluation reports

### Backend
Responsible for:
- Interview session management
- Business logic and validation
- REST API endpoints
- Persistent data management
- Communication with the AI service
- Lifecycle transitions, answer evaluation persistence, and deterministic
  follow-up selection

### AI Service
Responsible for:
- Generating interview questions
- Evaluating candidate responses
- Maintaining AI workflow context
- Suggesting follow-up questions and their evaluation criteria

### Database
PostgreSQL will store:
- Interview sessions
- Questions, relational evaluation criteria, and candidate responses
- Evaluation results
- Interview reports

## 4. High-Level Request Flow

1. Candidate configures an interview through the frontend.
2. Frontend sends a request to the Spring Boot backend.
3. Backend validates the request and creates an interview session.
4. Backend communicates with the Python AI service.
5. AI service generates the initial interview question.
6. Backend persists the relevant session data.
7. Frontend displays the question.
8. Candidate submits an answer for the current question.
9. Backend persists the answer as `PENDING`, then calls the AI service outside
   a database transaction.
10. Backend persists the evaluation as `COMPLETED` or records `FAILED` while
    retaining the candidate answer.
11. Backend applies its score/criterion/remaining-slot policy. A selected
    follow-up replaces the next scheduled question; Python never changes
    lifecycle state or question order.
12. The process repeats until the interview is completed.

## 5. Architectural Principles

- Separation of concerns
- Single source of truth for persistent application state
- Clear API contracts between services
- Backend-controlled interview state transitions
- Modular and maintainable design
- Durable answer capture before external evaluation

## 6. Future Enhancements

- Voice-based interviews
- Secure code execution
- Behavioral interview simulations
- Advanced analytics
- Authentication and authorization
- Improved concurrency and recovery handling
