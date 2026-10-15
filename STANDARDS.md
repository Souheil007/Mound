# Mound Engineering Standards & Conventions

This document defines the strict engineering standards, naming conventions, docstring styles, and architectural principles for the Mound repository.

---

## 1. Naming Conventions

Consistency across languages and layers is mandatory. Follow these rules without exception:

| Layer / Context | Convention | Example | Notes |
| :--- | :--- | :--- | :--- |
| **Python Files & Dirs** | `snake_case` | `spec_linter.py`, `core/rate_limit.py` | Descriptive, no abbreviations unless standard |
| **Python Classes & Enums** | `PascalCase` | `SpecPayload`, `PlanStatus`, `DedupEngine` | Nouns or noun phrases |
| **Python Functions & Methods** | `snake_case` | `compute_similarity()`, `verify_lease()` | Verb-first action names |
| **Python Variables & Fields** | `snake_case` | `trust_tier`, `created_at`, `plan_id` | Match database column names |
| **Python Constants** | `SCREAMING_SNAKE_CASE` | `MAX_DAILY_PROPOSALS`, `DEFAULT_TTL` | Defined at module or class level |
| **Database Tables & Columns** | `snake_case` | `plan_versions`, `upvotes_count` | Plural table names, singular column names |
| **API Request/Response JSON** | `snake_case` | `{"one_line_pitch": "...", "plan_id": "..."}` | Kept consistent with backend models |
| **TypeScript / TSX Files** | `kebab-case` | `plan-card.tsx`, `spec-diff-viewer.tsx` | All React components and helper files |
| **TypeScript Components** | `PascalCase` | `PlanCard`, `SpecDiffViewer` | Match export name |
| **TypeScript Functions / Vars** | `camelCase` | `fetchPlanById`, `isLoading` | Verb-first for functions |
| **TypeScript Types & Interfaces**| `PascalCase` | `PlanVersion`, `AgentManifest` | Do not prefix with `I` (e.g. no `IPlan`) |
| **Git Branches** | `kebab-case` | `feature/plan-1-schema`, `fix/rate-limit-leak` | Type prefix + short description |

---

## 2. Python Documentation: Google Style Docstrings

All Python modules, classes, and public functions must include **Google Style Docstrings**.
Keep them **short, concise, and high-signal**. Do not write redundant restatements of parameter names.

### Function Docstring Format
```python
def check_semantic_similarity(
    source_vector: list[float],
    target_vector: list[float],
    metric: str = "cosine",
) -> float:
    """Computes the similarity score between two embedding vectors.

    Args:
        source_vector: Embedded representation of the candidate spec.
        target_vector: Embedded representation of an existing plan spec.
        metric: Distance metric to apply ('cosine' or 'l2').

    Returns:
        A float between 0.0 and 1.0 indicating similarity.

    Raises:
        ValueError: If vector lengths do not match or metric is unsupported.
    """
```

### Module Docstring Format
Place at the top of every `.py` file to describe its single responsibility:
```python
"""Hybrid deduplication engine combining pgvector cosine distance and BM25 full-text search."""
```

### Class Docstring Format
```python
class SpecLinter:
    """Validates submitted project specifications against quality and safety rubrics."""
```

---

## 3. Architecture & Code Quality Principles

### Strict Typing Everywhere
- **Backend**: Python 3.12+ type hints are required on all function arguments and returns. Pydantic v2 / SQLModel models define data boundaries.
- **Frontend**: TypeScript in strict mode. No `any` types allowed without explicit review comments.

### Async by Default for I/O
- All FastAPI route handlers, database queries (SQLAlchemy async engine), Redis operations, and external HTTP calls must use `async`/`await`.

### Separation of Concerns
1. **Schemas (`schemas/`)**: Pure Pydantic data validation and serialization.
2. **Models (`models/`)**: Database tables and relationships (SQLAlchemy / SQLModel).
3. **Services (`services/`)**: Business logic (deduplication, linting, kit compilation). Keep route handlers thin.
4. **API Endpoints (`api/v1/`)**: Request parsing, dependency injection, and HTTP response mapping.

### Failure Isolation & Determinism
- Autonomous agents are untrusted clients: validate all input through strict schemas.
- External URLs must be verified for reachability with strict timeouts (max 3 seconds).
- Background workers must be idempotent and fault-tolerant.
