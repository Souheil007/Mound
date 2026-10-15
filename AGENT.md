# Mound Agent Guidelines

Welcome, AI Agent! You are working on **Mound**: a crowdsourced AI engineering forge where autonomous planning agents discover developer pain points, propose versioned specifications (**Blueprints**), humans curate and refine them, and developers (**Builders**) turn them into shipped software.

---

## 1. Prime Directive: Strictly Enforce STANDARDS.md

You MUST read and adhere to [STANDARDS.md](./STANDARDS.md) at all times:
- **Docstrings**: Use **Google Style Docstrings** for all Python modules, classes, and functions. Keep them **short, concise, and high-signal** (`Args:`, `Returns:`, `Raises:`).
- **Naming Conventions**:
  - Python: `snake_case` for files, functions, variables, and database tables/columns. `PascalCase` for classes, models, and exceptions. `SCREAMING_SNAKE_CASE` for constants.
  - TypeScript: `kebab-case.tsx` for files, `PascalCase` for React components/types, `camelCase` for functions and variables.
  - API JSON keys: Strict `snake_case` matching Pydantic schemas.
- **Typing**: Mandatory 100% type annotations in Python (3.12+) and strict mode in TypeScript.

---

## 2. Monorepo Map

- `apps/backend/`: FastAPI backend (async SQLAlchemy 2.0, pgvector, Redis, FastMCP).
  - `app/routers/v1/`: HTTP endpoints & FastMCP SSE gateway.
  - `app/core/`: Configuration (`config.py`), security, and Redis rate limiting.
  - `app/models/`: Database tables (Alembic managed).
  - `app/schemas/`: Pydantic input/output contracts (e.g. `blueprint_spec.py`).
  - `app/services/`: Business logic (MiniLM embedding engine, dedup, spec linter, kit compiler).
  - `tests/`: Pytest test suite.
- `apps/web/`: Next.js 15 (App Router) Human Agora UI.
- `packages/skill-manifest/`: Drop-in `skill.md` and MCP manifest for external agents.
- `packages/reference-agent/`: Python starter and Day-1 seed agent loop.
- `docker/`: `docker-compose.yml` for PostgreSQL 16 (pgvector) and Redis 7.
- `plans/`: Master technical roadmap (Plan 1 through Plan 6).
- `tests/`: Root-level cross-cutting E2E tests and mock fixtures.

---

## 3. Essential Workflows

Always use the root `Makefile` for routine operations:
- `make infra` - Boot PostgreSQL 16 (`pgvector`) & Redis 7.
- `make dev` - Start FastAPI in auto-reload mode on port 8000.
- `make lint` - Run `ruff check .` and `ruff format --check .`.
- `make test` - Run the test suite via pytest.
- `make db-migrate` - Run Alembic database migrations.

---

## 4. Architectural Guardrails

1. **Deterministic Quality Gates**: External agent inputs are untrusted. Always validate payloads through strict Pydantic schemas before persistence.
2. **Local Zero-Cost Embeddings**: Embeddings are generated locally using `sentence-transformers/all-MiniLM-L6-v2` (384 dims) via FastEmbed. Never introduce paid cloud embedding API dependencies into the core path.
3. **No Metaphor Creep in Code**: Use plain technical terminology in code and database schemas: `blueprints` (not `cells`), `agents` (not `scouts`), `builders` (not `masons`), and `spec_pr` (not `amendment`).
