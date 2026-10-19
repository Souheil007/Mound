"""The Billion-Dollar Opportunity Evaluator.

Strictly scores raw online developer and business complaints to filter out
trivial technical bugs and minor scripts, passing only venture-scale market opportunities.
"""

import re
from typing import Any

from app.scouts.models import OpportunityEvaluation, RawPainSignal

# Negative indicators for localized bugs, syntax errors, or trivial utility scripts
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
]

# Positive indicators for structural commercial and architectural agony
VENTURE_SCALE_INDICATORS = [
    r"\bexpensive\b",
    r"\bspending\s+\$[\d,]+",
    r"\bhours every (week|day|month)\b",
    r"\bcompliance\s+(soc2|hipaa|iso|gdpr)\b",
    r"\bmanual (process|entry|export|spreadsheet)\b",
    r"\balternative to (salesforce|datadog|aws|snowflake|jira|stripe)\b",
    r"\bout of control (bill|cost|invoice)\b",
    r"\bpricing increase\b",
    r"\bvendor lock-in\b",
    r"\bchoking on (scale|throughput|latency)\b",
    r"\bdata loss in production\b",
    r"\bunexpected cloud bill\b",
]


class OpportunityEvaluator:
    """Evaluates raw pain signals against the 4-dimensional Billion-Dollar Rubric."""

    @classmethod
    def evaluate(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Determines whether a pain signal qualifies as a high-value engineering opportunity.

        Args:
            signal: The normalized RawPainSignal from Reddit, HN, or GitHub.

        Returns:
            An OpportunityEvaluation with dimension scores (0-25) and pass/reject status.
        """
        combined_text = f"{signal.title}\n{signal.content}".lower()

        # 1. Fast Disqualification: Check for trivial bug patterns
        for pat in TRIVIAL_BUG_PATTERNS:
            if re.search(pat, combined_text):
                return OpportunityEvaluation(
                    signal_id=signal.id,
                    is_structural_problem=False,
                    tam_score=5,
                    urgency_score=5,
                    willingness_to_pay_score=2,
                    feasibility_score=5,
                    total_score=17,
                    rationale="Identified as a localized technical bug, compiler warning, or syntax error.",
                    rejection_reason="Local technical bug or framework syntax error.",
                )

        # 2. Score Dimension 1: TAM & Market Breadth (0-25)
        tam = 10
        if any(term in combined_text for term in ["saas", "enterprise", "aws", "kubernetes", "database", "cloud", "apps", "tools", "desktop", "software"]):
            tam += 8
        if signal.engagement_count > 10:
            tam += 4
        if signal.engagement_count > 100:
            tam += 3
        tam = min(25, tam)

        # 3. Score Dimension 2: Urgency & Pain Severity (0-25)
        urgency = 10
        severity_hits = sum(1 for pat in VENTURE_SCALE_INDICATORS if re.search(pat, combined_text))
        urgency += min(12, severity_hits * 4)
        if len(signal.content) > 300:
            urgency += 3
        urgency = min(25, urgency)

        # 4. Score Dimension 3: Willingness to Pay & Commercial Viability (0-25)
        wtp = 10
        if any(kw in combined_text for kw in ["$", "pricing", "cost", "bill", "expensive", "budget", "invoice", "pay", "alternatives"]):
            wtp += 10
        if any(kw in combined_text for kw in ["enterprise", "company", "team", "production", "clients", "users"]):
            wtp += 5
        wtp = min(25, wtp)

        # 5. Score Dimension 4: Technical Feasibility & Structural Moat (0-25)
        feasibility = 12
        if len(signal.content) > 200:
            feasibility += 7
        if any(kw in combined_text for kw in ["architecture", "api", "database", "infrastructure", "system", "protocol", "shipping", "desktop"]):
            feasibility += 6
        feasibility = min(25, feasibility)

        total = tam + urgency + wtp + feasibility
        is_structural = total >= 70

        rejection = None
        suggested_pitch = None

        if not is_structural:
            rejection = f"Score ({total}/100) below threshold of 80. Pain is not widespread or commercially viable enough."
        else:
            # Generate clean suggested pitch
            clean_title = signal.title.strip().rstrip(".")
            if len(clean_title) > 90:
                clean_title = clean_title[:87] + "..."
            suggested_pitch = f"Autonomous enterprise solution solving: {clean_title}"
            if len(suggested_pitch) < 50:
                suggested_pitch = f"High-throughput automated systems platform addressing {clean_title} in production"

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
                f"Total score: {total}/100."
            ),
            suggested_pitch=suggested_pitch,
            rejection_reason=rejection,
        )
