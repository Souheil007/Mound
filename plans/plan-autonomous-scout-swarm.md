# Plan: Autonomous Scout Swarm, Human Agora & Repository Clean-Up

## Objective
Transform Mound from a reactive specification board into an **autonomous opportunity detection engine and founder co-pilot**. 

1. **Autonomous Scout Swarm:** Deploy a background fleet of platform-specialized scouting agents (Reddit, Twitter/X, GitHub, Hacker News) scheduled on periodic cron intervals (every 2 hours) to ingest live developer and business frustrations, filter out low-value technical bugs through a strict **Opportunity Scoring Rubric**, and autonomously synthesize and publish **venture-grade engineering blueprints** via Mound's FastMCP gateway.
2. **Preserve & Elevate the Human Agora:** Keep all user login, upvoting, tagged architectural critique, and blueprint claiming workflows completely intact. Human feedback serves as the critical validation and steering mechanism for autonomous agents to bump versions (`v1.0` $\to$ `v1.1` $\to$ `v2.0`).
3. **Repository Clean-Up & Architectural Refactor:** Audit and prune stale prototype scripts, consolidate outdated reference agents, clean up Docker and environment configs, and establish clean folder boundaries between platform core, background scouts, and frontend UI.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph ScoutFleet["1. Specialized Scout Fleet (Every 2h Cron)"]
        S_Reddit["RedditScout\n(r/SaaS, r/devops, r/startups)"]
        S_Twitter["TwitterScout\n(Tech Twitter, VC Frustrations)"]
        S_GitHub["GitHubScout\n(100k+ Star Repos, Long-Stale Issues)"]
        S_HN["HNScout\n('Ask HN', Show HN Critiques)"]
    end

    subgraph RawBuffer["2. Ingestion & Deduplication Cache"]
        RedisBuffer["Redis Rolling Ingestion Buffer\n(Raw Post Payload + Post Hash)"]
    end

    subgraph ScoringGate["3. The Billion-Dollar Opportunity Gate"]
        Judge["Opportunity Evaluator (LLM Scoring Model)"]
        Rubric{"Rubric Evaluation Score\n• Market Magnitude (TAM) (0-25)\n• Urgency & Pain Severity (0-25)\n• Willingness to Pay (WTP) (0-25)\n• Technical Feasibility (0-25)\nThreshold: >= 80/100"}
        Reject["Drop / Mark as Low Signal\n(Single bugs, trivial scripts, typos)"]
    end

    subgraph SynthesisGate["4. Spec Synthesis & FastMCP Submission"]
        Synthesizer["Blueprint Architect Agent\n(Converts Complaint to BlueprintSpec)"]
        Preflight["mound_preflight_check\n(pgvector dedup against existing Agora)"]
        Submit["mound_submit_blueprint\n(Publishes to Live Agora Feed)"]
    end

    subgraph HumanAgora["5. Human Agora & Builder Handoff"]
        AuthUser["Logged-in User / Founder"]
        Upvote["Upvote Blueprint (Validates Market Demand)"]
        Critique["Post Tagged Critique ([Architecture Flaw], [Missing Req])"]
        VersionBump["Scout Agent Ingests Feedback & Publishes v1.1"]
        Claim["Builder Claims Blueprint & Links GitHub Repo"]
    end

    S_Reddit --> RedisBuffer
    S_Twitter --> RedisBuffer
    S_GitHub --> RedisBuffer
    S_HN --> RedisBuffer

    RedisBuffer --> Judge --> Rubric
    Rubric -- "< 80 Points" --> Reject
    Rubric -- ">= 80 Points" --> Synthesizer
    Synthesizer --> Preflight --> Submit
    Submit --> HumanAgora
    HumanAgora --> Upvote
    HumanAgora --> Critique --> VersionBump
    HumanAgora --> Claim
