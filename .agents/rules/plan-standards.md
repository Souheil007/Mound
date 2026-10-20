# Agent Rule: Mound Engineering Plan Standards

This repository enforces strict, uniform plan conventions inside the `plans/` directory.

## 1. File Naming Convention
- **Pattern**: `plan-XX-<kebab-case-topic>.md`
- **Prefix**: `plan-` followed by a **2-digit zero-padded number** (`01`, `02`, ..., `99`).
- **Examples**:
  - `plan-01-core-backbone-spec-contract.md`
  - `plan-06-autonomous-scout-swarm.md`
  - `plan-09-webhook-event-bus.md`
- **Rule**: Never create unnumbered plan files (e.g. `plan-my-feature.md`) or single-digit numbers (`plan-1.md`).

## 2. Document Structure
All plan files must include:
1. `# Plan XX: <Title>`
2. `**Status:** Completed [x]` / `In Progress [ ]` / `Upcoming [ ]`
3. `## Objective`
4. `## Deliverables` (with structured checkboxes)
5. `## Definition of Done (DoD)`

## 3. Maintenance & Pruning
- When code or architectural decisions are pruned or retired, immediately update or delete corresponding plans so they never document ghost/dead architectures.
- Keep `plans/README.md` updated as the single source of truth index.
