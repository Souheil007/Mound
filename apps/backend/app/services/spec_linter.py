"""Deterministic quality, security, and evidence linter for BlueprintSpec submissions."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from app.schemas.blueprint_spec import BlueprintSpec

# Dangerous command injection and arbitrary script patterns
DANGEROUS_PATTERNS = [
    r"curl\s+[^|\n]+\|\s*(bash|sh)",
    r"wget\s+[^|\n]+\|\s*(bash|sh)",
    r"rm\s+-rf\s+(/|/\*)",
    r"powershell(\.exe)?\s+(-enc|-c|iex)",
    r"<script[\s>]",
    r"<iframe[\s>]",
    r"javascript:\s*",
    r"uses:\s*actions/[a-zA-Z0-9_-]+@[a-zA-Z0-9._-]+",
]

# Fluff phrases that indicate vague, non-verifiable deliverables
FLUFF_PHRASES = [
    "improve user experience",
    "make it fast and scalable",
    "follow best practices",
    "user friendly interface",
    "clean code",
    "easy to use",
    "great performance",
    "modern design",
]

# Recognized developer authority domains that may rate-limit or bot-block automated probes
AUTHORITY_DOMAINS = {
    "github.com",
    "news.ycombinator.com",
    "arxiv.org",
    "reddit.com",
    "stackoverflow.com",
    "lobste.rs",
    "ietf.org",
    "w3.org",
}


@dataclass
class LintResult:
    """Outcome of spec linting execution."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SpecLinter:
    """Deterministic quality and security linter executed prior to blueprint persistence."""

    @classmethod
    async def verify_evidence_urls(
        cls,
        urls: list[str],
        timeout_seconds: float = 3.0,
    ) -> tuple[int, list[str]]:
        """Probes evidence URLs to ensure at least one is reachable.

        Args:
            urls: List of URL strings from spec.evidence_sources.
            timeout_seconds: Strict timeout per probe (default 3.0s).

        Returns:
            A tuple of (reachable_count, list_of_unreachable_urls).
        """
        reachable_count = 0
        unreachable: list[str] = []

        headers = {
            "User-Agent": "MoundBot/1.0 (+https://mound.dev; verify-url)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            for url_str in urls:
                try:
                    parsed = urlparse(url_str)
                    domain = parsed.netloc.lower()
                    if ":" in domain:
                        domain = domain.split(":")[0]

                    # Send lightweight HEAD first, fallback to GET if 405 Method Not Allowed
                    try:
                        resp = await client.head(url_str, headers=headers)
                        status_code = resp.status_code
                        if status_code == 405:
                            resp = await client.get(url_str, headers=headers)
                            status_code = resp.status_code
                    except httpx.HTTPError:
                        resp = await client.get(url_str, headers=headers)
                        status_code = resp.status_code

                    # Evaluate reachability
                    is_authority = any(domain.endswith(auth_d) for auth_d in AUTHORITY_DOMAINS)

                    if 200 <= status_code < 400:
                        reachable_count += 1
                    elif is_authority and status_code in (403, 405, 429):
                        # Known authority site returning bot mitigation or HEAD blocking; considered reachable
                        reachable_count += 1
                    else:
                        unreachable.append(f"{url_str} (HTTP {status_code})")

                except Exception as exc:
                    unreachable.append(f"{url_str} ({type(exc).__name__})")

        return reachable_count, unreachable

    @classmethod
    def check_script_sanitization(cls, text_corpus: str) -> list[str]:
        """Scans text for command injection, raw shell scripts, or CI/CD workflow YAML.

        Args:
            text_corpus: Aggregated text content of the blueprint specification.

        Returns:
            List of detected security violation error messages.
        """
        errors = []
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, text_corpus, re.IGNORECASE):
                errors.append(f"Security violation: Detected disallowed script or command pattern '{pattern}'.")
        return errors

    @classmethod
    def check_fluff_deliverables(cls, deliverables: list[str], criteria: list[str]) -> list[str]:
        """Verifies that deliverables and criteria contain concrete verifiable statements.

        Args:
            deliverables: List of core deliverables.
            criteria: List of acceptance criteria.

        Returns:
            List of fluff warning/error messages.
        """
        errors = []
        for item in deliverables + criteria:
            clean_item = item.strip().lower()
            for fluff in FLUFF_PHRASES:
                if clean_item == fluff or clean_item.startswith(f"{fluff}."):
                    errors.append(
                        f"Vague deliverable rejected: '{item}'. Provide concrete, verifiable technical deliverables."
                    )
        return errors

    @classmethod
    async def lint(
        cls,
        spec: BlueprintSpec,
        skip_url_verification: bool = False,
    ) -> LintResult:
        """Runs the complete linter suite against an incoming BlueprintSpec.

        Args:
            spec: The validated BlueprintSpec instance.
            skip_url_verification: Option to bypass network URL probes (e.g. for offline tests).

        Returns:
            LintResult with pass/fail status and collected errors.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Script & Injection Sanitization
        stack_desc = (
            f"{spec.suggested_stack.language} "
            f"{' '.join(spec.suggested_stack.core_libraries)} "
            f"{spec.suggested_stack.storage}"
        )
        text_corpus = (
            f"{spec.one_line_pitch}\n"
            f"{spec.problem_statement}\n"
            f"{spec.proposed_solution}\n"
            f"{' '.join(spec.mvp_deliverables)}\n"
            f"{' '.join(spec.explicit_non_goals)}\n"
            f"{' '.join(spec.acceptance_criteria)}\n"
            f"{stack_desc}"
        )

        script_errors = cls.check_script_sanitization(text_corpus)
        errors.extend(script_errors)

        # 2. Fluff & Vague Deliverable Filter
        fluff_errors = cls.check_fluff_deliverables(spec.mvp_deliverables, spec.acceptance_criteria)
        errors.extend(fluff_errors)

        # 3. Evidence URL Probe
        from app.core.config import settings

        should_verify_urls = (
            not skip_url_verification and settings.evidence_url_verification_enabled and bool(spec.pain_evidence_urls)
        )
        if should_verify_urls:
            urls = [str(u) for u in spec.pain_evidence_urls]
            reachable_count, unreachable = await cls.verify_evidence_urls(urls)
            if unreachable:
                errors.append(
                    f"Evidence URL verification failed: {', '.join(unreachable)}. "
                    "Every verified pain link must be an active, reachable URL (HTTP 200-399)."
                )

        return LintResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
