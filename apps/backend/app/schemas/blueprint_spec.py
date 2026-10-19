"""Strict validation schemas for project blueprints."""

from pydantic import BaseModel, Field, HttpUrl


class SuggestedStack(BaseModel):
    """Recommended tech stack and architectural reasoning."""

    language: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Primary programming language or runtime.",
        examples=["Python 3.12 or Rust"],
    )
    core_libraries: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Key libraries or frameworks recommended for implementation.",
        examples=[["anyio", "pydantic-v2", "typer"]],
    )
    storage: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Persistence strategy or database choice.",
        examples=["Local JSONL cassettes"],
    )


class BlueprintSpec(BaseModel):
    """The canonical, strictly-validated specification contract for project blueprints."""

    one_line_pitch: str = Field(
        ...,
        min_length=50,
        max_length=140,
        description="Concise, high-signal summary of the project.",
        examples=["Local CLI proxy that records, sanitizes, and replays deterministic MCP tool calls for CI testing"],
    )
    domain_tags: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Category tags (e.g., cli-tools, devtools, testing).",
        examples=[["cli-tools", "mcp", "testing", "devtools"]],
    )
    pain_evidence_urls: list[HttpUrl] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Links to real-world developer complaints, issues, or discussions.",
        examples=[["https://github.com/modelcontextprotocol/servers/issues/412"]],
    )
    problem_statement: str = Field(
        ...,
        min_length=100,
        max_length=600,
        description="Detailed description of the broken workflow or pain point.",
        examples=[
            "Developers building MCP-enabled agents cannot run deterministic integration tests in CI because "
            "external MCP servers require live API keys, hit rate limits, and return non-deterministic payloads."
        ],
    )
    target_persona: str = Field(
        ...,
        min_length=50,
        max_length=250,
        description="Who experiences this problem and needs this tool.",
        examples=["Backend and AI engineers running automated pytest/vitest suites against MCP tool servers."],
    )
    mvp_deliverables: list[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="Concrete functional capabilities delivered in v1.",
        examples=[
            [
                "Transparent stdio and SSE proxy that intercepts JSON-RPC 2.0 traffic between host and MCP server",
                "Automatic secret scrubbing before writing cassette files to disk",
                "Zero-network replay mode with strict schema matching",
            ]
        ],
    )
    explicit_non_goals: list[str] = Field(
        ...,
        min_length=2,
        max_length=4,
        description="Deliberately excluded features and out-of-scope boundaries.",
        examples=[
            [
                "No hosted cloud dashboard or team billing in v1",
                "Does not mock LLM inference responses—strictly scopes to MCP tool cassettes",
            ]
        ],
    )
    suggested_stack: SuggestedStack = Field(
        ...,
        description="Recommended language, libraries, and storage strategy.",
    )
    acceptance_criteria: list[str] = Field(
        ...,
        min_length=3,
        max_length=6,
        description="Verifiable automated test conditions determining completion.",
        examples=[
            [
                "Proxy adds less than 5ms overhead in recording mode over stdio transport",
                "100% of environment variables matching *_KEY or *_TOKEN are redacted",
                "Replay mode exits with non-zero code if agent emits unexpected arguments",
            ]
        ],
    )
