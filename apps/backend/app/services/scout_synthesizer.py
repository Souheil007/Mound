"""Scout Synthesizer: Translates qualified high-scoring pain signals into strictly-typed BlueprintSpec proposals.

Dynamically categorizes problems into specific enterprise domains (FinOps, Distributed Systems,
Security Compliance, Data Engineering, Observability, API Infrastructure) and generates
bespoke, production-grade architectural specifications with tailored deliverables and criteria.
"""

import re
from typing import Any

from app.schemas.blueprint_spec import BlueprintSpec, SuggestedStack
from app.scouts.models import OpportunityEvaluation, RawPainSignal

# Domain keyword signatures for dynamic categorization
DOMAIN_SIGNATURES: dict[str, list[str]] = {
    "FINOPS": [
        "finops", "cloud bill", "aws bill", "cost", "spending", "egress", "unallocated", "compute spend",
        "expensive", "invoice", "datadog bill", "snowflake cost", "pricing increase", "waste", "budget",
    ],
    "DISTRIBUTED_SYSTEMS": [
        "connection pool", "database cluster", "postgres replication", "distributed", "split-brain",
        "deadlock", "failover", "thundering herd", "concurrency", "lock", "high-availability", "latency spike",
    ],
    "SECURITY_COMPLIANCE": [
        "soc2", "hipaa", "compliance", "audit", "pci-dss", "iam privilege", "standing access",
        "secret leakage", "tamper", "vulnerability", "gdpr", "policy enforcement", "security invariant",
    ],
    "DATA_ENGINEERING": [
        "data pipeline", "cdc", "change data capture", "kafka", "clickhouse", "schema drift",
        "streaming etl", "columnar", "parquet", "partition", "data corruption", "ingestion",
    ],
    "DEVOPS_OBSERVABILITY": [
        "telemetry", "cardinality", "ebpf", "distributed tracing", "opentelemetry", "alerting fatigue",
        "metric explosion", "sre", "monitoring cost", "canary", "log retention", "tracing overhead",
    ],
    "API_INTEGRATION_INFRA": [
        "api rate limit", "breaking schema", "webhook", "api gateway", "vendor lock-in",
        "provider outage", "token-bucket", "retry queue", "contract validation", "third-party api",
    ],
}

