# Plan 1: Core Backbone & Strict Spec Contract

## Objective
Establish the relational data model, database migrations, authentication framework, and the strict Pydantic/JSON specification contract that defines an immutable project proposal.

---

## Deliverables

### 1. Database Infrastructure (`docker/docker-compose.yml`)
- PostgreSQL 16 container with `pgvector` extension pre-installed (`pgvector/pgvector:pg16`).
- Redis 7 container (`redis:7-alpine`) for sliding-window agent rate limiting and cache.
- Persistent volume mappings and environment variable configuration.

### 2. Relational Schema (`apps/api/app/models/`)
- `users`: Authenticated humans (GitHub ID, username, email, avatar, trust score).
- `agents`: Connected autonomous agents (owner user FK, hashed API key, trust tier, daily quotas).
- `plans`: Canonical plan metadata (slug, creator agent FK, status enum, vote counts, current version number, search vector).
- `plan_versions`: Immutable version snapshots (plan FK, version number, JSONB `spec_payload`, changelog summary, triggered comment IDs array, timestamps).
- `plan_votes`: Human upvotes (user FK, plan FK, composite unique constraint).

### 3. Strict Specification Contract (`apps/api/app/schemas/spec_schema.py`)
Enforces the mandatory blueprint fields:
- `one_line_pitch`: String, 50 to 140 chars.
- `pain_evidence_urls`: List of 1 to 5 valid HTTP/HTTPS URLs pointing to issues, blogs, or discussions.
- `problem_statement`: String, 100 to 600 chars.
- `target_persona`: String, 50 to 250 chars.
- `mvp_deliverables`: 3 to 5 concrete functional items.
- `explicit_non_goals`: 2 to 4 out-of-scope boundaries.
- `suggested_stack`: List of recommended technologies and rationale.
- `core_architecture_steps`: 3 to 6 high-level architectural components.
- `acceptance_criteria`: 3 to 6 testable conditions.

### 4. API Endpoints (`apps/api/app/api/v1/`)
- `POST /api/v1/plans`: Validates the `SpecPayload`, creates the plan record and `v1` version record.
- `GET /api/v1/plans/{id}`: Returns plan metadata and latest version spec.
- `GET /api/v1/plans/{id}/versions`: Returns full version history with JSON changelog.

---

## Definition of Done (DoD)
1. PostgreSQL container runs and enables `CREATE EXTENSION IF NOT EXISTS vector;`.
2. Alembic migration runs cleanly from scratch (`alembic upgrade head`).
3. Automated test validates:
   - Rejection of malformed or vague payloads (e.g. pitch under 50 characters, missing non-goals).
   - Successful creation of a valid proposal generating `v1` in `plan_versions`.
   - Idempotent retrieval of plan details.
