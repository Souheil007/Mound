# Plan 5: Qualification Gates & Deterministic Builder Kit Compiler

## Objective
Prevent the "Upvoted Graveyard" trap. When a community-refined blueprint achieves critical qualification criteria, automatically compile the winning specification into an actionable, downloadable "Builder Handoff Kit" using a deterministic template engine so developers can build immediately in Cursor, Claude Code, or Windsurf.

---

## Deliverables

### 1. Milestone Qualification Gates
State transition rules from `OPEN` to `QUALIFIED`:
- Configurable vote threshold (e.g., 15 upvotes for MVP cohort, scaling to 100+).
- Requirement: Must have at least 1 revision bump (`v1` -> `v2` or higher) proving iterative improvement.
- Requirement: Zero unresolved `[Architecture Flaw]` comments with 3+ upvotes.
- Automatic transition: Once all criteria are met, status updates to `QUALIFIED` and triggers the Compiler Service.

### 2. Deterministic Template Compiler (`apps/api/app/services/kit_compiler.py`)
Rather than relying on expensive, slow, non-deterministic LLM inference to compile handoff files, Mound uses a **Jinja2 deterministic template compiler** that runs in 5ms for $0:
- **`ARCHITECTURE.md`**:
  - Automatically synthesizes project layout, module boundaries, database schemas, and API endpoint contracts directly from the validated `BlueprintSpec`.
- **`TASKS.md`**:
  - Generates a sequential, dependency-ordered checklist of 5 to 8 atomic implementation tasks with verifiable acceptance criteria for each step (also serves as Phase-2's DAG blueprint).
- **`AI_CODING_PROMPT.md` / `.cursorrules` / `CLAUDE.md`**:
  - Turnkey system instructions with strict architectural boundaries, explicit non-goals, and coding rules that any developer can copy-paste into an AI editor to begin coding immediately with zero context loss.

### 3. Builder Kit Export UI (`apps/web/src/components/builder-kit-modal.tsx`)
- One-click copy buttons for `.cursorrules`, `CLAUDE.md`, and `TASKS.md`.
- "Download Complete Starter Zip" packaging the spec, markdown guides, and repo scaffolding.
- Updates blueprint status to `READY_FOR_BUILD`.

---

## Definition of Done (DoD)
1. A blueprint crossing the vote and revision threshold triggers the compiler service.
2. The compiler renders `ARCHITECTURE.md`, `TASKS.md`, and `.cursorrules` in < 10ms with zero LLM API dependency.
3. The Next.js UI displays the "Ready for Build" badge and unlocks the Builder Handoff Kit modal.
