"""Tier-2 Intelligent Opportunity Evaluator.

Provides semantic LLM-driven evaluation for candidate signals that pass the Tier-1 filter.
Supports Google Gemini, Mistral AI, OpenAI, Anthropic, local Ollama, and local ONNX vector semantic embeddings.
"""

import json
import logging
import math
import os
import re
from typing import Any

import httpx

from app.core.config import settings
from app.scouts.models import OpportunityEvaluation, RawPainSignal
from app.services.embedding_engine import EmbeddingEngine

logger = logging.getLogger(__name__)

# Reference archetype embeddings for local semantic evaluation (when external LLM keys are absent)
ARCHETYPE_PROMPTS = [
    # Enterprise Infrastructure & Reliability
    "Autonomous AI agent governance, tool calling harness, prompt drift detection, context window management, and Model Context Protocol servers",
    "High-availability distributed database proxy, connection pool multiplexer, adaptive backpressure coordinator, and failover circuit breaker",
    "Automated zero-day CVE vulnerability scanner, exploit surface auditor for agencies, and continuous infrastructure compliance monitor",
    "SaaS external dependency sentinel, cloud quota and billing alert governor, and synthetic golden-path health check agent",
    # Developer Productivity, Build Tools & Micro-SaaS
    "High-leverage standalone developer productivity tool, CLI utility, SDK generator, API gateway proxy, and workflow orchestration engine",
    "Developer workflow automation, schema migration validator, webhook reliability proxy, and third-party API contract tester",
    "Lightweight developer micro-SaaS, error monitoring sentinel, database backup verification engine, and background job dashboard",
    "Cross-platform developer tooling, local environment orchestrator, git workflow assistant, and automated release manager",
]


