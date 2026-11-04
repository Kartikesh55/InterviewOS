# InterviewOS: Technical Interview Preparation

## Architecture in one minute

InterviewOS is a modular Python monolith. FastAPI exposes the API, SQLAlchemy
repositories access PostgreSQL, services own lifecycle and persistence rules,
and LangGraph orchestrates question generation and answer evaluation inside
the same process. The React frontend is separate; Ollama provides a local
Qwen2.5 model.

## Key design decisions

### Why a modular monolith?

The application is a student MVP with one backend team and one deployment
target. In-process AI calls avoid service-to-service HTTP overhead, duplicated
contracts, and extra failure modes. Routers, schemas, repositories, services,
and AI graphs remain separated so they can be independently tested and later
extracted if scaling needs arise.

### Why persist an answer before inference?

LLM calls are slow and can time out. The backend opens a short transaction to
validate the current interview/question and persist a `PENDING` answer, commits,
and only then invokes LangGraph. A second transaction stores the evaluation or
sets `FAILED`. A model outage therefore cannot erase the candidate's answer,
and no database lock is held during inference.

### How are lifecycle races handled?

PostgreSQL `SELECT ... FOR UPDATE` locks serialize operations that transition
an interview or submit an answer. Unique constraints also enforce question
ordering and one answer per question. Lifecycle transitions are only
`CREATED -> IN_PROGRESS -> COMPLETED`.

### How does evaluation scoring work?

The model drafts dimension scores and one criterion assessment per supplied
criterion. Python checks evidence against the original answer using normalized,
case-insensitive substring matching, reconstructs the assessment list from the
stored criteria, calculates completeness, computes the weighted score, and
derives strengths, missing concepts, and feedback. Weights are 40% technical
accuracy, 30% completeness, 15% clarity, and 15% depth.

Quote presence is not semantic proof. The model's rationale and decision that a
quote demonstrates a concept remain probabilistic LLM judgments. An evaluation
failure returns no scores and no missing-concept claims.

### How does adaptation work?

The LLM can suggest a follow-up but cannot modify an interview. Python selects
it only after a completed evaluation if the overall score is below 7.0 or any
criterion is missing/partial, follow-up text and criteria are valid, and a
next slot already exists. The follow-up replaces that scheduled question and
retains its order and the interview's maximum question count.

### How is schema evolution managed?

Alembic owns production schema migrations. The first revision adopts the
existing Hibernate tables and preserves their rows. Legacy naive timestamps
must be interpreted using the Java host's timezone before conversion to UTC;
future timestamps are timezone-aware UTC values.

## Data model

- `Interview` owns ordered `InterviewQuestion` rows and stores lifecycle state,
  question limit, and current question order.
- `InterviewQuestion` stores source (`GENERATED`/`FOLLOW_UP`) and ordered
  relational evaluation criteria.
- `InterviewAnswer` belongs to one question and stores answer text, evaluation
  status, scores, feedback, strengths, missing concepts, and suggested
  follow-up data.
- `CriterionAssessment` belongs to an answer and stores the original
  criterion, status, and evidence.

## API workflow

Create interview, generate/persist questions, start, fetch current question,
submit its answer, review evaluation, advance if a slot remains, and complete.
`GET /api/interviews/{id}/report` returns stored interview, question, answer,
and evaluation data without a new model call.

## Known limitations

- Semantic correctness, quote relevance, and follow-up relevance are not
  deterministically provable.
- Failed evaluations are durable but have no retry endpoint.
- There is no authentication or authorization yet.
- The project uses a local model and has no model-provider fallback.
- SQLite tests do not exercise PostgreSQL row-lock behavior; PostgreSQL
  integration/runtime checks are separate.
