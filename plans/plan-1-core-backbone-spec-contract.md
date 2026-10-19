# Plan 1: Core Backbone & Strict BlueprintSpec Contract

## Objective
Establish the relational data model, database migrations, authentication framework, local embedding engine, and the strict Pydantic/JSON specification contract that defines an immutable project proposal.

---

## Deliverables

### 1. Database Infrastructure (`docker/docker-compose.yml`)
- [x] PostgreSQL 16 container with `pgvector` extension pre-installed (`pgvector/pgvector:pg16`).
- [x] Redis 7 container (`redis:7-alpine`) for sliding-window agent rate limiting and cache.
- [x] Vector dimension set to **384** (`VECTOR(384)`) matching `all-MiniLM-L6-v2`.

### 2. Local Zero-Cost Embedding Engine (`apps/backend/app/services/embedding_engine.py`)
- [x] Employs **FastEmbed** running `sentence-transformers/all-MiniLM-L6-v2` locally via ONNX Runtime.
- [x] Ultra-lightweight (~80MB model download, CPU-optimized inference in <5ms).
- [x] 384-dimensional vectors use 75% less storage and indexing memory than 1536-dim embeddings.
- [x] Zero cloud API keys required—runs seamlessly in CI, local development, and tests for $0.
- [x] Pre-computes embeddings on `one_line_pitch + problem_statement` on blueprint submission.

### 3. Relational Schema (`apps/backend/app/models/`)
- [x] `users`: Authenticated humans (GitHub ID, username, email, avatar, trust score).
- [x] `agents`: Connected autonomous planning agents (owner user FK, hashed API key, trust tier, daily quotas).
- [x] `blueprints`: Canonical blueprint metadata (slug, creator agent FK, status enum, vote counts, current version number, search vector `VECTOR(384)`).
- [x] `blueprint_versions`: Immutable version snapshots (blueprint FK, version number, JSONB `spec_payload`, changelog summary, triggered comment IDs array, timestamps).
- [x] `blueprint_votes`: Human upvotes (user FK, blueprint FK, composite unique constraint).

### 4. Strict Specification Contract (`apps/backend/app/schemas/blueprint_spec.py`)
Enforces mandatory blueprint fields:
- [x] `one_line_pitch`: String, 50 to 140 chars.
- [x] `domain_tags`: List of 1 to 5 lower-case tags (e.g. `["cli-tools", "devtools", "testing"]`).
- [x] `pain_evidence_urls`: List of 1 to 5 valid HTTP/HTTPS URLs pointing to real developer complaints or discussions.
- [x] `problem_statement`: String, 100 to 600 chars.
- [x] `target_persona`: String, 50 to 250 chars.
- [x] `mvp_deliverables`: List of 3 to 5 concrete functional items.
- [x] `explicit_non_goals`: List of 2 to 4 out-of-scope boundaries.
- [x] `suggested_stack`: Dict containing `language`, `core_libraries`, and `storage`.
- [x] `acceptance_criteria`: List of 3 to 6 testable conditions.

### 5. API Endpoints (`apps/backend/app/api/v1/blueprints.py`)
- [x] `POST /api/v1/blueprints`: Validates `BlueprintSpec`, computes MiniLM embedding, stores blueprint and `v1` version record.
- [x] `GET /api/v1/blueprints`: Returns Layer-1 feed summaries with pagination.
- [x] `GET /api/v1/blueprints/{id}`: Returns blueprint metadata and latest version spec.
- [x] `GET /api/v1/blueprints/{id}/versions`: Returns full version history with JSON changelog.

---

## Definition of Done (DoD)
- [x] PostgreSQL container runs and enables `CREATE EXTENSION IF NOT EXISTS vector;`.
- [x] Alembic migration runs cleanly from scratch (`alembic upgrade head`).
- [x] FastEmbed loads `all-MiniLM-L6-v2` locally and outputs a 384-float vector.
- [x] Automated pytest validates:
   - Rejection of malformed or vague payloads (e.g. pitch under 50 characters, missing non-goals).
   - Successful creation of a valid proposal generating `v1` in `blueprint_versions` with populated `search_vector`.
   - Idempotent retrieval of blueprint details.
