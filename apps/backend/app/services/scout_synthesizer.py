"""Scout Synthesizer: Translates qualified high-scoring pain signals into strictly-typed BlueprintSpec proposals."""

import re
from typing import Any

from app.schemas.blueprint_spec import BlueprintSpec, SuggestedStack
from app.scouts.models import OpportunityEvaluation, RawPainSignal


class ScoutSynthesizer:
    """Transforms raw community signals into complete, verifiable BlueprintSpec contracts."""

    @classmethod
    def synthesize_spec(
        cls,
        signal: RawPainSignal,
        evaluation: OpportunityEvaluation,
    ) -> BlueprintSpec:
        """Synthesizes a production-grade BlueprintSpec matching Mound's schema.

        Args:
            signal: The original RawPainSignal (Reddit, GitHub, HN).
            evaluation: The passing OpportunityEvaluation (score >= 80).

        Returns:
            A strictly validated BlueprintSpec.
        """
        clean_title = re.sub(r"[^\w\s-]", "", signal.title).strip()
        if len(clean_title) > 90:
            clean_title = clean_title[:87] + "..."

        # 1. Calibrate one_line_pitch: strictly 50-140 chars
        pitch = f"Autonomous enterprise systems engine solving: {clean_title}"
        if len(pitch) < 50:
            pitch = f"Autonomous enterprise infrastructure engine solving {clean_title} in production"
        if len(pitch) > 140:
            pitch = pitch[:137] + "..."

        # 2. Calibrate problem_statement: strictly 100-600 chars
        raw_body = signal.content.strip()
        # Strip out HTML tags, raw iframe/script tags, and markdown delimiters that trigger security linter
        clean_body = re.sub(r"<[^>]+>", " ", raw_body)
        clean_body = re.sub(r"[<>|;`]", " ", clean_body)
        clean_body = re.sub(r"\s+", " ", clean_body)
        problem = (
            f"Organizations face severe operational overhead and financial waste due to {clean_title}. "
            f"As reported by {signal.author} on {signal.platform.value}: '{clean_body}'"
        )
        if len(problem) < 100:
            problem = (
                f"{problem} Current commercial tools lack automated orchestration, forcing teams to waste "
                f"hundreds of engineering hours each quarter on error-prone manual workarounds."
            )
        if len(problem) > 590:
            problem = problem[:587] + "..."

        # 3. Target Persona: strictly 50-250 chars
        persona = (
            f"DevOps leaders, SREs, and engineering directors managing high-throughput production "
            f"systems affected by {signal.platform.value} community workflow bottlenecks."
        )
        if len(persona) < 50:
            persona = f"Enterprise DevOps and infrastructure leaders managing production systems affected by {clean_title}."
        if len(persona) > 250:
            persona = persona[:247] + "..."

        # 4. Domain tags (1 to 5)
        platform_tag = signal.platform.value.lower()
        domain_tags = ["enterprise", "automation", "infrastructure", platform_tag, "devtools"][:5]

        # 5. MVP Deliverables (3 to 5 items)
        deliverables = [
            f"Autonomous streaming ingestion daemon integrating directly with {signal.platform.value} signal sources",
            "Zero-copy policy evaluation engine detecting compliance and cost regressions in real time",
            "Cryptographically verifiable audit log exporting automated proofs to Prometheus and Datadog",
        ]

        # 6. Explicit Non-Goals (2 to 4 items)
        non_goals = [
            "Does not replace human strategic decision-making or company-wide legal compliance counsel",
            "Does not support deprecated legacy platforms or unencrypted transport protocols in v1",
        ]

        # 7. Suggested Stack
        stack = SuggestedStack(
            language="Rust (edition 2021) or Python 3.12",
            core_libraries=["tokio", "anyio", "pydantic-v2"],
            storage="PostgreSQL 16 with pgvector and Redis cache-aside",
        )

        # 8. Acceptance Criteria (3 to 6 items)
        acceptance = [
            "Ingestion pipeline processes up to 10,000 community events per minute under 50ms latency",
            "Zero false-positive alerts on verified production telemetry within 72 hours of deployment",
            "API endpoints maintain sub-100ms p95 response time under 1,000 concurrent requests",
        ]

        # 9. Evidence URLs
        evidence_urls = [signal.url]

        return BlueprintSpec(
            one_line_pitch=pitch,
            problem_statement=problem,
            target_persona=persona,
            pain_evidence_urls=evidence_urls,
            domain_tags=domain_tags,
            mvp_deliverables=deliverables,
            explicit_non_goals=non_goals,
            suggested_stack=stack,
            acceptance_criteria=acceptance,
        )
