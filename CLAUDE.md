# Mound AI Instructions (Claude Code)

Please read and strictly follow the project conventions defined in:
1. [AGENT.md](./AGENT.md)
2. [STANDARDS.md](./STANDARDS.md)

### Key Rules
- **Google Docstrings**: Concise Google docstrings on all Python modules, classes, and functions (`Args:`, `Returns:`, `Raises:`).
- **Naming**: `snake_case` in Python/SQL, `kebab-case.tsx` and `camelCase` in TypeScript/React.
- **Terminology**: Use `Blueprint`, `Planning Agent`, `Builder`, and `Spec PR` (never use `cell` or `mason`).
- **Embeddings**: Local 384-dim MiniLM via FastEmbed. Zero paid cloud dependencies.
- **Commands**:
  - `make test` to run pytest.
  - `make lint` to run ruff.
  - `make infra` to launch Postgres with pgvector and Redis.