# Bespoke domain specifications
DOMAIN_ARCHETYPES: dict[str, dict[str, Any]] = {
    "FINOPS": {
        "pitch_template": "Autonomous FinOps telemetry and policy engine eliminating cloud compute and egress waste",
        "persona": "Cloud FinOps directors, VP of Infrastructure, and enterprise platform engineering leads.",
        "problem_template": (
            "Modern multi-tenant cloud architectures suffer from severe financial waste caused by unallocated cloud compute, "
            "opaque network egress routing, and unmonitored resource overprovisioning. Standard vendor dashboards lack autonomous "
            "policy enforcement, forcing engineering and finance teams to spend weeks in manual spreadsheet triage while unexpected "
            "cloud invoices surge past quarterly budgets."
        ),
        "deliverables": [
            "eBPF-driven runtime container telemetry collector attributing compute, network egress, and memory footprint per tenant",
            "Dynamic cloud policy enforcement proxy intercepting and rightsizing unallocated cloud API provisioning calls in real time",
            "Automated zero-downtime downsizing orchestrator safely draining and rescheduling overprovisioned cluster nodes",
        ],
        "acceptance": [
            "Demonstrates continuous attribution of 100% of ephemeral compute and network egress costs within 30 seconds of allocation",
            "Reduces idle non-production cloud infrastructure spending by at least 30% within 30 days of initial deployment",
            "Policy enforcement proxy introduces strictly less than 4ms latency overhead on cloud control-plane API calls",
        ],
        "stack": SuggestedStack(
            language="Rust (edition 2021) or Go 1.22",
            core_libraries=["tokio", "ebpf-cilium", "tonic-grpc", "pydantic-v2"],
            storage="ClickHouse for high-cardinality time-series and PostgreSQL 16 for policy configurations",
        ),
        "non_goals": [
            "Does not negotiate custom enterprise pricing agreements or manage offline vendor contract paperwork",
            "Does not terminate active mission-critical stateful database workloads without verified human operator confirmation",
        ],
        "tags": ["finops", "cloud-cost", "infrastructure", "aws", "automation"],
    },
    "DISTRIBUTED_SYSTEMS": {
        "pitch_template": "High-throughput distributed coordinator mitigating connection exhaustion and failover deadlocks",
        "persona": "Principal distributed systems architects, SRE team leads, and backend infrastructure engineers.",
        "problem_template": (
            "High-traffic distributed architectures face severe reliability failures due to database connection pool exhaustion, "
            "thundering herd spikes, and catastrophic failover deadlocks. Existing client-side drivers and static connection pools lack "
            "coordinated backpressure, leading to cascading outages, SLA breaches, and costly downtime during traffic surges."
        ),
        "deliverables": [
            "Zero-copy distributed connection multiplexer dynamically pooling and leasing backend database connections",
            "Consensus-backed adaptive backpressure engine shedding non-critical read traffic during downstream latency spikes",
            "Automated circuit-breaker daemon preventing thundering herds and cascading retries during primary failover",
        ],
        "acceptance": [
            "Multiplexer sustains 50,000 concurrent client connections while maintaining sub-8ms p99 proxy latency overhead",
            "Zero connection drops or split-brain deadlocks recorded during simulated primary database failover under heavy load",
            "Adaptive backpressure stabilizes system throughput within 100ms of downstream database latency degradation",
        ],
        "stack": SuggestedStack(
            language="Rust (edition 2021)",
            core_libraries=["tokio", "tower", "pingora", "hyper"],
            storage="Redis cluster for fast distributed leases and PostgreSQL 16 for metadata",
        ),
        "non_goals": [
            "Does not alter upstream application query syntax or rewrite complex relational queries in flight",
            "Does not replace native database storage engines or manage physical disk partitioning",
        ],
        "tags": ["distributed-systems", "infrastructure", "high-availability", "database", "reliability"],
    },
    "SECURITY_COMPLIANCE": {
        "pitch_template": "Continuous autonomous policy engine enforcing real-time SOC2 and HIPAA compliance invariants",
        "persona": "Chief Information Security Officers (CISOs), compliance officers, and SecOps engineering managers.",
        "problem_template": (
            "Enterprise organizations lose hundreds of engineering hours every quarter manually generating point-in-time compliance "
            "evidence for SOC2, HIPAA, and ISO27001 audits. Point-in-time screenshots and manual spreadsheets fail to detect continuous "
            "IAM privilege drift, unencrypted storage exposures, and unpatched infrastructure vulnerabilities between audit cycles."
        ),
        "deliverables": [
            "Continuous infrastructure-as-code and runtime policy engine evaluating SOC2, HIPAA, and ISO27001 invariants",
            "Ephemeral credential manager with automated just-in-time privilege revocation eliminating standing access",
            "Cryptographically verifiable audit log exporting continuous tamper-proof proofs directly to enterprise SIEMs",
        ],
        "acceptance": [
            "Evaluates 100% of infrastructure state changes within 15 seconds, alerting on any compliance invariant breach",
            "Cryptographic audit ledger guarantees tamper-evident provenance verifiable by external auditors without manual exports",
            "Just-in-time credential broker reduces standing administrative cloud privileges across production environments to zero",
        ],
        "stack": SuggestedStack(
            language="Go 1.22 or Rust (edition 2021)",
            core_libraries=["open-policy-agent", "cosign", "vault-sdk", "pydantic-v2"],
            storage="PostgreSQL 16 with pgvector and append-only tamper-evident cryptographic log",
        ),
        "non_goals": [
            "Does not replace external certified auditor opinions or provide legal indemnification counsel",
            "Does not manage physical building access or offline corporate HR security policies",
        ],
        "tags": ["security", "compliance", "soc2", "enterprise", "audit"],
    },
    "DATA_ENGINEERING": {
        "pitch_template": "Distributed Change Data Capture and schema drift engine ensuring zero-downtime ETL pipelines",
        "persona": "Head of Data Engineering, Principal Data Architects, and analytics platform engineers.",
        "problem_template": (
            "Modern data organizations face critical production failures when unexpected upstream database schema changes break "
            "downstream analytics pipelines and cause silent data corruption. Existing batch ETL pipelines and rigid ingestion tools fail "
            "to handle high-throughput CDC events reliably, resulting in multi-day data pipeline stalls and stale reporting."
        ),
        "deliverables": [
            "Asynchronous Change Data Capture (CDC) stream engine with distributed partition rebalancing and exactly-once semantics",
            "Automated bidirectional schema evolution gate with real-time drift detection and backward-compatibility validation",
            "Zero-copy columnar transformation pipeline sustaining high-throughput streaming ingestion without memory bloat",
        ],
        "acceptance": [
            "Ingestion pipeline sustains 100,000 events per second with end-to-end stream latency strictly below 50ms",
            "Zero unhandled schema drift failures: breaking migrations are quarantined with zero data loss or pipeline interruption",
            "Achieves verified exactly-once delivery across distributed consumer group rebalances under simulated worker crashes",
        ],
        "stack": SuggestedStack(
            language="Rust (edition 2021) or Python 3.12",
            core_libraries=["apache-arrow", "datafusion", "confluent-kafka", "pydantic-v2"],
            storage="Apache Parquet on S3 / MinIO with Apache Iceberg catalog and PostgreSQL metadata",
        ),
        "non_goals": [
            "Does not build frontend BI visualization dashboards or replace consumer-facing reporting tools",
            "Does not support legacy unindexed flat CSV batch drops over SFTP in the core streaming runtime",
        ],
        "tags": ["data-engineering", "cdc", "streaming", "kafka", "pipelines"],
    },
    "DEVOPS_OBSERVABILITY": {
        "pitch_template": "Low-overhead telemetry gateway mitigating metric cardinality explosion and tracing cost",
        "persona": "SRE directors, VP of Platform Engineering, and observability infrastructure architects.",
        "problem_template": (
            "High-cardinality telemetry across microservice fleets leads to unsustainable monitoring SaaS bills and severe alerting "
            "fatigue. Engineering teams drown in noisy alerts while observability costs grow faster than core compute, yet critical "
            "distributed causal dependencies remain difficult to isolate during production incidents."
        ),
        "deliverables": [
            "Adaptive telemetry proxy dynamically downsampling low-entropy spans while preserving 100% of error traces",
            "High-cardinality metric roll-up aggregator mitigating index explosion prior to downstream storage ingestion",
            "Causality correlation engine linking distributed trace spans directly to host resource spikes and git commits",
        ],
        "acceptance": [
            "Telemetry proxy processes up to 1,000,000 trace spans per second with under 2ms proxy latency overhead",
            "Reduces downstream observability storage footprint and SaaS ingestion costs by at least 45% without losing error context",
            "Isolates root-cause upstream microservice within 20 seconds of an anomaly detection event",
        ],
        "stack": SuggestedStack(
            language="Go 1.22 or Rust (edition 2021)",
            core_libraries=["opentelemetry-collector", "ebpf-cilium", "prometheus-client", "grpc"],
            storage="ClickHouse for high-throughput columnar trace and log storage",
        ),
        "non_goals": [
            "Does not create proprietary charting widgets—exports standard Prometheus and OpenTelemetry formats",
            "Does not perform intrusive in-memory bytecode instrumentation of third-party closed-source binaries",
        ],
        "tags": ["observability", "devops", "sre", "opentelemetry", "monitoring"],
    },
    "API_INTEGRATION_INFRA": {
        "pitch_template": "Resilient multi-provider API gateway providing dynamic rate-limit pooling and contract enforcement",
        "persona": "Enterprise API architects, platform engineering leads, and core backend developers.",
        "problem_template": (
            "Critical enterprise applications integrating multiple external cloud and AI APIs face recurring downtime from sudden "
            "provider rate limits, undocumented API contract breaks, and webhook delivery timeouts. Without resilient multi-provider "
            "pooling and automated fallback routing, single-provider outages immediately disrupt customer-facing workflows."
        ),
        "deliverables": [
            "Distributed API proxy with dynamic multi-provider failover, token-bucket pooling, and priority request queueing",
            "Automated API schema contract validator catching upstream breaking payload alterations before database ingestion",
            "Idempotent distributed webhook delivery coordinator guaranteeing zero-loss dispatch with exponential backoff",
        ],
        "acceptance": [
            "Proxy transparently reroutes 100% of requests to standby providers within 15ms upon detecting primary upstream 429 or 5xx errors",
            "Webhook coordinator guarantees at-least-once delivery with cryptographic payload verification under simulated network partitions",
            "Maintains sub-5ms p99 latency overhead under a sustained load of 25,000 requests per second",
        ],
        "stack": SuggestedStack(
            language="Rust (edition 2021) or Go 1.22",
            core_libraries=["tokio", "pingora", "redis-rs", "pydantic-v2"],
            storage="Redis cluster for distributed rate-limit counters and PostgreSQL 16 for audit records",
        ),
        "non_goals": [
            "Does not bypass third-party terms of service, CAPTCHAs, or unauthorized authentication protocols",
            "Does not maintain customer billing checkout flows or merchant payment processing accounts",
        ],
        "tags": ["api-gateway", "infrastructure", "rate-limiting", "reliability", "backend"],
    },
}


