"""The 2-Tier Hybrid Opportunity Evaluator.

Tier 1: Fast Heuristic Pruner (disqualifies local bugs, single-repo chores, consumer complaints in 1ms).
Tier 2: LLM & Dense Semantic Evaluator (evaluates innovation, market viability, and standalone solvability).
"""

import re
from typing import Any

from app.scouts.models import OpportunityEvaluation, RawPainSignal
from app.services.llm_evaluator import LLMEvaluator

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

# Innovation Category: AI & Autonomous Agent Leverage
AI_AND_AGENT_INNOVATION_INDICATORS = [
    r"\b(autonomous agent|multi-agent|agentic|agent loop|agent harness|tool use)\b",
    r"\b(mcp|model context protocol|tool calling|function calling)\b",
    r"\b(context window|context management|memory governance|long-term memory)\b",
    r"\b(prompt drift|eval harness|synthetic data|evals? benchmark)\b",
    r"\b(rag|vector search|embeddings|vector database|chunking|rerank)\b",
    r"\b(local llm|local inference|vllm|ollama|llama\.cpp|quantization|gguf|moe)\b",
    r"\b(hallucination|circuit breaker|token limit|token consumption)\b",
    r"\b(structured output|json schema|grammar-guided)\b",
]

# Innovation Category: Standalone Software & Developer Tooling
STANDALONE_PRODUCT_INDICATORS = [
    r"\b(developer tool|devtool|cli|sdk|library|api gateway|middleware)\b",
    r"\b(proxy|daemon|governor|orchestrator|workflow engine|pipeline)\b",
    r"\b(self-hosted|privacy-first|open source alternative|dashboard)\b",
    r"\b(micro-saas|saas|platform|extension|browser extension|vscode extension)\b",
    r"\b(fuzzing|security scanner|vulnerability|monitoring|alerting)\b",
    r"\b(automation|automated|orchestration|codegen|code generation)\b",
    r"\b(kubernetes|k8s|aws|gcp|terraform|docker|cloud infrastructure)\b",
    r"\b(database cluster|postgres replication|connection pool|split-brain|failover)\b",
    r"\b(data pipeline|cdc|change data capture|kafka|clickhouse|schema drift)\b",
    r"\b(soc2|hipaa|pci-dss|compliance|audit|iam privilege|standing access)\b",
    r"\b(finops|cloud bill|egress cost|unallocated compute|spend leak|snowflake cost)\b",
]

# Indicators of high problem intensity and market friction
PROBLEM_INTENSITY_INDICATORS = [
    r"\b(wasting hours|wasted|manual toil|nightmare|frustrated|struggling|exhausted|drowning)\b",
    r"\b(expensive|sick of paying|pricing is insane|cost runaway|bleeding|exploded|spend leak)\b",
    r"\b(alternative to|no good tool|missing in open source|why does no tool)\b",
    r"\b(unreliable|flaky|breaks constantly|silent corruption|hallucinating|hallucination)\b",
    r"\b(production issue|bottleneck|latency|memory leak|exhaustion|cascading|deadlock)\b",
    r"\b(compliance|audit|security leak|rce|vulnerability|data loss|outage|thundering herd)\b",
    r"\b(sla breach|failed audit|compliance fine|p1 outage|cost exploded|cascading)\b",
    r"\b(manual spreadsheet|spreadsheets|spreadsheet triage|drowning in manual|toil)\b",
    r"\b(vendor lock-in|price increase|privilege creep|standing access)\b",
]

# Indicators of commercial and adoption viability
COMMERCIAL_VIABILITY_INDICATORS = [
    r"\b(would pay|willing to pay|paying for|pricing|subscription|budget)\b",
    r"\b(freelancers|agencies|founders|startups|engineering team|devs|platform team)\b",
    r"\b(production|commercial|saas|api|monetization|revenue|enterprise)\b",
    r"\b(self-hostable|team seats|billing|client sites|infrastructure team)\b",
    r"\b(datadog bill|snowflake cost|aws bill|cloud bill|invoice|spending \$)\b",
    r"\b(ciso|compliance officer|engineering org|approved budget|procurement)\b",
]