class LLMEvaluator:
    """Tier-2 Product Architect: Evaluates viability, novelty, and market defensibility."""

    _archetype_vectors: list[list[float]] | None = None

    @classmethod
    def _cosine_similarity(cls, v1: list[float], v2: list[float]) -> float:
        """Computes cosine similarity between two normalized vectors."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    @classmethod
    def _get_archetype_vectors(cls) -> list[list[float]]:
        """Lazily generates and caches reference vectors for high-value software archetypes."""
        if cls._archetype_vectors is None:
            cls._archetype_vectors = EmbeddingEngine.embed_texts(ARCHETYPE_PROMPTS)
        return cls._archetype_vectors

    @classmethod
    async def evaluate_candidate(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Performs Tier-2 evaluation on a candidate signal via LLM or dense semantic vector analysis."""
        provider = (getattr(settings, "llm_provider", "") or "").lower()
        mistral_key = getattr(settings, "mistral_api_key", None) or os.getenv("MISTRAL_API_KEY")
        gemini_key = getattr(settings, "gemini_api_key", None) or os.getenv("GEMINI_API_KEY")
        openai_key = getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        anthropic_key = getattr(settings, "anthropic_api_key", None) or os.getenv("ANTHROPIC_API_KEY")
        mistral_model = getattr(settings, "mistral_model", "open-mistral-7b")

        # 1. Prioritize explicitly selected provider
        if provider == "mistral" and mistral_key:
            try:
                return await cls._evaluate_mistral(signal, mistral_key, mistral_model)
            except Exception as exc:
                logger.warning("Tier-2 Mistral evaluation failed, falling back: %s", exc)

        if provider == "gemini" and gemini_key:
            try:
                return await cls._evaluate_gemini(signal, gemini_key)
            except Exception as exc:
                logger.warning("Tier-2 Gemini evaluation failed, falling back: %s", exc)

        if provider == "openai" and openai_key:
            try:
                return await cls._evaluate_openai(signal, openai_key)
            except Exception as exc:
                logger.warning("Tier-2 OpenAI evaluation failed, falling back: %s", exc)

        if provider == "anthropic" and anthropic_key:
            try:
                return await cls._evaluate_anthropic(signal, anthropic_key)
            except Exception as exc:
                logger.warning("Tier-2 Anthropic evaluation failed, falling back: %s", exc)

        # 2. Cascade through any other configured API keys
        providers_to_try = [
            ("mistral", mistral_key),
            ("gemini", gemini_key),
            ("openai", openai_key),
            ("anthropic", anthropic_key),
        ]
        for name, key in providers_to_try:
            if not key or name == provider:
                continue
            try:
                if name == "mistral":
                    return await cls._evaluate_mistral(signal, key, mistral_model)
                elif name == "gemini":
                    return await cls._evaluate_gemini(signal, key)
                elif name == "openai":
                    return await cls._evaluate_openai(signal, key)
                elif name == "anthropic":
                    return await cls._evaluate_anthropic(signal, key)
            except Exception as exc:
                logger.warning("Tier-2 %s evaluation failed, trying next provider: %s", name, exc)

        # 3. Local Dense Vector Semantic Evaluation (Zero Cost, No API Key, ONNX Runtime)
        return cls._evaluate_local_semantic(signal)

    @classmethod
    def _evaluate_local_semantic(cls, signal: RawPainSignal) -> OpportunityEvaluation:
        """Evaluates project potential using 384-dimensional dense semantic similarity against reference archetypes."""
        combined_text = f"{signal.title}\n{signal.content[:600]}"
        signal_vector = EmbeddingEngine.embed_text(combined_text)

        # Measure semantic affinity to modern software project archetypes
        archetypes = cls._get_archetype_vectors()
        affinities = [cls._cosine_similarity(signal_vector, arch) for arch in archetypes]
        max_affinity = max(affinities) if affinities else 0.5
        avg_affinity = sum(affinities) / len(affinities) if affinities else 0.4

        # Dynamic scoring scaled from dense semantic vector affinity (no regex counting)
        tam = int(10 + max(0, min(15, max_affinity * 30)))
        urgency = int(10 + max(0, min(15, max_affinity * 28)))
        wtp = int(10 + max(0, min(15, max_affinity * 28)))
        feasibility = int(10 + max(0, min(15, max_affinity * 28)))

        # Engagement resonance bonus
        if signal.engagement_count >= 15:
            tam = min(25, tam + 2)
        if signal.engagement_count >= 50:
            tam = min(25, tam + 2)
            wtp = min(25, wtp + 2)

        total = tam + urgency + wtp + feasibility
        is_viable = total >= 70 and tam >= 12 and urgency >= 12 and wtp >= 12 and feasibility >= 12

        clean_title = re.sub(r"[^\w\s-]", "", signal.title).strip()
        if len(clean_title) > 75:
            clean_title = clean_title[:72] + "..."

        project_name = "".join(w.capitalize() for w in clean_title.split()[:3]) if is_viable else None
        project_type = "Developer Tool / Automation" if is_viable else None
        mvp_scope = (
            f"Modular MVP resolving core friction in {clean_title} with CLI/API integration." if is_viable else None
        )
        pitch = f"Autonomous developer platform addressing {clean_title}" if is_viable else None
        rejection = (
            None
            if is_viable
            else f"Semantic affinity ({max_affinity:.2f}) indicates insufficient standalone project leverage."
        )

        return OpportunityEvaluation(
            signal_id=signal.id,
            is_structural_problem=is_viable,
            tam_score=tam,
            urgency_score=urgency,
            willingness_to_pay_score=wtp,
            feasibility_score=feasibility,
            total_score=total,
            proposed_project_name=project_name,
            project_type=project_type,
            mvp_scope=mvp_scope,
            rationale=f"Tier-2 Dense Semantic Scoring: max archetype affinity {max_affinity:.2f}. Total score: {total}/100. Viable: {is_viable}.",
            suggested_pitch=pitch,
            rejection_reason=rejection,
        )

    @classmethod
    async def _evaluate_gemini(cls, signal: RawPainSignal, api_key: str) -> OpportunityEvaluation:
        """Evaluates candidate through Google Gemini 1.5 Flash via REST API."""
        prompt = cls._build_prompt(signal)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
            res_dict = cls._extract_and_parse_json(text_resp)
            return cls._parse_llm_dict(signal, res_dict, "Gemini-1.5-Flash")

    @classmethod
    async def _evaluate_openai(cls, signal: RawPainSignal, api_key: str) -> OpportunityEvaluation:
        """Evaluates candidate through OpenAI GPT-4o-mini via REST API."""
        prompt = cls._build_prompt(signal)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an elite YC/DevTool Product Architect. Always reply in valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            res_dict = cls._extract_and_parse_json(raw_text)
            return cls._parse_llm_dict(signal, res_dict, "GPT-4o-Mini")

    @classmethod
    async def _evaluate_anthropic(cls, signal: RawPainSignal, api_key: str) -> OpportunityEvaluation:
        """Evaluates candidate through Anthropic Claude 3.5 Haiku via REST API."""
        prompt = cls._build_prompt(signal)
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 800,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Anthropic API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            raw_text = data["content"][0]["text"]
            res_dict = cls._extract_and_parse_json(raw_text)
            return cls._parse_llm_dict(signal, res_dict, "Claude-3.5-Haiku")

    @classmethod
    async def _evaluate_mistral(
        cls, signal: RawPainSignal, api_key: str, model_name: str = "open-mistral-7b"
    ) -> OpportunityEvaluation:
        """Evaluates candidate through Mistral AI API using open-mistral-7b."""
        prompt = cls._build_prompt(signal)
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an elite Y-Combinator Venture Architect and Principal Developer Tooling Engineer. Always reply strictly in valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 429:
                await asyncio.sleep(2.0)
                resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Mistral API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            res_dict = cls._extract_and_parse_json(raw_text)
            return cls._parse_llm_dict(signal, res_dict, f"Mistral ({model_name})")

    @classmethod
    def _extract_and_parse_json(cls, raw_text: str) -> dict[str, Any]:
        """Robustly extracts and parses JSON from LLM output, handling markdown fences,
        trailing commas, unescaped characters, and falling back to regex key extraction if needed."""
        if not raw_text:
            raise ValueError("Empty LLM response text")

        text = raw_text.strip()

        # 1. Strip markdown fences if present
        if "```" in text:
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
            text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
            text = text.strip()

        # 2. Extract outermost JSON object candidate
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = json_match.group(0) if json_match else text

        # Attempt 1: Standard JSON parse
        try:
            return json.loads(candidate)
        except Exception:
            pass

        # Attempt 2: Clean trailing commas before closing braces/brackets
        cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # Attempt 3: Replace unescaped newlines inside strings
        def _fix_newlines(match_obj):
            s = match_obj.group(0)
            return s.replace("\n", "\\n").replace("\r", "")

        cleaned_newlines = re.sub(r'"([^"\\]*(\\.[^"\\]*)*)"', _fix_newlines, cleaned)
        try:
            return json.loads(cleaned_newlines)
        except Exception:
            pass

        # Attempt 4: Deterministic Regex-based Key Extraction fallback
        logger.info("LLMEvaluator: Attempting regex key extraction fallback for LLM response.")
        extracted: dict[str, Any] = {}

        viable_match = re.search(r'"is_viable_project"\s*:\s*(true|false)', text, re.IGNORECASE)
        if viable_match:
            extracted["is_viable_project"] = viable_match.group(1).lower() == "true"

        for score_key in ["tam_score", "urgency_score", "willingness_to_pay_score", "feasibility_score"]:
            sm = re.search(rf'"{score_key}"\s*:\s*(\d+)', text)
            if sm:
                extracted[score_key] = int(sm.group(1))

        for str_key in [
            "proposed_project_name",
            "project_type",
            "suggested_pitch",
            "mvp_scope",
            "rationale",
            "rejection_reason",
        ]:
            stm = re.search(rf'"{str_key}"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if stm:
                try:
                    extracted[str_key] = stm.group(1).encode("utf-8").decode("unicode_escape", errors="replace")
                except Exception:
                    extracted[str_key] = stm.group(1)

        if extracted.get("tam_score") is not None or extracted.get("is_viable_project") is not None:
            return extracted

        raise ValueError(f"Could not parse valid JSON or extract keys from LLM response: {raw_text[:200]}")

    @classmethod
    def _build_prompt(cls, signal: RawPainSignal) -> str:
        return f"""You are a Principal Product Architect and Venture Scout specializing in developer tools, micro-SaaS, and software utilities.

Analyze this community signal to identify if it represents a VALUABLE, STANDALONE SOFTWARE PROJECT that a small team or solo developer can build, launch, and monetize.

=== SIGNAL DETAILS ===
Source: {signal.platform.value}
Title: {signal.title}
Post Content:
{signal.content[:3500]}

=== SPECIAL GUIDANCE FOR "SHOW & TELL" / PROTOTYPE POSTS ===
Many signals come from builder communities (e.g. r/SideProject, r/microSaaS, Show HN, r/selfhosted) where developers post: "I built X", "Show HN: X", or showcase a working prototype or proof-of-concept.
For these posts:
1. RECOGNIZE THE UNDERLYING WORKFLOW FRICTION & MARKET GAP:
   Do NOT judge whether this specific author's hobby prototype has polished marketing or enterprise sales. Instead, evaluate the CORE SOFTWARE UTILITY OR WORKFLOW GAP it addresses.
   Ask: Is this prototype proving that a painful workflow (e.g. controlling devices via AI agents, validating document citations, masking credentials during screen sharing, git-native task tracking) can be automated?
2. STANDALONE PRODUCT VIABILITY:
   Could this concept (or a polished, production-grade, multi-tenant version of it) be built and monetized by a developer? (e.g., as an MCP server, CLI, desktop utility, browser extension, or micro-SaaS).
3. DO NOT DOWNVOTE INNOVATIVE PROTOTYPES AS "HOBBY":
   If a prototype solves a painful real-world workflow or unlocks a new agentic/developer paradigm, award high TAM (14-22), Urgency (14-20), and Feasibility (16-24).

=== EVALUATION CRITERIA ===
1. PROBLEM VALIDITY: Is this a genuine, recurring friction, developer productivity gap, or industry workflow need? (Reject localized single-repo bugs, syntax issues, homework, or trivial config).
2. BUILDABILITY: Can 1-2 engineers build a functional MVP within 2-4 weeks? (Prefer high-leverage tools, CLIs, micro-SaaS, API proxies, MCP servers, or workflow extensions over impossible multi-year capital-intensive megaprojects).
3. COMMERCIAL OR DEVELOPER DEMAND: Would developers or companies pay recurring fees ($15-$500/mo) or enthusiastically adopt/star this?
4. INCUMBENT CHECK: Is there room for a focused, superior standalone product, or is this already trivialized by standard native features?

=== CALIBRATED SCORING RUBRIC (0-25 each, Total 0-100) ===
- tam_score (Market Magnitude):
    0-8: Niche hobbyist curiosity or single-user quirk.
    9-16: Solid micro-SaaS / focused developer niche ($1M - $20M addressable market).
    17-25: Broad horizontal standard across modern software engineering or enterprise teams.
- urgency_score (Pain Severity):
    0-8: Mild inconvenience; easily worked around with a quick script.
    9-16: Recurring productivity drag, frequent context switching, or operational frustration.
    17-25: Production downtime, revenue loss, data risk, or severe compliance breach.
- willingness_to_pay_score (Commercial Viability):
    0-8: Expected to be free; strong user pushback against payment.
    9-16: High probability of $10-$99/mo developer/team subscription or rapid open-source adoption.
    17-25: Proven budget with willingness for $200-$2,000/mo team or enterprise tier.
- feasibility_score (Buildability & MVP Scope):
    0-8: Impractical (requires deep OS kernel changes, massive partnerships, or billions in capital).
    9-16: Moderate buildability (requires resilient background workers, reverse-engineering, or multi-protocol bridges).
    17-25: High buildability (a clean, elegant MVP can be built and deployed in 2-4 weeks).

Reply strictly with a valid JSON object matching these exact keys:
{{
  "is_viable_project": bool,
  "proposed_project_name": "Short, catchy working project name (or null if rejected)",
  "project_type": "CLI | Micro-SaaS | Browser/VSCode Extension | API Bridge | Developer Library | MCP Server (or null)",
  "tam_score": int, (0-25)
  "urgency_score": int, (0-25)
  "willingness_to_pay_score": int, (0-25)
  "feasibility_score": int, (0-25)
  "suggested_pitch": "One compelling sentence describing what to build and for whom (or null)",
  "mvp_scope": "2-3 sentence description of the minimum viable product (or null)",
  "rationale": "Strategic explanation of the evaluation and scores",
  "rejection_reason": string or null
}}"""

    @classmethod
    def _parse_llm_dict(cls, signal: RawPainSignal, data: dict[str, Any], engine_name: str) -> OpportunityEvaluation:
        def _clean_str(val: Any) -> str | None:
            if val is None:
                return None
            if isinstance(val, dict):
                return " ".join(str(v) for v in val.values()).strip() or None
            if isinstance(val, list):
                return " ".join(str(v) for v in val).strip() or None
            s = str(val).strip()
            return s if s else None

        tam = max(0, min(25, int(data.get("tam_score", 10))))
        urgency = max(0, min(25, int(data.get("urgency_score", 10))))
        wtp = max(0, min(25, int(data.get("willingness_to_pay_score", 10))))
        feasibility = max(0, min(25, int(data.get("feasibility_score", 10))))
        total = tam + urgency + wtp + feasibility

        explicit_viable = data.get("is_viable_project")
        if explicit_viable is not None:
            is_viable = (
                bool(explicit_viable)
                and total >= 70
                and tam >= 10
                and urgency >= 10
                and wtp >= 10
                and feasibility >= 10
            )
        else:
            is_viable = total >= 70 and tam >= 12 and urgency >= 12 and wtp >= 12 and feasibility >= 12

        project_name = _clean_str(data.get("proposed_project_name"))
        project_type = _clean_str(data.get("project_type"))
        mvp_scope = _clean_str(data.get("mvp_scope"))
        pitch = _clean_str(data.get("suggested_pitch"))
        rejection = _clean_str(data.get("rejection_reason"))

        if not is_viable and not rejection:
            rejection = f"Total score ({total}/100) or dimension balance below qualification threshold."

        raw_rationale = data.get("rationale", "Evaluated via LLM reasoning.")
        if isinstance(raw_rationale, (dict, list)):
            raw_rationale = json.dumps(raw_rationale)
        rationale = f"Tier-2 LLM ({engine_name}): {raw_rationale}"

        return OpportunityEvaluation(
            signal_id=signal.id,
            is_structural_problem=is_viable,
            tam_score=tam,
            urgency_score=urgency,
            willingness_to_pay_score=wtp,
            feasibility_score=feasibility,
            total_score=total,
            proposed_project_name=project_name,
            project_type=project_type,
            mvp_scope=mvp_scope,
            rationale=rationale,
            suggested_pitch=pitch,
            rejection_reason=rejection,
        )
