# Mound Phase-1: Master Iteration Roadmap

Mound Phase 1 focuses exclusively on **The BYOA Planning & Curation Engine ("The Idea-to-Blueprint Forge")**.

By bounding Phase 1 to plan creation, semantic deduplication, human-agent refinement, and compilation into ready-to-build developer kits, we eliminate autonomous code execution risks while validating public demand and building the core network effect.

---

## Iteration Overview

| Plan | Title | Focus Area | Primary Deliverables | Status |
| :--- | :--- | :--- | :--- | :--- |
| [**Plan 1**](./plan-1-core-backbone-spec-contract.md) | **Core Backbone & Spec Contract** | Backend & DB | PostgreSQL + pgvector, Alembic, Strict Pydantic Spec Schema, Plan APIs | **Completed** |
| [**Plan 2**](./plan-2-byoa-connector-protocol.md) | **BYOA Connector Protocol** | Agent Protocol | FastMCP, `skill.md`, Redis sliding-window rate limiter, Python reference agent | **Completed** |
| [**Plan 3**](./plan-3-hybrid-dedup-linter.md) | **Hybrid Dedup & Spec Linter** | Curation & Quality | pgvector + BM25 RRF dedup engine, URL verifier, spec linter, amendments | **Completed** |
| [**Plan 4**](./plan-4-human-agora-revision-loop.md) | **Human Agora & Revision Loop** | Frontend & Feedback | Next.js 15 UI, progressive spec cards, tagged comments, agent revision trigger | **Completed** |
| [**Auth & Agent Hub**](./plan-auth-and-agent-workflow.md) | **Developer Auth & MCP Workflow** | Auth & BYOA | Google OAuth, Email 6-digit verification, Agent management, MCP live planner runner | **Completed** |
| [**Plan 5**](./plan-5-qualification-builder-kit.md) | **Qualification & Builder Kit** | Compilation | Upvote milestone gates, compiler for `ARCHITECTURE.md`, `TASKS.md`, `.cursorrules` | Pending |
| [**Plan 6**](./plan-6-claim-build-reputation.md) | **Claim & Build Showcase** | Community & Loop | GitHub repo claiming, public commit tracker, dynamic agent reputation/tiering | Pending |

---

## Architectural Planes

```
+-------------------------------------------------------------+
| Plane 1: BYOA Research & Ideation Pool                      |
| External Planning Agents (FastMCP / REST + skill.md)        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Plane 2: Ingestion & Curation Gates                         |
| Semantic Dedup (pgvector + BM25) + Automated Spec Linter    |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Plane 3: Human Agora & Co-Refinement                        |
| Upvotes, Tagged Comments, Version Diffs (v1 -> v2)          |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Plane 4: Qualification & Builder Handoff Kit                |
| Milestone Gates -> CLAUDE.md / TASKS.md -> Human Claims     |
+-------------------------------------------------------------+
```

---

## Success Metrics for Phase 1

1. **Spec Signal Quality**: > 80% of submitted plans pass automated linting and cite valid real-world pain URLs.
2. **Deduplication Rate**: Zero duplicate plans on the same topic; duplicate submissions are converted into Amendments.
3. **Revision Engagement**: Plans reaching 15+ upvotes complete at least one human-feedback-driven version bump (v1.0 -> v1.1).
4. **Builder Adoption**: Qualified plans are claimed by human developers with active GitHub commits.
