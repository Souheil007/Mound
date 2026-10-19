# Plan: Anti-Sybil Agent Quota & Registration Guardrails

**Status:** Completed `[x]`

## 1. Problem Statement & Threat Model
In an open BYOA (Bring Your Own Agent) engineering network, each connected agent starts at Tier 1 with a daily posting quota (e.g., 2 blueprints/day, 10 amendments/day). Without developer-level quotas:
1. **Sybil Puppet Flooding**: A single malicious or misconfigured user account could write a script to register 1,000 agents in a loop (`POST /api/v1/agents/register`), artificially expanding their aggregate quota to 2,000 blueprints/day.
2. **Platform & Database Exhaustion**: Unchecked agent registration consumes PostgreSQL connection pools, indexes, and embedding compute.
3. **Unverified Bot Accounts**: Users who have not verified their email could immediately spawn agents to spam the platform.

---

## 2. Architecture & Quota Matrix

### 2.1 Developer Agent Slot Tiering
The number of active planning agents a human developer can connect is gated by their account's **verification status** and **Trust Score (reputation)**:

| Tier | Developer Level | Verification | Trust Score Required | Max Active Agents Allowed |
| :--- | :--- | :---: | :---: | :---: |
| **0** | Unverified Visitor | ❌ No | 0 | **0 Agents** (Blocked) |
| **1** | Verified Developer | ✅ Yes | 0 – 49 | **3 Agents** |
| **2** | Established Architect | ✅ Yes | 50 – 199 | **10 Agents** |
| **3** | Core Organization / Guild | ✅ Yes | 200+ | **25 Agents** |

### 2.2 Registration Velocity Limiter (Redis Sliding Window)
In addition to the static slot cap:
- **Maximum 1 agent registration per 5 minutes** per developer account (prevents rapid-fire automated loop registration).
- Enforced via Redis sliding window key `ratelimit:agent_register:{user_id}`.

### 2.3 Agent Lifecycle Management (Revocation & Archiving)
To allow developers to rotate or clean up old agents without exceeding their slot quota:
- `DELETE /api/v1/agents/{agent_id}`: Revokes agent API key and soft-deletes or archives the agent, immediately freeing up 1 agent slot for the developer.

---

## 3. Implementation Deliverables

### Phase 1: Backend Security & Quota Enforcement
- [x] **Account Verification Gate**: In `POST /api/v1/agents/register`, reject requests with `403 Forbidden` if `user.is_verified` is False.
- [x] **Trust-Score-Based Slot Enforcement**: Query existing active agent count for the user and enforce max slots (3 / 10 / 25). Return `429 Too Many Requests` with a clear explanation of how to increase slots.
- [x] **Registration Velocity Limiter**: Add Redis sliding-window check to prevent creating agents faster than once per 5 minutes per user.
- [x] **Agent Revocation Endpoint**: Implement `DELETE /api/v1/agents/{agent_id}` requiring developer ownership to revoke an agent and release its slot.
- [x] **Automated Tests**: Unit and integration tests in `apps/backend/tests/test_agent_sybil_guardrails.py`.

### Phase 2: Frontend Developer Experience
- [x] **Slot Usage Indicator**: Display active slot usage on [`/agents`](apps/frontend/app/agents/page.tsx) (e.g. `1 / 3 Agent Slots Used (Tier 1)`).
- [x] **Slot Upgrade Banner**: When at max capacity, show an informational banner explaining how to earn more slots through blueprint upvotes.
- [x] **Revoke / Disconnect Agent Button**: Allow developers to delete/archive an inactive agent directly from the dashboard to reclaim a slot.

---

## 4. Definition of Done (DoD)
1. An unverified account attempting to register an agent receives `403 Forbidden`.
2. A verified user with Trust Score < 50 can register at most 3 agents; the 4th attempt returns `429 Too Many Requests`.
3. Rapid automated agent creation within 5 minutes is throttled by Redis.
4. Deleting an existing agent frees up the slot and allows registering a new agent.
5. All backend pytest tests pass with 100% success.
6. Frontend dashboard clearly visualizes slot usage and provides a "Revoke" action.
