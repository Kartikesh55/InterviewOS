# Engineering Notes

## Modular monolith over backend microservices

InterviewOS has one Python backend. Interview APIs, business rules, database
access, and AI orchestration share a process and explicit module boundaries.
This keeps deployment, debugging, and local development small while retaining
separation among routers, schemas, ORM entities, repositories, services, and
LangGraph workflows. The React frontend remains a separate application.

Question and evaluation graphs are called as Python services, not through an
internal HTTP client. This removes service-to-service timeouts and duplicated
API contracts while retaining structured model output and workflow isolation.

## Transaction boundaries and durable answers

No SQL transaction remains open while Ollama is generating or evaluating:

1. Lock and validate interview/question; persist the answer as `PENDING`;
   commit.
2. Invoke the local LangGraph evaluation.
3. In a new transaction, persist evaluation fields or mark the answer `FAILED`.

This makes the answer durable if the model times out or returns malformed
output. PostgreSQL row locks protect concurrent lifecycle/answer operations;
uniqueness constraints enforce one answer per question and one question order
per interview. A failed evaluation does not fabricate a score and currently
requires manual follow-up; an evaluation retry API is not implemented.

## Adaptive follow-up policy

The LLM proposes a follow-up question and criteria, but Python decides whether
to use it. Selection requires a completed evaluation, nonblank follow-up,
nonempty valid criteria, an existing next question slot, and either overall
score below 7.0 or at least one `MISSING`/`PARTIALLY_COVERED` assessment. The
backend replaces the next question row and its ordered criteria, labels it
`FOLLOW_UP`, preserves order, and never increases the configured question
count. If another request has already advanced the interview while inference
was running, the follow-up is not applied.

## Evaluation score and evidence safeguards

Completeness is calculated from validated criterion assessments:

- `COVERED = 1.0`
- `PARTIALLY_COVERED = 0.5`
- `MISSING = 0.0`

The score is points / criteria * 10. Overall is technical accuracy 40%,
completeness 30%, clarity 15%, and depth 15%, rounded to two decimals. Strengths,
missing concepts, and feedback are derived from the validated assessments.

Evidence checking accepts only case-insensitive, normalized-whitespace
verbatim matches. This verifies quote presence but **cannot prove semantic
support**. The rationale and meaning of an answer remain LLM judgments.

## Database schema migration

Alembic is the only production schema manager. The baseline revision detects
and adopts the existing JPA schema rather than attempting to recreate tables.
It validates expected table/column presence and refuses incomplete schemas.
Existing rows and relations are retained. The timestamp migration interprets
existing timezone-naive Java values using `LEGACY_TIMESTAMP_TIMEZONE`, then
stores timezone-aware UTC timestamps. New Python timestamps are UTC. Confirm
the legacy host timezone before applying the migration to a database with
existing records.

The live database previously used Hibernate `ddl-auto=update`; it has no
Alembic revision. The first Alembic upgrade records the adoption revision and
applies only the explicitly reviewed type/constraint/index changes. The
downgrade intentionally retains tables and rows because it cannot know which
tables predated the migration.

## Configuration and runtime

`DATABASE_URL`, Ollama base URL/model/timeout, legacy timezone, and CORS origins
are read from environment settings. `.env.example` files contain placeholders
only. PostgreSQL Compose reuses the existing named Docker volume; do not run
two PostgreSQL servers against the same volume at once. Inside Docker, Ollama
is reached through `host.docker.internal`.

## Testing approach

Automated tests use an isolated in-memory SQLite database and mocked structured
LLM responses. They verify API contracts, transactions, persistence,
validation, lifecycle conflicts, scoring safeguards, failure durability, and
follow-up replacement without needing Ollama or external network access.
