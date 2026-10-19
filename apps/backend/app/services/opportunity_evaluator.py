"""The Billion-Dollar Opportunity Evaluator.

Strictly scores raw online developer and business complaints against a rigorous
venture-scale rubric to filter out trivial bugs, consumer apps, and minor scripts,
passing only true multi-million and billion-dollar enterprise market opportunities.
"""

import re
from typing import Any

from app.scouts.models import OpportunityEvaluation, RawPainSignal

# Disqualifier 1: Localized bugs, syntax errors, or trivial compiler warnings
TRIVIAL_BUG_PATTERNS = [
    r"\berror:\s*cannot find module\b",
    r"\btypeerror:\s*cannot read property\b",
    r"\bsyntaxerror\b",
    r"\bnullpointerexception\b",
    r"\bhow to fix this bug\b",
    r"\bwhy is my css not working\b",
    r"\bpage reload doesn't work\b",
    r"\bdeprecat(ed|ion)\s+warning\b",
    r"\bfailed to compile\b",
    r"\bpermission denied\b",
    r"\bunexpected token\b",
    r"\bspelling typo\b",
    r"\bsegmentation fault\b",
    r"\bunhandled promise rejection\b",
    r"\battributeerror\b",
]

# Disqualifier 2: Consumer complaints, personal subscriptions, and mobile apps
CONSUMER_AND_MOBILE_PATTERNS = [
    r"\b(iphone|ipad|ios app|android app|macos app)\b",
    r"\b(battery drain|dark mode|font size|screen brightness)\b",
    r"\b(student discount|personal tier|hobbyist|pricing in (india|brazil|turkey))\b",
    r"\b(chatgpt plus|claude pro|spotify|netflix|steam|playstation|xbox)\b",
    r"\b(dating app|social media algorithm|instagram|tiktok|youtube recommender)\b",
    r"\b(cancel my subscription|refund my 20 dollars)\b",
]

# Disqualifier 3: Local dev ergonomics, single library quirks, and flame wars
LOCAL_DEV_AND_OPINION_PATTERNS = [
    r"\b(iframe support|cypress|vitest|jest mock|webpack config|eslint rule|prettier)\b",
    r"\b(zsh autocomplete|vscode extension|sublime text|terminal font|theme)\b",
    r"\b(why i hate|php in 20\d\d|is \w+ dead|should i learn \w+|switch from \w+ to \w+)\b",
    r"\b(tabs vs spaces|vim vs emacs|my first project|help with homework)\b",
    r"\b(beginner tutorial|learn coding|portfolio review)\b",
]

# Disqualifier 4: Self-promotion, side projects, and landing page reviews
SELF_PROMO_PATTERNS = [
    r"\bshow hn:?\b",
    r"\bi built a\b",
    r"\bmy side project\b",
    r"\bcheck out my\b",
    r"\bfeedback on my (landing page|saas|project|app)\b",
    r"\blaunched today\b",
]

# Positive indicators for enterprise infrastructure, FinOps, and multi-tenant bottlenecks
ENTERPRISE_INFRA_INDICATORS = [
    r"\b(kubernetes|k8s|aws|gcp|azure|terraform|cloud infrastructure)\b",
    r"\b(database cluster|postgres replication|connection pool|split-brain|failover)\b",
    r"\b(data pipeline|cdc|change data capture|kafka|clickhouse|schema drift)\b",
    r"\b(soc2|hipaa|pci-dss|compliance|audit|iam privilege|standing access)\b",
    r"\b(finops|cloud bill|egress cost|unallocated compute|spend leak|snowflake cost)\b",
    r"\b(telemetry|cardinality|ebpf|distributed tracing|log retention)\b",
    r"\b(api rate limit|breaking schema|webhook delivery failure)\b",
    r"\b(multi-tenant|distributed deadlock|cascading outage|zero-downtime)\b",
]

# Indicators of severe operational agony and financial bleeding
SEVERE_AGONY_INDICATORS = [
    r"\b(data loss|silent data corruption|unplanned downtime|production outage|outage)\b",
    r"\b(thousands of dollars|six-figure|exploded by|wasted|cost runaway)\b",
    r"\b(sla breach|failed audit|audit failure|compliance fine|compliance failure|compliance audit|p1 outage|cascading)\b",
    r"\b(manual spreadsheet|spreadsheets|spreadsheet triage|drowning in manual|choking on|toil)\b",
    r"\b(vendor lock-in|price increase|thundering herd|exhaustion|privilege creep|privilege drift|standing access)\b",
]

# Indicators of commercial viability and high enterprise willingness to pay
WILLINGNESS_TO_PAY_INDICATORS = [
    r"\b(enterprise|procurement|approved budget|contract|annual budget)\b",
    r"\b(datadog bill|snowflake cost|aws bill|cloud bill|invoice|spending \$)\b",
    r"\b(ciso|compliance officer|infrastructure team|devops team|engineering org|platform team)\b",
    r"\b(production cluster|multi-tenant|sla breach|thousands of dollars lost)\b",
]