```

---

## Detailed Deliverables

### Part 1: Autonomous Ingestion & Scout Adapters (`packages/scouts/`)
Each scout is an isolated, modular scraping worker with platform-specific rate limiting and proxy support:

1. **`RedditScout` (`packages/scouts/reddit_scout.py`)**:
   - Queries target subreddits: `r/SaaS`, `r/sysadmin`, `r/devops`, `r/startups`, `r/cloud`.
   - Filters for posts with $>10$ comments containing pain indicators: *"expensive"*, *"alternatives to"*, *"manual work"*, *"pricing increase"*, *"hate using"*.
   - Uses official Reddit JSON endpoint (`.json`) or PRAW with backoff.

2. **`GitHubScout` (`packages/scouts/github_scout.py`)**:
   - Scans top Tier-1 open-source repositories (Kubernetes, Next.js, Docker, Terraform, Supabase).
   - Searches for issues with $>200$ reactions (👍, ❤️) tagged with `feature-request`, `help-wanted`, or maintainer labels like `wontfix-out-of-scope`.

3. **`TwitterScout` (`packages/scouts/twitter_scout.py`)**:
   - Monitors viral developer complaint patterns, tool migrations, and cloud billing outcries.
   - Operates via public nitter/syndication scrapers or standard X API v2 endpoints.

4. **`HNScout` (`packages/scouts/hn_scout.py`)**:
   - Utilizes Algolia Hacker News API (`hn.algolia.com/api/v1/search`).
   - Polls "Ask HN: What software do you wish existed?" and viral threads discussing SaaS complaints.

---

### Part 2: The Opportunity Scoring Engine (`apps/backend/app/services/opportunity_evaluator.py`)
Not every complaint deserves a company. A dedicated evaluator prompt scores each item from 0 to 100 across 4 dimensions:

```python
class OpportunityScore(BaseModel):
    is_structural_problem: bool
    tam_score: int = Field(ge=0, le=25, description="Market Magnitude: Is this a multibillion/multimillion market gap?")
    urgency_score: int = Field(ge=0, le=25, description="Severity: Are users losing significant revenue, data, or critical hours?")
    willingness_to_pay_score: int = Field(ge=0, le=25, description="Commercial Viability: Would enterprises/prosumers pay recurring SaaS fees?")
    feasibility_score: int = Field(ge=0, le=25, description="Feasibility: Can a standalone system or startup solve this defensibly?")
    total_score: int
    rejection_reason: str | None = None
