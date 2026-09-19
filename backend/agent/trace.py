"""Tool Selection Trace: a structured record of every decision the agent made.

One TraceStep per model call. It captures which tools the model could choose
from, what it said about its choice, which tools it actually picked (with
inputs), how each call went, and timing/token usage. The whole thing is
JSON-serializable so the UI can render it directly.
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Any


def preview(obj: Any, limit: int = 300) -> str:
    text = json.dumps(obj, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


@dataclass
class ToolCallTrace:
    tool_use_id: str
    tool: str
    input: dict[str, Any]
    ok: bool = True
    duration_ms: int = 0
    result_preview: str = ""
    error: str | None = None


@dataclass
class TraceStep:
    step: int
    available_tools: list[str]
    model_text: str = ""
    decision: str = "final_answer"  # "use_tools" | "final_answer" | "stopped"
    stop_reason: str | None = None
    tool_calls: list[ToolCallTrace] = field(default_factory=list)
    model_latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass
class Trace:
    model: str
    language: str = "en"
    steps: list[TraceStep] = field(default_factory=list)
    total_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
