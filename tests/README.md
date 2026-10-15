# Mound Test Suites

This directory houses cross-cutting end-to-end (E2E) integration tests and test fixtures for the Mound platform.

---

## Structure

```
tests/
├── e2e/              # End-to-end integration tests (Docker + API + Agent + Web)
└── fixtures/         # Mock sample blueprints, pain citations, and test payloads
```

---

## Test Execution

- **Backend Unit & API Tests:**
  ```bash
  make test
  # or: cd apps/api && uv run pytest
  ```

- **Frontend Tests:**
  ```bash
  cd apps/web && npm test
  ```

- **E2E Smoke Tests:**
  ```bash
  make infra
  uv run pytest tests/e2e
  ```
