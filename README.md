# InterviewOS

InterviewOS is an adaptive technical-interview platform. The React frontend
communicates with one Python FastAPI backend. That backend owns the API,
interview lifecycle, PostgreSQL persistence, and internal LangGraph workflows.
Ollama runs the local `qwen2.5:3b` model; it is not a second application
service.

## Architecture

- `backend/` — Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic,
  LangGraph, LangChain, and Ollama integration.
- `frontend/` — React 19, TypeScript, Vite, Tailwind CSS, Axios, and React
  Router.
- `docs/` — architecture, engineering notes, and interview preparation.
- PostgreSQL 17 — persistent interviews, questions, criteria, answers, and
  evaluations.

Question generation and answer evaluation invoke LangGraph directly in backend
services. Answers are committed with `PENDING` status before model inference;
inference runs outside database transactions. A failed evaluation keeps the
answer and records `FAILED`.

## Prerequisites

- Windows PowerShell (commands below use PowerShell syntax).
- Python 3.13.
- Node.js and npm (for the Vite frontend).
- PostgreSQL 17, either an existing local instance or Docker.
- Ollama with `qwen2.5:3b` downloaded for live AI evaluation.

## Local setup

### 1. Start PostgreSQL

Use the existing PostgreSQL instance if it already contains InterviewOS data.
Do not initialize a new database over that data. Alternatively, start the
PostgreSQL Compose profile after setting up the root `.env` as described below.

### 2. Create and configure the Python environment

```powershell
Set-Location .\backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` and set `DATABASE_URL` to the PostgreSQL database that
contains the existing InterviewOS schema. URL-encode special characters in the
database username or password. Set `OLLAMA_BASE_URL` if Ollama is not listening
at `http://localhost:11434`.

Before upgrading a database created by the Java application, set
`LEGACY_TIMESTAMP_TIMEZONE` to the timezone used by the Java host when it wrote
the old timezone-naive timestamps. The migration defaults to `UTC`; do not use
that default unless it matches the legacy data. The migration converts those
values to timezone-aware UTC instants and retains all rows.

### 3. Apply the Alembic migration

Run this from `backend/` after verifying the database URL and legacy timezone:

```powershell
alembic upgrade head
```

This migration adopts the existing JPA tables and constraints in place. It
does not drop tables or copy candidate records elsewhere. On an empty database
it creates the Python schema. SQLAlchemy `create_all()` is used only by isolated
tests, never to manage production schema.

### 4. Install Ollama and run the backend

In another PowerShell window:

```powershell
ollama pull qwen2.5:3b
ollama serve
```

Start the API from the repository root with the development script. The
`-StopExisting` switch stops only confirmed InterviewOS listeners on port 8000,
including an orphaned reload worker verified by its parent PID and the
InterviewOS health response. It refuses to stop unverified processes. The
script runs one foreground Uvicorn process with application DEBUG diagnostics
and HTTP access logging; press `Ctrl+C` in that terminal to stop it cleanly:

```powershell
.\backend\scripts\start-dev.ps1 -StopExisting
```

- Health: <http://localhost:8000/api/health>
- Swagger UI: <http://localhost:8000/docs>

The app reads `DATABASE_URL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`,
`OLLAMA_TIMEOUT_SECONDS`, and `CORS_ORIGINS` from the environment or
`backend/.env`.

### 5. Start the frontend

In another PowerShell window, from the repository root:

```powershell
Set-Location .\frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Vite serves the frontend at <http://localhost:5173>. The example
`VITE_API_BASE_URL` points to the local backend at `http://localhost:8000`;
change it in `frontend/.env.local` if the backend uses another URL.

## Docker Compose

The Compose PostgreSQL service reuses the named `interviewos-postgres-data`
volume. If this volume is not present on a fresh machine, create it first:

```powershell
docker volume create interviewos-postgres-data
Copy-Item .env.example .env
```

Edit the root `.env` and use a local-only password. **Do not start the Compose
PostgreSQL profile while another PostgreSQL container is using this same
volume.** If the existing `interviewos-postgres` container owns the volume,
keep using it or stop that container before starting the profile; do not remove
the volume.

Start the Compose-managed database and wait for it to become healthy:

```powershell
docker compose --profile postgres up -d postgres
docker compose ps
```

Build the backend image, apply the schema migration, then start the API:

```powershell
docker compose build backend
docker compose --profile postgres run --rm backend alembic upgrade head
docker compose up backend
```

Ollama remains on the host and the container uses
`http://host.docker.internal:11434`. To use an already-running host PostgreSQL
container instead, set the root `.env` `DATABASE_URL` host to
`host.docker.internal`, then build, migrate against that database, and start
only the backend service:

```powershell
docker compose build backend
docker compose run --rm backend alembic upgrade head
docker compose up backend
```

## Interview API workflow

