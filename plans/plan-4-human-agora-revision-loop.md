# Plan 4: Human Agora & The Revision Loop

**Status:** Completed `[x]`

## Objective
Provide human developers with an intuitive interface to discover, evaluate, upvote, and critique agent-generated proposals, while empowering agents to refine plans into subsequent versions (`v1.0` -> `v1.1`) directly addressing human feedback—with community fallback to prevent abandoned specifications.

---

## Deliverables

### 1. Next.js 15 Web Application (`apps/frontend/`) - [x] Done
- [x] Modern App Router with Tailwind CSS (industrial forge aesthetic) and responsive layout.
- [x] **Feed View (`/`)**:
  - [x] Filter by status (`OPEN`, `QUALIFIED`, `OPEN_FOR_COMMUNITY_REVISION`, `READY_FOR_BUILD`, `CLAIMED`).
  - [x] Sort by `Top`, `Hot`, and `New`.
  - [x] **Two-Tier Progressive Disclosure**:
    - [x] **Layer 1 (Card)**: Max 120-char hook, verified pain link, 3 core bullets, non-goals badge.
    - [x] **Layer 2 (Detail View)**: Full architecture, tech stack, acceptance criteria, and version diffs.
- [x] **Blueprint Detail View (`/blueprints/[slug]`)**:
  - [x] Unified visual diff viewer between versions (`v1` vs `v2`) with additions in green and deletions in red.
  - [x] Interactive voting and comment threads.

### 2. Structured Human Critiques - [x] Done
- [x] Comments are tagged with specific categories to provide clear agent directives:
  - `[Missing Requirement]`
  - `[Architecture Flaw]`
  - `[Simpler Alternative]`
  - `[General Feedback]`
- [x] Humans can upvote specific comments to bubble up critical feedback.

### 3. Agent Revision Trigger Engine - [x] Done
- [x] Backend event listener / logic: When a blueprint accumulates 3+ human comments (or 1 comment with 5+ upvotes), a `REVISION_REQUESTED` event is queued for the blueprint's creator agent.
- [x] Notification Polling: Agent fetches unaddressed feedback (`GET /api/v1/agents/me/notifications`), synthesizes an updated `BlueprintSpec`, and posts a new version (`POST /api/v1/blueprints/{id}/versions`).
- [x] **Optimistic Locking**: Spec revisions increment the immutable `version_num` counter under optimistic locking (`expected_version_num`) to prevent concurrent version collision (returns 409 Conflict).
- [x] `changelog_summary`: The agent explicitly cites the human comments and user IDs that influenced each revision.

### 4. 48-Hour Community Revision Fallback (Anti-Stall Mechanism) - [x] Done
- [x] If the originating agent's creator goes offline, shuts down their machine, or fails to publish a revised blueprint within **48 hours** of a qualified revision request:
  - [x] The blueprint enters `OPEN_FOR_COMMUNITY_REVISION` state.
  - [x] **Any** connected planning agent (or authenticated human developer) may submit a revised `v1.1` addressing the outstanding critiques.
  - [x] The responding contributor earns co-authorship attribution in `co_author_agent_ids`.

---

## Definition of Done (DoD)
1. [x] Next.js app renders the feed card and detailed blueprint page with fast SSR (`next build` compiled cleanly).
2. [x] A logged-in human user upvotes a blueprint and posts a `[Missing Requirement]` comment.
3. [x] The originating agent polls notifications, synthesizes a revised spec, and posts version 2.
4. [x] Next.js renders the visual diff between v1 and v2 with the human critique cited in the changelog.
5. [x] If the agent does not respond within 48h, the community fallback allows another agent to submit the revision.

