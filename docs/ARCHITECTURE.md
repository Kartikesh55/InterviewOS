# InterviewOS Architecture

## Overview

InterviewOS is a modular Python monolith plus a separately deployed React
frontend. One FastAPI process owns the public API, interview business rules,
database transactions, and LangGraph orchestration. PostgreSQL is the source of
truth. Ollama runs the local model process; the backend does not make an
inter-service HTTP request for AI workflows.

## Modules

```text
backend/app/
  api/routes/       FastAPI routers and request dependency wiring
  core/             Settings and domain/API exceptions
  db/               SQLAlchemy base and session factory
  models/           SQLAlchemy entities and relationships
  schemas/          Pydantic request/response and AI draft contracts
  repositories/     ORM queries, row locks, and ordered result loading
  services/         Lifecycle, persistence, evaluation, and adaptive policy
  ai/
    graphs/         LangGraph question and evaluation graphs
    services/       LLM prompting, structured output validation, score logic
    llm.py          Environment-configured Ollama model factory
backend/alembic/    Versioned PostgreSQL schema migrations
```

API routers validate and delegate. Services own transaction boundaries and
business decisions. AI graph nodes call the Python AI services directly.

## Request and evaluation flow

1. `POST /api/interviews` validates role, difficulty, and question count, then
   creates a `CREATED` interview.
2. `POST /api/interviews/{id}/questions` checks for existing questions in a
   short locked transaction. If none exist, it commits that transaction,
   invokes question-generation LangGraph, validates the structured output, then
   opens a separate transaction to persist ordered questions and criteria.
3. Starting an interview locks the interview row, verifies questions exist,
   sets status to `IN_PROGRESS`, and sets current order to 1.
4. Answer submission locks and validates the interview/current question,
   persists a unique answer with `PENDING` status, and commits.
5. LangGraph/Ollama evaluation executes with no database transaction open. The
   request is built from the stored question, answer, role, difficulty, and
   ordered criteria.
6. On success, the backend validates quotes against the answer, recalculates
   completeness and weighted overall score, derives consistent strengths,
   missing concepts, and feedback, then persists evaluations.
7. Java-era behavior is preserved in the Python service: any selected
   follow-up replaces the next scheduled question row, reuses its order, and
   persists its criteria/source. The backend checks the score/coverage rule and
   remaining slot; the LLM cannot change interview state.
8. On evaluation failure, a short transaction marks the already-persisted
   answer `FAILED`; no scores or assessment facts are fabricated.
9. `GET /api/interviews/{id}/report` aggregates persisted results with no LLM
   call.

## Lifecycle invariants

- `CREATED -> IN_PROGRESS -> COMPLETED` is the only supported state path.
- Starting requires at least one persisted question.
- Current-question retrieval, advancing, completion, and answer submission
  require `IN_PROGRESS`.
- Row locks serialize lifecycle transitions and answer creation in PostgreSQL.
- An answer must reference the current question belonging to that interview.
- One answer is allowed per question.
- Question order is unique per interview and never exceeds the configured
  maximum. Follow-ups replace an existing next slot.

## Persistence

SQLAlchemy models map the existing Hibernate tables to preserve live data.
Ordered question criteria, answer strengths, missing concepts, and follow-up
criteria remain relational child tables. Criterion assessments are child rows
of an answer. UUID primary/foreign keys and existing uniqueness constraints
remain in place.

Alembic owns schema changes. The initial migration adopts a complete existing
JPA schema, validates expected tables/columns, adds the missing assessment
status constraint/indexes, and converts legacy naive timestamps to timezone
aware values. It rejects a partial schema rather than dropping or overwriting
data. Legacy timestamp conversion requires the original Java host timezone
through `LEGACY_TIMESTAMP_TIMEZONE`; new timestamps are UTC.

## API

- `GET /api/health`
- `POST /api/interviews`
- `GET /api/interviews/{interviewId}`
- `POST /api/interviews/{interviewId}/questions`
- `POST /api/interviews/{interviewId}/start`
- `GET /api/interviews/{interviewId}/current-question`
- `POST /api/interviews/{interviewId}/next-question`
- `POST /api/interviews/{interviewId}/questions/{questionId}/answers`
- `POST /api/interviews/{interviewId}/complete`
- `GET /api/interviews/{interviewId}/report`

Existing AI utility routes are retained for compatibility; the interview
workflow itself invokes the graphs internally. Swagger UI is available at
`/docs`.

## Reliability and limitations

AI failures leave durable answers marked `FAILED`. There is not yet a retry
endpoint. Quote validation proves only that evidence is a normalized verbatim
substring; whether it supports a concept remains LLM judgment. Follow-up
criteria are checked for structure and nonemptiness, while their semantic
relevance to the suggested question cannot be proven deterministically.
