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
    "Autonomous AI agent governance, tool calling harness, prompt drift detection, context window management, and Model Context Protocol servers",
    "High-availability distributed database proxy, connection pool multiplexer, adaptive backpressure coordinator, and failover circuit breaker",
    "High-leverage standalone developer productivity tool, CLI utility, SDK generator, API gateway proxy, and workflow orchestration engine",
    "Automated zero-day CVE vulnerability scanner, exploit surface auditor for agencies, and continuous infrastructure compliance monitor",
    "SaaS external dependency sentinel, cloud quota and billing alert governor, and synthetic golden-path health check agent",
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
            if not key:
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
        is_viable = total >= 65 and tam >= 12 and urgency >= 12 and wtp >= 12 and feasibility >= 12

        clean_title = re.sub(r"[^\w\s-]", "", signal.title).strip()
        if len(clean_title) > 75:
            clean_title = clean_title[:72] + "..."

        pitch = f"Autonomous developer platform addressing {clean_title}" if is_viable else None
        rejection = None if is_viable else f"Semantic affinity ({max_affinity:.2f}) indicates insufficient standalone project leverage."

        return OpportunityEvaluation(
            signal_id=signal.id,
            is_structural_problem=is_viable,
            tam_score=tam,
            urgency_score=urgency,
            willingness_to_pay_score=wtp,
            feasibility_score=feasibility,
            total_score=total,
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
            res_dict = json.loads(text_resp)
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
                {"role": "system", "content": "You are an elite YC/DevTool Product Architect. Always reply in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            res_dict = json.loads(data["choices"][0]["message"]["content"])
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
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            res_dict = json.loads(match.group(0)) if match else json.loads(raw_text)
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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Mistral API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            res_dict = json.loads(match.group(0)) if match else json.loads(raw_text)
            return cls._parse_llm_dict(signal, res_dict, f"Mistral ({model_name})")

    @classmethod
    def _build_prompt(cls, signal: RawPainSignal) -> str:
        return f"""You are an elite Y-Combinator Venture Architect and Principal Developer Tooling Engineer.
Evaluate this community pain signal to determine if it represents an INNOVATIVE, STANDALONE SOFTWARE PROJECT (devtool, AI agent harness, micro-SaaS, or CLI).

Do NOT accept single-repo bug reports, syntax errors, or localized repository maintenance chores.
Look for:
1. Novelty & Modern Tech Leverage (autonomous agents, MCP, RAG, devtools, privacy-first, workflow automation).
2. Standalone Solvability (Can an engineer build this as an independent tool/SaaS?).
3. Commercial & Developer Demand (Would people pay or star this?).

Title: {signal.title}
Platform: {signal.platform.value}
Content:
{signal.content[:1000]}

Reply strictly with a JSON object with these exact keys:
{{
  "is_viable_project": bool,
  "tam_score": int, (0-25)
  "urgency_score": int, (0-25)
  "willingness_to_pay_score": int, (0-25)
  "feasibility_score": int, (0-25)
  "suggested_pitch": string or null,
  "rationale": string,
  "rejection_reason": string or null
}}"""

    @classmethod
    def _parse_llm_dict(cls, signal: RawPainSignal, data: dict[str, Any], engine_name: str) -> OpportunityEvaluation:
        tam = max(0, min(25, int(data.get("tam_score", 10))))
        urgency = max(0, min(25, int(data.get("urgency_score", 10))))
        wtp = max(0, min(25, int(data.get("willingness_to_pay_score", 10))))
        feasibility = max(0, min(25, int(data.get("feasibility_score", 10))))
        total = tam + urgency + wtp + feasibility

        is_viable = bool(data.get("is_viable_project", total >= 65))
        pitch = data.get("suggested_pitch")
        rationale = f"Tier-2 LLM ({engine_name}): {data.get('rationale', 'Evaluated via LLM reasoning.')}"
        rejection = data.get("rejection_reason")

        return OpportunityEvaluation(
            signal_id=signal.id,
            is_structural_problem=is_viable,
            tam_score=tam,
            urgency_score=urgency,
            willingness_to_pay_score=wtp,
            feasibility_score=feasibility,
            total_score=total,
            rationale=rationale,
            suggested_pitch=pitch,
            rejection_reason=rejection,
        )