class OpportunityEvaluator:
    """Evaluates raw signals using the 2-Tier Hybrid Architecture."""

    MIN_PASSING_TOTAL = 65
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
        """Synchronously scores a signal using Tier 1 Heuristics + Tier 2 Semantic Evaluation."""
        disqualification = cls.check_tier1_disqualification(signal)
        if disqualification is not None:
            return disqualification

        # Evaluate candidate through Tier 2 Dense Semantic Engine
        return cls._score_candidate(signal)

    @classmethod
    async def evaluate_async(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Asynchronously scores a signal using full Tier-2 LLM / Dense Semantic Engine."""
        disqualification = cls.check_tier1_disqualification(signal)
        if disqualification is not None:
            return disqualification

        # Tier 2: LLM evaluation (Gemini/OpenAI/Anthropic/Ollama) with semantic embedding fallback
        return await LLMEvaluator.evaluate_candidate(signal)

    @classmethod
    def _score_candidate(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Scores candidate signal incorporating semantic affinity and project viability signals."""
        combined_text = f"{signal.title}\n{signal.content}".lower()

        # Dimension 1: TAM & Community Resonance (0-25)
        tam = 8
        ai_hits = sum(1 for pat in AI_AND_AGENT_INNOVATION_INDICATORS if re.search(pat, combined_text))
        infra_hits = sum(1 for pat in STANDALONE_PRODUCT_INDICATORS if re.search(pat, combined_text))
        tam += min(12, (ai_hits * 4) + (infra_hits * 3))

        if signal.engagement_count >= 15:
            tam += 3
        if signal.engagement_count >= 50:
            tam += 2
        tam = max(0, min(25, tam))

        # Dimension 2: Urgency & Problem Intensity (0-25)
        urgency = 8
        intensity_hits = sum(1 for pat in PROBLEM_INTENSITY_INDICATORS if re.search(pat, combined_text))
        urgency += min(12, intensity_hits * 3)

        if len(signal.content) >= 150:
            urgency += 3
        if any(w in combined_text for w in ["nightmare", "wasting hours", "expensive", "broken", "frustrated", "struggling", "catastrophic", "wasted", "drowning", "exploded", "deadlock"]):
            urgency += 2
        urgency = max(0, min(25, urgency))

        # Dimension 3: Commercial & Adoption Viability (0-25)
        wtp = 8
        commercial_hits = sum(1 for pat in COMMERCIAL_VIABILITY_INDICATORS if re.search(pat, combined_text))
        wtp += min(12, commercial_hits * 3)

        if any(w in combined_text for w in ["enterprise", "freelancers", "agencies", "startups", "devops", "platform team", "production"]):
            wtp += 3
        if any(w in combined_text for w in ["pricing", "subscription", "paying", "billing", "bill", "invoice"]):
            wtp += 2
        wtp = max(0, min(25, wtp))

        # Dimension 4: Innovation & Standalone Product Solvability (0-25)
        feasibility = 8
        if ai_hits >= 1:
            feasibility += 8
        elif infra_hits >= 1:
            feasibility += 5

        if any(w in combined_text for w in ["proxy", "daemon", "gateway", "engine", "protocol", "pipeline", "ledger", "coordinator", "governor", "harness", "scanner", "dashboard", "cli"]):
            feasibility += 6
        if len(signal.content) >= 150:
            feasibility += 3
        feasibility = max(0, min(25, feasibility))

        total = tam + urgency + wtp + feasibility

        is_viable_project = (
            total >= cls.MIN_PASSING_TOTAL
            and tam >= cls.MIN_DIMENSION_SCORE
            and urgency >= cls.MIN_DIMENSION_SCORE
            and wtp >= cls.MIN_DIMENSION_SCORE
            and feasibility >= cls.MIN_DIMENSION_SCORE
        )

        rejection = None
        suggested_pitch = None

        if not is_viable_project:
            failed_dims = []
            if tam < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"TAM/Resonance ({tam}/25 < {cls.MIN_DIMENSION_SCORE})")
            if urgency < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"Urgency/Pain ({urgency}/25 < {cls.MIN_DIMENSION_SCORE})")
            if wtp < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"Commercial Viability ({wtp}/25 < {cls.MIN_DIMENSION_SCORE})")
            if feasibility < cls.MIN_DIMENSION_SCORE:
                failed_dims.append(f"Innovation/Solvability ({feasibility}/25 < {cls.MIN_DIMENSION_SCORE})")

            fail_summary = ", ".join(failed_dims) if failed_dims else f"Total score ({total}/100 < {cls.MIN_PASSING_TOTAL})"
            rejection = f"Failed Innovation Rubric: {fail_summary}. Insufficient standalone project leverage."
        else:
            clean_title = re.sub(r"[^\w\s-]", "", signal.title).strip()
            if len(clean_title) > 75:
                clean_title = clean_title[:72] + "..."
            suggested_pitch = f"Autonomous developer platform addressing {clean_title}"

        return OpportunityEvaluation(
            signal_id=signal.id,
            is_structural_problem=is_viable_project,
            tam_score=tam,
            urgency_score=urgency,
            willingness_to_pay_score=wtp,
            feasibility_score=feasibility,
            total_score=total,
            rationale=(
                f"Evaluated on TAM ({tam}/25), Urgency ({urgency}/25), Commercial ({wtp}/25), and Innovation/Solvability ({feasibility}/25). "
                f"Total score: {total}/100. Project qualification: {is_viable_project}."
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
