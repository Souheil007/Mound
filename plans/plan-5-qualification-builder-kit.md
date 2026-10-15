# Plan 5: Qualification Gates & The "Builder Handoff Kit" Compiler

## Objective
Prevent the "Upvoted Graveyard" trap. When a community-refined plan achieves critical qualification criteria, automatically compile the winning specification into an actionable, downloadable "Builder Handoff Kit" so human developers can scaffold and build it immediately with AI tools like Cursor, Claude Code, or Windsurf.

---

## Deliverables

### 1. Milestone Qualification Gates
State transition rules from `OPEN` to `QUALIFIED`:
- Configurable vote threshold (e.g., 15 upvotes for MVP cohort, scaling to 100+).
- Requirement: Must have at least 1 revision bump (`v1` -> `v2` or higher) proving iterative improvement.
- Requirement: Zero unresolved `[Architecture Flaw]` comments with 3+ upvotes.
- Automatic transition: Once all criteria are met, status updates to `QUALIFIED` and queues the Kit Compiler.

### 2. Builder Kit Compiler Service (`apps/api/app/services/kit_compiler.py`)
Converts the structured `spec_payload` JSON into ready-to-run developer assets:
- **`ARCHITECTURE.md`**: Complete directory layout, module roles, database schema definitions (DDL / SQLModel), and API endpoint specifications.
- **`TASKS.md`**: A sequential, dependency-ordered checklist of 5 to 8 atomic implementation steps with verifiable acceptance criteria for each step (also serves as the Phase-2 DAG blueprint).
- **`AI_CODING_PROMPT.md` / `.cursorrules` / `CLAUDE.md`**: Pre-configured system instructions that developers can drop directly into their AI editor to initialize the project with zero context loss.

### 3. Builder Kit Export UI (`apps/web/src/components/builder-kit-modal.tsx`)
- One-click copy buttons for `.cursorrules`, `CLAUDE.md`, and `TASKS.md`.
- "Download Complete Starter Zip" button packaging the spec, markdown guides, and repo scaffolding.
- Updates plan status to `READY_FOR_BUILD`.

---

## Definition of Done (DoD)
1. A plan crossing the vote and revision threshold triggers the compiler worker.
2. The generated `ARCHITECTURE.md` and `TASKS.md` contain accurate, detailed guidelines derived from the plan's `spec_payload`.
3. The Next.js UI displays the "Ready for Build" badge and unlocks the Builder Handoff Kit modal.
