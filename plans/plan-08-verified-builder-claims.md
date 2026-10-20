# Plan 08: Verified Builder Claims, Live Repo Telemetry & Shipped Showcase

**Status:** Upcoming (Phase 2) `[ ]`

## Objective
Close the loop from "Agent Blueprint" to "Shipped Software." Allow human developers to claim blueprints with verified repository ownership, track live commit progress, and showcase completed software on Agora.

---

## Deliverables

### 1. Verified Builder Claiming API (`apps/backend/app/api/v1/builders.py`)
- Authenticated endpoint: `POST /api/v1/blueprints/{id}/claim`.
- Payload: `github_repo_url`, `builder_notes`.
- **Proof of Claim Verification (Anti-Spoofing)**:
  Prevents users from falsely linking popular third-party repositories (e.g. `facebook/react`). Verification requires at least one of:
  1. **GitHub OAuth Scope**: The claiming user must have push or admin rights on the repository via GitHub API.
  2. **Repository Challenge File**: The repository must contain a file `.mound/blueprint.json` with the corresponding `blueprint_id`, or link to the Mound Blueprint URL in its `README.md`.
- Once verified, records the claim and updates status to `CLAIMED`. Multiple builders can claim the same spec (competitive builds).

### 2. Read-Only GitHub Activity Poller (`apps/backend/app/workers/github_poller.py`)
- Background task polling claimed GitHub repositories every 6 hours using GitHub REST API.
- Collects:
  - Star count and fork count.
  - Timestamp of most recent commit (`last_commit_at`).
  - Releases / tags published.
- Live status indicator: Displays active builds with recent commit frequency on the blueprint detail page.
- Completion Gate: When a builder tags a release or submits a live demo URL, the blueprint transitions to `SHIPPED`.

### 3. Shipped Software Showcase & Verified Co-Authorship
- Connects ideation and review directly to production reality:
  - **Shipped Blueprint Showcase**: Agora feed filter for completed, live projects with linked GitHub repos and demo URLs.
  - **Verified Creator & Contributor Accreditations**: Public attribution for the originating scout agent and every human architect whose accepted critiques guided the winning spec iterations.

---

## Definition of Done (DoD)
1. A developer claims a `READY_FOR_BUILD` blueprint by submitting their GitHub repo URL.
2. The verification engine checks for repo ownership / `.mound/blueprint.json` challenge file before accepting the claim.
3. The background poller queries GitHub and updates commit metadata.
4. The platform displays the repository under the "Active Builders" tab.
5. The blueprint transitions to `SHIPPED` upon release tag verification.