class ScoutSynthesizer:
    """Transforms raw community signals into complete, verifiable BlueprintSpec contracts."""

    @classmethod
    def classify_domain(cls, signal: RawPainSignal) -> str:
        """Determines the core enterprise domain for a raw signal based on keyword affinity."""
        combined_text = f"{signal.title} {signal.content}".lower()
        scores: dict[str, int] = {}
        for domain, keywords in DOMAIN_SIGNATURES.items():
            scores[domain] = sum(1 for kw in keywords if kw in combined_text)

        # Default to FINOPS or highest scored domain
        best_domain = max(scores, key=lambda k: scores[k])
        if scores[best_domain] == 0:
            return "DISTRIBUTED_SYSTEMS"
        return best_domain

    @classmethod
    def synthesize_spec(
        cls,
        signal: RawPainSignal,
        evaluation: OpportunityEvaluation,
    ) -> BlueprintSpec:
        """Synthesizes a production-grade BlueprintSpec matching Mound's schema.

        Args:
            signal: The original RawPainSignal (Reddit, GitHub, HN).
            evaluation: The passing OpportunityEvaluation (score >= 82).

        Returns:
            A strictly validated BlueprintSpec with dynamic domain deliverables.
        """
        domain_key = cls.classify_domain(signal)
        archetype = DOMAIN_ARCHETYPES[domain_key]

        # 1. Calibrate one_line_pitch: strictly 50-140 chars
        clean_title = re.sub(r"[^\w\s-]", "", signal.title).strip()
        if len(clean_title) > 60:
            clean_title = clean_title[:57] + "..."

        pitch = archetype["pitch_template"]
        # Tailor slightly if length permits
        if len(f"{pitch} across enterprise systems") <= 140:
            pitch = f"{pitch} across enterprise systems"
        if len(pitch) > 140:
            pitch = pitch[:137] + "..."
        if len(pitch) < 50:
            pitch = f"{pitch} in production environments"

        # 2. Calibrate problem_statement: strictly 100-600 chars
        # State the problem professionally without raw quotes or author handle shoutouts
        problem = archetype["problem_template"].strip()
        # Ensure length is strictly within [100, 590]
        if len(problem) < 100:
            problem = (
                f"{problem} Current tooling forces teams to waste hundreds of engineering hours on error-prone "
                f"manual mitigation while operational risks compound."
            )
        if len(problem) > 590:
            problem = problem[:587] + "..."

        # 3. Target Persona: strictly 50-250 chars
        persona = archetype["persona"].strip()
        if len(persona) < 50:
            persona = f"Enterprise infrastructure leaders, platform architects, and {persona}"
        if len(persona) > 250:
            persona = persona[:247] + "..."

        # 4. Domain tags (1 to 5)
        domain_tags = archetype["tags"][:5]

        # 5. MVP Deliverables (3 to 5 items)
        deliverables = archetype["deliverables"][:5]

        # 6. Explicit Non-Goals (2 to 4 items)
        non_goals = archetype["non_goals"][:4]

        # 7. Suggested Stack
        stack = archetype["stack"]

        # 8. Acceptance Criteria (3 to 6 items)
        acceptance = archetype["acceptance"][:6]

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
