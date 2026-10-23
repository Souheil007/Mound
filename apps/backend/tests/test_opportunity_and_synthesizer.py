"""Tests verifying the strict Billion-Dollar Opportunity Rubric and Dynamic Domain Synthesizer."""

import pytest
from app.scouts.models import PlatformSource, RawPainSignal
from app.services.opportunity_evaluator import OpportunityEvaluator
from app.services.scout_synthesizer import ScoutSynthesizer
from app.services.spec_linter import SpecLinter


def test_rejects_cypress_iframe_issue():
    signal = RawPainSignal(
        id="cypress_136",
        platform=PlatformSource.GITHUB,
        title="Iframe support",
        content="Currently the Test Runner does not support selecting or accessing elements from within an iframe.",
        author="brian-mann",
        url="https://github.com/cypress-io/cypress/issues/136",
        engagement_count=500,
    )
    evaluation = OpportunityEvaluator.evaluate(signal)
    assert not evaluation.is_structural_problem
    assert "disqualified" in evaluation.rationale.lower() or "failed" in evaluation.rejection_reason.lower()


def test_rejects_php_language_flame_war():
    signal = RawPainSignal(
        id="hn_php_2019",
        platform=PlatformSource.HACKERNEWS,
        title="PHP in 2019",
        content="Crystal is cool, but it is still immature in terms of ecosystem, the language could change.",
        author="bin0",
        url="https://news.ycombinator.com/item?id=12345",
        engagement_count=15,
    )
    evaluation = OpportunityEvaluator.evaluate(signal)
    assert not evaluation.is_structural_problem


def test_rejects_consumer_pricing_complaint():
    signal = RawPainSignal(
        id="reddit_claude_pricing",
        platform=PlatformSource.REDDIT,
        title="Pricing in India is ridiculous for Claude Pro",
        content="I can't afford $20 a month in India for Claude Pro subscription. Why is there no student discount?",
        author="dev_user",
        url="https://reddit.com/r/SaaS/comments/xyz123",
        engagement_count=120,
    )
    evaluation = OpportunityEvaluator.evaluate(signal)
    assert not evaluation.is_structural_problem


def test_rejects_show_hn_side_project():
    signal = RawPainSignal(
        id="hn_show_hn",
        platform=PlatformSource.HACKERNEWS,
        title="Show HN: I built a catalog of cloud architecture diagrams",
        content="Check out my new project where I catalog cloud architecture diagrams. Feedback on my landing page welcome!",
        author="digitalsanctum",
        url="https://news.ycombinator.com/item?id=56789",
        engagement_count=80,
    )
    evaluation = OpportunityEvaluator.evaluate(signal)
    assert not evaluation.is_structural_problem


def test_qualifies_enterprise_finops_agony():
    signal = RawPainSignal(
        id="finops_disaster",
        platform=PlatformSource.REDDIT,
        title="Our AWS cloud bill and Snowflake cost exploded by $45,000 this month due to unallocated compute and egress waste",
        content=(
            "Our enterprise infrastructure team is drowning in cloud infrastructure spend leaks. We have dozens of Kubernetes "
            "clusters in AWS with thousands of dollars wasted every month on idle compute, unattached EBS volumes, and runaway egress costs. "
            "Our engineering org is spending weeks in manual spreadsheet triage trying to trace costs per tenant. "
            "We have an approved procurement budget and need an autonomous policy enforcement proxy that can intercept provisioning and rightsize instances."
        ),
        author="director_of_infra",
        url="https://reddit.com/r/devops/comments/finops123",
        engagement_count=145,
    )
    evaluation = OpportunityEvaluator.evaluate(signal)
    assert evaluation.is_structural_problem
    assert evaluation.total_score >= 82
    assert evaluation.tam_score >= 18
    assert evaluation.urgency_score >= 18
    assert evaluation.willingness_to_pay_score >= 18
    assert evaluation.feasibility_score >= 18

    # Now verify ScoutSynthesizer generates domain-specific deliverables and no raw quotes
    spec = ScoutSynthesizer.synthesize_spec(signal, evaluation)
    assert "finops" in spec.domain_tags or "cloud-cost" in spec.domain_tags
    assert "As reported by" not in spec.problem_statement
    assert "director_of_infra" not in spec.problem_statement
    assert len(spec.problem_statement) >= 100
    assert len(spec.problem_statement) <= 600

    # Verify deliverables are specifically FinOps/compute oriented, not generic
    assert any("ebpf" in d.lower() or "compute" in d.lower() or "rightsizing" in d.lower() for d in spec.mvp_deliverables)
    # Verify acceptance criteria have concrete percentages / latencies
    assert any("30%" in a or "latency" in a for a in spec.acceptance_criteria)


