
# InterviewOS

An adaptive AI-powered technical interview platform built to simulate realistic technical interviews, evaluate candidate responses, and generate personalized feedback.

## Overview

InterviewOS combines a Java Spring Boot backend with a Python-based AI orchestration service to deliver interactive technical interview experiences.

Candidates can configure interviews, answer dynamically generated questions, receive adaptive follow-ups, and review detailed performance reports.

Generated interview questions include persisted evaluation criteria. Answers are
saved before the backend requests an evaluation; evaluation results are stored
with a `PENDING`, `COMPLETED`, or `FAILED` status. The backend decides whether
to replace the next scheduled question with an AI-suggested follow-up. Follow-ups
reuse the next question slot and never increase the interview's configured
question limit.

## Technology Stack

- Java 24
- Spring Boot
- Python
- LangGraph
- React
- TypeScript
- PostgreSQL
- Docker

## Architecture

The application is organized into four main components:

- `backend/` – Java Spring Boot application.
- `ai-service/` – Python AI orchestration service.
- `frontend/` – React user interface.
- `docs/` – Architecture and engineering documentation.

## Current Status

🚧 Under active development.

## Planned Features

- Configurable technical interviews
- AI-generated interview questions
- Adaptive follow-up questions
- Context-aware answer evaluation
- Interview performance reports
- Interview history

## Future Enhancements

- Voice-based interviews
- Coding assessments with secure execution
- Behavioral interviews
- Advanced performance analytics

## License

To be determined.