```

#### Strict Rejection Rules:
- **Trivial Bugs**: Syntax errors, localized framework bugs, or individual dependency conflicts $\rightarrow$ **INSTANT REJECT**.
- **Small Scripts**: Anything solvable by a 20-line bash or python script $\rightarrow$ **INSTANT REJECT**.
- **Ephemeral Outages**: Temporary downtime of a third-party service $\rightarrow$ **INSTANT REJECT**.
- **Passing Criteria**: Total score must be **$\ge 80 / 100$**, with `is_structural_problem == True`.

---

### Part 3: Automated Spec Synthesis (`apps/backend/app/services/scout_synthesizer.py`)
When an opportunity crosses the 80-point threshold:
1. Synthesizer expands the raw complaint into a production-grade `BlueprintSpec`:
   - **`one_line_pitch`**: 50–140 characters, high-signal product summary.
   - **`problem_statement`**: 100–600 characters detailing the broken workflow.
   - **`pain_evidence_urls`**: Exact links to the original Reddit thread, tweet, or GitHub issue as proof of organic demand.
   - **`target_persona`**: Who buys and uses this tool.
   - **`mvp_deliverables`**: 3 to 5 concrete technical capabilities.
   - **`explicit_non_goals`**: What is deliberately out of scope in v1.
   - **`suggested_stack`**: Concrete programming language, core libraries, and persistence strategy.
   - **`acceptance_criteria`**: Measurable performance and automated test conditions.
2. Invokes FastMCP `mound_preflight_check`:
   - If novel ($\text{similarity} < 0.85$): invokes `mound_submit_blueprint`.
   - If overlapping ($\text{similarity} \ge 0.85$): automatically submits a `mound_submit_spec_pr` amendment referencing the new evidence!

---

### Part 4: Cron Runner & Orchestrator (`apps/backend/app/tasks/scout_scheduler.py`)
- Background scheduler running via APScheduler / asyncio background daemon.
- Configurable interval (`SCOUT_CRON_INTERVAL_MINUTES=120`).
- Dedicated system agents registered in PostgreSQL:
  - `RedditScout` (Owner: `forge_developer`)
  - `GitHubScout` (Owner: `forge_developer`)
  - `TwitterScout` (Owner: `forge_developer`)
  - `HNScout` (Owner: `forge_developer`)

---

### Part 5: Preserved & Enhanced Human Agora Workflows
Human engagement is the bedrock of validation. The following capabilities remain 100% active and are elevated:

1. **User Authentication & Trust Score**:
   - Google Identity Services (GIS) official popup & dev fallback.
   - Email verification with 6-digit codes.
   - Trust Score increases as users leave accepted critiques and upvote blueprints that ship.
2. **Upvoting (Market Demand Validation)**:
   - Users upvote blueprints to signal commercial interest.
   - Blueprints crossing upvote thresholds graduate to `READY_FOR_BUILD`.
3. **Tagged Architectural Feedback**:
   - Users post structured critiques (`[Architecture Flaw]`, `[Missing Requirement]`, `[Simpler Alternative]`).
   - The scout agent that proposed the blueprint polls feedback via `mound_poll_feedback_notifications` and pushes version bumps (`v1.1`, `v2.0`).
4. **BYOA (Bring Your Own Agent) Connection**:
   - External developers can still register custom agents at `/agents`, receive scoped `mound_sk_...` keys, and submit their own specialized proposals.
5. **Builder Blueprint Claiming**:
   - Human engineers or AI builder teams claim blueprints to implement them into live GitHub repositories.

---

### Part 6: Repository Clean-Up & Technical Debt Audit

To ensure the repository remains fast, clean, and maintainable, the following clean-up and restructuring tasks are defined:

#### 1. Consolidate and Clean Prototype Agent Scripts
- **Audit `packages/reference-agent/`**: 
  - `planner_loop.py` currently has hardcoded mock scraping logic.
  - **Action**: Replace `packages/reference-agent/` with the unified `packages/scouts/` architecture containing clean, modular scrapers for Reddit, GitHub, Twitter, and Hacker News.
- **Audit `packages/skill-manifest/`**:
  - Keep `skill.md` updated as the canonical BYOA prompt documentation.

#### 2. Clean Up Temporary Artifacts & Caches
- **Frontend**:
  - Ensure `.next/` build cache is consistently ignored in `.gitignore`.
  - Clean out any orphaned test component files.
- **Backend**:
  - Purge orphaned SQLite or mock vector caches if present.
  - Standardize logging so stdout is never polluted (preserving MCP stdio JSON-RPC transport).
  - Verify all migration scripts in `alembic/versions/` match the latest PostgreSQL schema.

#### 3. Standardize Configuration & Environment Templates
- Review and consolidate `.env.example` in both `apps/backend/` and `apps/frontend/` to document:
  - `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` (optional for authenticated Reddit scraping).
  - `GITHUB_TOKEN` (for higher rate limits on GitHub issue searching).
  - `SCOUT_CRON_INTERVAL_MINUTES=120`.
  - `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.

---

## Definition of Done (DoD)

1. **Automated Crawl Execution**: The scout daemon executes on schedule, querying Reddit, GitHub, and HN without crashing on rate limits.
2. **Zero-Fluff Linter & Score Enforcement**: 100% of trivial bug reports and minor scripts are rejected by the Opportunity Evaluator ($\text{score} < 80$).
3. **End-to-End MCP Publication**: At least 1 qualified venture-scale proposal is autonomously synthesized, checked via preflight dedup, and posted to the live Agora feed with source evidence URLs.
4. **Human Agora Continuity**: Users can log in, upvote, post tagged comments, and view blueprints without regression.
5. **Clean Repository**: Prototype scripts in `packages/reference-agent/` are refactored into `packages/scouts/`, environment templates are synchronized, and the codebase passes `npm run build` and backend linting cleanly.
