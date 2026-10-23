"""The 2-Tier Hybrid Opportunity Evaluator.

Tier 1: Fast Heuristic Pruner (disqualifies local bugs, single-repo chores, consumer complaints in 1ms).
Tier 2: Semantic & LLM Evaluator (evaluates innovation, market viability, and standalone solvability via Dense Vectors / LLM).
"""

import re
from typing import Any

from app.scouts.models import OpportunityEvaluation, RawPainSignal
from app.services.llm_evaluator import LLMEvaluator

# =========================================================================
# Tier 1 Disqualifiers (Negative Filters ONLY - Never used for scoring)
# =========================================================================

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

# Disqualifier 2: Single-repository maintenance chores, release readiness, and internal PR noise
REPO_CHORE_PATTERNS = [
    r"\b(release readiness|post-v\d+\.\d+|bump version|milestone closure|acceptance gates?)\b",
    r"\b(re:\s*shape reconciliation|re:\s*perf\(|re:\s*compiler\(|re:\s*\[integrated)\b",
    r"\b(flaky test:\s*\w+)\b",
    r"\b(dual-account coordination|manifest d[aâ]y|manifest bi[eê]n|db rehearsal)\b",
    r"\b(chuyển heroku sang|migration manifest)\b",
]

# Disqualifier 3: Consumer complaints, personal subscriptions, and mobile apps
CONSUMER_AND_MOBILE_PATTERNS = [
    r"\b(iphone|ipad|ios app|android app|macos app)\b",
    r"\b(battery drain|dark mode|font size|screen brightness)\b",
    r"\b(student discount|personal tier|hobbyist|pricing in (india|brazil|turkey))\b",
    r"\b(chatgpt plus|claude pro|spotify|netflix|steam|playstation|xbox)\b",
    r"\b(dating app|social media algorithm|instagram|tiktok|youtube recommender)\b",
    r"\b(cancel my subscription|refund my 20 dollars)\b",
]

# Disqualifier 4: Framework flame wars, homework, or beginner tutorials
LOCAL_DEV_AND_OPINION_PATTERNS = [
    r"\b(iframe support|cypress|vitest|jest mock|webpack config|eslint rule|prettier)\b",
    r"\b(zsh autocomplete|sublime text|terminal font|theme)\b",
    r"\b(why i hate|php in 20\d\d|is \w+ dead|should i learn \w+|switch from \w+ to \w+)\b",
    r"\b(tabs vs spaces|vim vs emacs|my first project|help with homework)\b",
    r"\b(beginner tutorial|learn coding|portfolio review)\b",
]

# Disqualifier 5: Pure promotional spam
SPAM_PATTERNS = [
    r"\b(crypto airdrop|join my telegram|roast my (landing page|website)|free crypto)\b",
    r"\b(feedback on my landing page welcome)\b",
]


class OpportunityEvaluator:
    """Evaluates raw signals using the 2-Tier Hybrid Architecture.
    
    Tier 1 (Heuristic Pruning): Discards obvious non-opportunities in < 1ms.
    Tier 2 (Semantic / LLM Evaluation): Evaluates valid candidates via 384-dim dense vectors or LLM reasoning.
    """

    MIN_PASSING_TOTAL = 80
    MIN_DIMENSION_SCORE = 12

    @classmethod
    def check_tier1_disqualification(cls, signal: RawPainSignal) -> OpportunityEvaluation | None:
        """Tier 1: Fast Heuristic Pruning in < 1ms."""
        combined_text = f"{signal.title}\n{signal.content}".lower()

        for pat in TRIVIAL_BUG_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Local technical bug, compiler warning, or syntax error.")

        for pat in REPO_CHORE_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Single-repository internal maintenance chore, release ticket, or PR discussion.")

        for pat in CONSUMER_AND_MOBILE_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Consumer software, mobile app, or personal subscription complaint.")

        for pat in LOCAL_DEV_AND_OPINION_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Local dev tooling quirk, framework opinion piece, or tutorial question.")

        for pat in SPAM_PATTERNS:
            if re.search(pat, combined_text):
                return cls._disqualify(signal, "Promotional spam, token airdrop, or landing page roasting.")

        return None

    @classmethod
    def evaluate(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Synchronously scores a signal using Tier 1 Filter + Tier 2 Dense ONNX Vector Semantics."""
        disqualification = cls.check_tier1_disqualification(signal)
        if disqualification is not None:
            return disqualification

        # Tier 2: 100% Semantic Dense Vector Evaluation (Zero Regex Keyword Counting)
        return LLMEvaluator._evaluate_local_semantic(signal)

    @classmethod
    async def evaluate_async(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Asynchronously scores a signal using Tier 1 Filter + Tier 2 LLM Engine (with semantic fallback)."""
        disqualification = cls.check_tier1_disqualification(signal)
        if disqualification is not None:
            return disqualification

        # Tier 2: Full LLM Evaluation (Gemini/OpenAI/Claude/Ollama) with dense semantic fallback
        return await LLMEvaluator.evaluate_candidate(signal)

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