class OpportunityEvaluator:
    """Evaluates raw pain signals against the 4-dimensional Billion-Dollar Rubric."""

    MIN_PASSING_TOTAL = 80
    MIN_DIMENSION_SCORE = 16

    @classmethod
    def evaluate(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Determines whether a pain signal qualifies as a high-value engineering opportunity.

        Args:
            signal: The normalized RawPainSignal from Reddit, HN, or GitHub.

        Returns:
            An OpportunityEvaluation with dimension scores (0-25) and pass/reject status.
        """
        combined_text = f"{signal.title}\n{signal.content}".lower()

        # 1. Fast Disqualification Checks
        for pat in TRIVIAL_BUG_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Local technical bug, compiler warning, or syntax error.")

        for pat in CONSUMER_AND_MOBILE_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Consumer software, mobile app, or personal subscription complaint.")

        for pat in LOCAL_DEV_AND_OPINION_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Local dev tooling quirk, framework opinion piece, or tutorial question.")

        for pat in SELF_PROMO_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Self-promotion, side-project announcement, or landing page review.")

        # 2. Score Dimension 1: TAM & Enterprise Market Breadth (0-25)
        tam = 8
        infra_hits = sum(1 for pat in ENTERPRISE_INFRA_INDICATORS if re.search(pat, combined_text))
        tam += min(12, infra_hits * 4)
        if signal.engagement_count >= 20:
            tam += 3
        if signal.engagement_count >= 50:
            tam += 2
        tam = max(0, min(25, tam))

        # 3. Score Dimension 2: Urgency & Operational Agony (0-25)
        urgency = 8
        agony_hits = sum(1 for pat in SEVERE_AGONY_INDICATORS if re.search(pat, combined_text))
        urgency += min(12, agony_hits * 4)
        if len(signal.content) >= 200:
            urgency += 3
        if any(w in combined_text for w in ["catastrophic", "untenable", "nightmare", "choking", "broken", "bleeding"]):
            urgency += 2
        urgency = max(0, min(25, urgency))

        # 4. Score Dimension 3: Willingness to Pay & Commercial Viability (0-25)
        wtp = 8
        wtp_hits = sum(1 for pat in WILLINGNESS_TO_PAY_INDICATORS if re.search(pat, combined_text))
        wtp += min(12, wtp_hits * 4)
        if any(w in combined_text for w in ["enterprise", "production", "infrastructure", "devops", "finops", "compliance", "ciso"]):
            wtp += 3
        if any(w in combined_text for w in ["engineering org", "platform team", "cluster", "multi-tenant"]):
            wtp += 2
        # Strict penalties for hobbyist / free seekers
        if any(w in combined_text for w in ["free tier", "open source alternative for free", "too poor", "hobby"]):
            wtp = max(0, wtp - 15)
        wtp = max(0, min(25, wtp))

        # 5. Score Dimension 4: Technical Feasibility & Systemic Moat (0-25)
        feasibility = 10
        if any(w in combined_text for w in ["architecture", "proxy", "daemon", "gateway", "engine", "protocol", "stream", "pipeline", "ledger", "coordinator", "policy"]):
            feasibility += 8
        if len(signal.content) >= 200:
            feasibility += 4
        if signal.engagement_count >= 10:
            feasibility += 3
        feasibility = max(0, min(25, feasibility))

        total = tam + urgency + wtp + feasibility

        # Strict Multi-Dimensional Barrier
        is_structural = (
            total >= cls.MIN_PASSING_TOTAL
            and tam >= cls.MIN_DIMENSION_SCORE
            and urgency >= cls.MIN_DIMENSION_SCORE
            and wtp >= cls.MIN_DIMENSION_SCORE
            and feasibility >= cls.MIN_DIMENSION_SCORE
        )

        rejection = None
        suggested_pitch = None

        if not is_structural:
            failed_dims = []
            if tam < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"TAM ({tam}/25 < {cls.MIN_DIMENSION_SCORE})")
            if urgency < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"Urgency ({urgency}/25 < {cls.MIN_DIMENSION_SCORE})")
            if wtp < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"WTP ({wtp}/25 < {cls.MIN_DIMENSION_SCORE})")
            if feasibility < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"Feasibility ({feasibility}/25 < {cls.MIN_DIMENSION_SCORE})")

            fail_summary = ", ".join(failed_dims) if failed_dims else f"Total score ({total}/100 < {cls.MIN_PASSING_TOTAL})"
            rejection = f"Failed Billion-Dollar Rubric: {fail_summary}. Does not represent a venture-scale market opportunity."
        else:
            clean_title = re.sub(r"[^\w\s-]", "", signal.title).strip()
            if len(clean_title) > 75:
                clean_title = clean_title[:72] + "..."
            suggested_pitch = f"High-throughput enterprise infrastructure platform addressing {clean_title} in production"

        return OpportunityEvaluation(
            signal_id=signal.id,
            is_structural_problem=is_structural,
            tam_score=tam,
            urgency_score=urgency,
            willingness_to_pay_score=wtp,
            feasibility_score=feasibility,
            total_score=total,
            rationale=(
                f"Evaluated on TAM ({tam}/25), Urgency ({urgency}/25), WTP ({wtp}/25), and Feasibility ({feasibility}/25). "
                f"Total score: {total}/100. Structural qualification: {is_structural}."
            ),
            suggested_pitch=suggested_pitch,
            rejection_reason=rejection,
        )

    @classmethod
    def _disqualify(cls, signal: RawPainSignal, reason: str) -> OpportunityEvaluation:
        """Helper to return an immediate disqualification response."""
        return OpportunityEvaluation(
            signal_id=signal.id,
            is_structural_problem=False,
            tam_score=4,
            urgency_score=4,
            willingness_to_pay_score=2,
            feasibility_score=5,
            total_score=15,
            rationale=f"Disqualified: {reason}",
            rejection_reason=reason,
        )