The API uses camelCase JSON fields. Invalid requests return HTTP 400, missing
resources return 404, and invalid lifecycle transitions/conflicts return 409.

### Create an interview

```http
POST /api/interviews
Content-Type: application/json

{
  "targetRole": "Backend Engineer",
  "difficulty": "INTERMEDIATE",
  "numberOfQuestions": 2
}
```

The response contains the UUID, role, difficulty, question limit, initial
`CREATED` status, and UTC `createdAt`.

### Generate and persist questions

```http
POST /api/interviews/{interviewId}/questions
```

Returns the persisted ordered question list, including each question's
`evaluationCriteria` and `source`. Repeated calls return the existing list.

### Start, retrieve, and progress

```http
POST /api/interviews/{interviewId}/start
GET  /api/interviews/{interviewId}
GET  /api/interviews/{interviewId}/current-question
POST /api/interviews/{interviewId}/next-question
```

Only a `CREATED` interview with questions can start. Starting sets
`IN_PROGRESS` and current order 1. Current-question retrieval and progression
require `IN_PROGRESS`; the API rejects advancement beyond the final question.

### Submit an answer and evaluate it

```http
POST /api/interviews/{interviewId}/questions/{questionId}/answers
Content-Type: application/json

{"candidateAnswer": "A transaction groups operations atomically."}
```

Only the current question of an `IN_PROGRESS` interview accepts one nonblank
answer. The backend loads evaluation criteria from PostgreSQL; clients cannot
override them. The response includes evaluation status, scores, assessments,
feedback, and any suggested follow-up. If Ollama fails, the answer remains
persisted with `FAILED` status and no evaluation scores.

### Adaptive follow-ups and reporting

The backend uses a valid suggested follow-up only after a completed evaluation
when the overall score is below 7.0 or a criterion is missing/partial, follow-up
criteria are valid and nonempty, and a next question slot exists. A selected
follow-up replaces that next persisted question and preserves its order and the
configured question count.

```http
GET  /api/interviews/{interviewId}/report
POST /api/interviews/{interviewId}/complete
```

The report aggregates persisted questions and answers; it makes no additional
LLM call. Only `IN_PROGRESS` interviews can be completed.

## PowerShell API walkthrough

With the backend on port 8000 and Ollama/PostgreSQL configured:

```powershell
$base = "http://localhost:8000"
$interview = Invoke-RestMethod -Method Post -Uri "$base/api/interviews" `
  -ContentType "application/json" -Body (@{
    targetRole = "Backend Engineer"
    difficulty = "INTERMEDIATE"
    numberOfQuestions = 2
  } | ConvertTo-Json)
$id = $interview.id

$questions = Invoke-RestMethod -Method Post -Uri "$base/api/interviews/$id/questions"
Invoke-RestMethod -Method Post -Uri "$base/api/interviews/$id/start"
$current = Invoke-RestMethod -Method Get -Uri "$base/api/interviews/$id/current-question"

$answer = Invoke-RestMethod -Method Post `
  -Uri "$base/api/interviews/$id/questions/$($current.id)/answers" `
  -ContentType "application/json" `
  -Body (@{ candidateAnswer = "A transaction groups related database operations." } | ConvertTo-Json)
$answer | ConvertTo-Json -Depth 8

if ($questions.Count -gt 1) {
  $current = Invoke-RestMethod -Method Post -Uri "$base/api/interviews/$id/next-question"
  if ($current.source -eq "FOLLOW_UP") {
    Write-Output "Adaptive follow-up replaced the scheduled next question."
  } else {
    Write-Output "The scheduled next question was retained."
  }
  $answer = Invoke-RestMethod -Method Post `
    -Uri "$base/api/interviews/$id/questions/$($current.id)/answers" `
    -ContentType "application/json" `
    -Body (@{ candidateAnswer = "I would test commit and rollback behavior." } | ConvertTo-Json)
}

$report = Invoke-RestMethod -Method Get -Uri "$base/api/interviews/$id/report"
$report | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post -Uri "$base/api/interviews/$id/complete"
```

When adapting the walkthrough to a different question count, submit an answer
for each current question and advance only when a next slot remains. An adaptive
follow-up replaces the next question rather than adding one.

## Tests and verification

From `backend/`:

```powershell
python -m compileall -q app tests
python -m pytest -q
```

Tests use an isolated SQLite database and mocked LangGraph model calls. They do
not require PostgreSQL, Ollama, or network access.

From `frontend/`:

```powershell
npm ci
npm run build
npm run lint
```

There is currently no frontend test script.

## Evaluation limitations

Verbatim quote matching accepts only case and whitespace normalization and
confirms that the quote occurs in the submitted answer. It does not prove that
the quoted content semantically satisfies a criterion; semantic assessment
remains an LLM judgment. The application calculates completeness and overall
score and derives strengths, missing concepts, and feedback from validated
criterion assessments.