def test_qualifies_distributed_systems_connection_failure():
    signal = RawPainSignal(
        id="postgres_pool_failover",
        platform=PlatformSource.HACKERNEWS,
        title="PostgreSQL connection pool exhaustion caused a 3-hour cascading production outage and data loss",
        content=(
            "Our multi-tenant database cluster experienced catastrophic connection pool exhaustion when our primary node failed over. "
            "The sudden thundering herd of client connections caused cascading distributed deadlocks across all microservices, leading to an SLA breach "
            "and thousands of dollars lost during the outage. Our infrastructure team desperately needs a zero-copy distributed proxy "
            "with consensus-backed backpressure and automated circuit breakers to manage database connections during failover."
        ),
        author="sre_principal",
        url="https://news.ycombinator.com/item?id=998877",
        engagement_count=210,
    )
    evaluation = OpportunityEvaluator.evaluate(signal)
    assert evaluation.is_structural_problem
    assert evaluation.total_score >= 82

    spec = ScoutSynthesizer.synthesize_spec(signal, evaluation)
    assert "distributed-systems" in spec.domain_tags or "high-availability" in spec.domain_tags
    assert "As reported by" not in spec.problem_statement
    assert "sre_principal" not in spec.problem_statement

    # Check deliverables are specifically distributed systems / connection pooling
    assert any("connection" in d.lower() or "backpressure" in d.lower() for d in spec.mvp_deliverables)
    assert any("50,000" in a or "failover" in a for a in spec.acceptance_criteria)


@pytest.mark.asyncio
async def test_synthesized_spec_passes_strict_linter():
    signal = RawPainSignal(
        id="soc2_audit_nightmare",
        platform=PlatformSource.REDDIT,
        title="Failed our enterprise SOC2 audit due to IAM privilege creep and unencrypted cloud storage",
        content=(
            "Our enterprise organization suffered a major compliance audit failure under SOC2 Trust Services Criteria. "
            "Manual spreadsheets and point-in-time screenshots failed to detect continuous IAM privilege drift and standing admin access. "
            "Our CISO and compliance team need continuous autonomous policy enforcement and cryptographic audit ledgers to guarantee compliance."
        ),
        author="ciso_enterprise",
        url="https://reddit.com/r/SaaS/comments/soc2audit",
        engagement_count=85,
    )
    evaluation = OpportunityEvaluator.evaluate(signal)
    assert evaluation.is_structural_problem
    spec = ScoutSynthesizer.synthesize_spec(signal, evaluation)

    # Pass through strict linter (skip network url check in unit test)
    lint_res = await SpecLinter.lint(spec, skip_url_verification=True)
    assert lint_res.passed
    assert len(lint_res.errors) == 0


@pytest.mark.asyncio
async def test_mistral_llm_evaluator_with_open_mistral_7b(monkeypatch):
    """Verifies Mistral LLM evaluation with model open-mistral-7b."""
    from unittest.mock import AsyncMock, MagicMock
    from app.services.llm_evaluator import LLMEvaluator
    from app.core.config import settings
    import httpx

    signal = RawPainSignal(
        id="mistral_test_signal",
        platform=PlatformSource.HACKERNEWS,
        title="OpenShell – A safe, private runtime for fleets of autonomous AI agents",
        content="Autonomous agents require sandboxed isolation harnesses and tool permissions.",
        author="agent_dev",
        url="https://news.ycombinator.com/item?id=50204791",
        engagement_count=42,
    )

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"is_viable_project": true, "tam_score": 24, "urgency_score": 23, '
                        '"willingness_to_pay_score": 22, "feasibility_score": 23, '
                        '"suggested_pitch": "Sandboxed runtime for autonomous AI agents", '
                        '"rationale": "High-leverage enterprise agent infrastructure.", '
                        '"rejection_reason": null}'
                    )
                }
            }
        ]
    }

    async def mock_post(self, url, **kwargs):
        assert url == "https://api.mistral.ai/v1/chat/completions"
        assert kwargs["json"]["model"] == "open-mistral-7b"
        assert kwargs["headers"]["Authorization"] == "Bearer mock_mistral_key"
        return mock_response

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(settings, "llm_provider", "mistral")
    monkeypatch.setattr(settings, "mistral_api_key", "mock_mistral_key")
    monkeypatch.setattr(settings, "mistral_model", "open-mistral-7b")

    eval_result = await LLMEvaluator.evaluate_candidate(signal)

    assert eval_result.is_structural_problem is True
    assert eval_result.total_score == 92
    assert eval_result.tam_score == 24
    assert eval_result.urgency_score == 23
    assert eval_result.willingness_to_pay_score == 22
    assert eval_result.feasibility_score == 23
    assert "Mistral" in eval_result.rationale
    assert eval_result.suggested_pitch == "Sandboxed runtime for autonomous AI agents"

