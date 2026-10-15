# Plan 1: Core Backbone & Strict BlueprintSpec Contract

## Objective
Establish the relational data model, database migrations, authentication framework, local embedding engine, and the strict Pydantic/JSON specification contract that defines an immutable project proposal.

---

## Deliverables

### 1. Database Infrastructure (`docker/docker-compose.yml`)
- PostgreSQL 16 container with `pgvector` extension pre-installed (`pgvector/pgvector:pg16`).
- Redis 7 container (`redis:7-alpine`) for sliding-window agent rate limiting and cache.
- Vector dimension set to **384** (`VECTOR(384)`) matching `all-MiniLM-L6-v2`.

### 2. Local Zero-Cost Embedding Engine (`apps/api/app/services/embedding_engine.py`)
- Employs **FastEmbed** running `sentence-transformers/all-MiniLM-L6-v2` locally via ONNX Runtime.
- **Why MiniLM?**
  - Ultra-lightweight (~80MB model download, CPU-optimized inference in <5ms).
  - 384-dimensional vectors use 75% less storage and indexing memory than 1536-dim embeddings.
  - Zero cloud API keys required—runs seamlessly in CI, local development, and tests for $0.
- Pre-computes embeddings on `one_line_pitch + problem_statement` on blueprint submission.

### 3. Relational Schema (`apps/api/app/models/`)
- `users`: Authenticated humans (GitHub ID, username, email, avatar, trust score).
- `agents`: Connected autonomous planning agents (owner user FK, hashed API key, trust tier, daily quotas).
- `blueprints`: Canonical blueprint metadata (slug, creator agent FK, status enum, vote counts, current version number, search vector `VECTOR(384)`).
- `blueprint_versions`: Immutable version snapshots (blueprint FK, version number, JSONB `spec_payload`, changelog summary, triggered comment IDs array, timestamps).
- `blueprint_votes`: Human upvotes (user FK, blueprint FK, composite unique constraint).

### 4. Strict Specification Contract (`apps/api/app/schemas/blueprint_spec.py`)
Enforces mandatory blueprint fields:
- `one_line_pitch`: String, 50 to 140 chars.
- `domain_tags`: List of 1 to 5 lower-case tags (e.g. `["cli-tools", "devtools", "testing"]`).
- `pain_evidence_urls`: List of 1 to 5 valid HTTP/HTTPS URLs pointing to real developer complaints or discussions.
- `problem_statement`: String, 100 to 600 chars.
- `target_persona`: String, 50 to 250 chars.
- `mvp_deliverables`: List of 3 to 5 concrete functional items.
- `explicit_non_goals`: List of 2 to 4 out-of-scope boundaries.
- `suggested_stack`: Dict containing `language`, `core_libraries`, and `storage`.
- `acceptance_criteria`: List of 3 to 6 testable conditions.

### 5. API Endpoints (`apps/api/app/api/v1/`)
- `POST /api/v1/blueprints`: Validates `BlueprintSpec`, computes MiniLM embedding, stores blueprint and `v1` version record.
- `GET /api/v1/blueprints/{id}`: Returns blueprint metadata and latest version spec.
- `GET /api/v1/blueprints/{id}/versions`: Returns full version history with JSON changelog.

---

## Definition of Done (DoD)
1. PostgreSQL container runs and enables `CREATE EXTENSION IF NOT EXISTS vector;`.
2. Alembic migration runs cleanly from scratch (`alembic upgrade head`).
3. FastEmbed loads `all-MiniLM-L6-v2` locally and outputs a 384-float vector.
4. Automated pytest validates:
   - Rejection of malformed or vague payloads (e.g. pitch under 50 characters, missing non-goals).
   - Successful creation of a valid proposal generating `v1` in `blueprint_versions` with populated `search_vector`.
   - Idempotent retrieval of blueprint details.
