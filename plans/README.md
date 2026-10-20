# Mound Master Iteration Roadmap & Plan Standards

Mound transforms software ideation from a reactive proposal board into an **autonomous opportunity detection engine and crowdsourced engineering forge**.

---

## 1. Master Plan Index

All engineering plans follow a standardized, zero-padded chronological ordering (`plan-01` to `plan-08`).

| Plan | Title | Focus Area | Primary Deliverables | Status |
| :--- | :--- | :--- | :--- | :---: |
| [**Plan 01**](./plan-01-core-backbone-spec-contract.md) | **Core Backbone & Strict BlueprintSpec Contract** | Backend & DB | PostgreSQL 16 + pgvector, Alembic, FastEmbed MiniLM, Pydantic Spec Schema | **Completed `[x]`** |
| [**Plan 02**](./plan-02-byoa-connector-protocol.md) | **BYOA Connector Protocol & FastMCP Gateway** | Agent Protocol | FastMCP SSE server (`/mcp`), `skill.md`, Redis sliding-window limiter | **Completed `[x]`** |
| [**Plan 03**](./plan-03-hybrid-dedup-linter.md) | **Hybrid Semantic Deduplication & Spec Linter Gate** | Curation & Quality | Two-tier vector dedup (pgvector), live URL verification, fluff/script linter, Amendments | **Completed `[x]`** |
| [**Plan 04**](./plan-04-human-agora-revision-loop.md) | **Human Agora & The Revision Loop** | Frontend & Feedback | Next.js 15 Agora feed, progressive cards, tagged critiques (`[Architecture Flaw]`), 48h community revision fallback | **Completed `[x]`** |
| [**Plan 05**](./plan-05-developer-auth-and-mcp-studio.md) | **Developer Authentication & FastMCP Studio** | Auth & BYOA | Google OAuth, Email 6-digit verification, Developer API Key generation & Cursor/Claude snippets | **Completed `[x]`** |
| [**Plan 06**](./plan-06-autonomous-scout-swarm.md) | **Autonomous Scout Swarm & Opportunity Engine** | Autonomous Swarm | 2h cron scouts (Reddit, HN, GitHub), 4-tier rate hardening, Billion-$ Rubric ($\ge 75$ pts), `/agents` live telemetry & sweep triggers | **Completed `[x]`** |
| [**Plan 07**](./plan-07-qualification-builder-kit.md) | **Qualification Gates & Deterministic Builder Kit Compiler** | Compilation (Phase 2) | Milestone qualification gates, Jinja2 template engine compiling `ARCHITECTURE.md`, `TASKS.md`, `.cursorrules`, `CLAUDE.md` | **Upcoming `[ ]`** |
| [**Plan 08**](./plan-08-verified-builder-claims.md) | **Verified Builder Claims, Live Repo Telemetry & Shipped Showcase** | Builder Loop (Phase 2) | GitHub repo claim verification (`POST /api/v1/blueprints/{id}/claim`), challenge file anti-spoofing, activity poller, shipped showcase | **Upcoming `[ ]`** |

---

## 2. Architectural Planes

```
+---------------------------------------------------------------------------------+
| Plane 1: Autonomous Ingestion Fleet & External BYOA Research Pool               |
| Background 2h Swarm (Reddit, HN, GitHub) + FastMCP External Agents (Claude/Cursor)|
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| Plane 2: Curation & The Billion-Dollar Opportunity Gate                         |
| Rubric Evaluator (>= 75 pts) + Two-Tier Vector Dedup (pgvector) + Spec Linter   |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| Plane 3: Human Agora & Co-Refinement Loop                                       |
| Community Upvotes, Tagged Critiques ([Architecture Flaw]), Version Bumps (v1->v2)|
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| Plane 4: Milestone Qualification & Deterministic Builder Handoff                |
| State Gates -> Jinja2 Kit Compiler (CLAUDE.md, TASKS.md) -> Verified Claims     |
+---------------------------------------------------------------------------------+
```

---

## 3. Plan Naming & Engineering Standards for Agents & Developers

To ensure consistent project tracking, maintainability, and clean tooling integration, all future plans created by AI agents or human contributors **must strictly conform** to the following standard:

### 3.1 File Naming Convention
- **Format**: `plan-XX-<kebab-case-topic>.md`
- **Prefix**: `plan-` followed by a **two-digit, zero-padded integer** (`01`, `02`, ..., `99`).
- **Slug**: Concise, hyphen-separated description of the core capability (e.g. `plan-09-webhook-event-bus.md`).
- **Forbidden**: Unnumbered names (e.g. `plan-feature.md`), single-digit prefixes (`plan-1.md`), or uppercase letters (`Plan-01.md`).

### 3.2 Mandatory Document Sections
Every plan must include the following structural sections:
1. **Title Header**: `# Plan XX: <Descriptive Title>`
2. **Status Badge**: `**Status:** Completed [x]` or `**Status:** In Progress [ ]` or `**Status:** Upcoming (Phase 2) [ ]`
3. **`## Objective`**: A concise 2 to 4 sentence executive summary of what problem this plan solves and why it matters.
4. **`## Deliverables`**: Subdivided into concrete numbered subsections detailing database models, backend API routes, UI components, and background tasks.
5. **`## Definition of Done (DoD)`**: A measurable checklist of acceptance criteria (e.g., test suite pass rates, performance benchmarks, and UI flows).

### 3.3 Plan Lifecycle & Deletion Policy
- **Living Plans**: When a plan is actively being implemented, checkboxes (`- [x]`) must be updated in real time.
- **Obsolete / Dead Features**: If a feature or architecture direction is retired or pruned (e.g. dead mock code, deprecated quota models), the corresponding plan must be either updated to remove the dead scope or deleted entirely if the whole plan is no longer relevant. Do not leave ghost plans describing deprecated systems.
