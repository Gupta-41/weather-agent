"""The agent loop, run on Gemini instead of Claude.

Runs against the same TOOL_DEFINITIONS, produces the same AgentResult and the
same Trace shape as backend/agent/agent.py, so nothing downstream — the API
route, the trace UI, the tests — needs to know which model actually answered.
Only the wire format for a model call and a tool result differs, which is
exactly what this module isolates.
"""

import time
from dataclasses import dataclass

from google.genai import types

from backend import config
from backend.agent.agent import STEP_LIMIT_REPLY, build_system_prompt
from backend.agent.gemini_tools import build_tools
from backend.agent.trace import ToolCallTrace, Trace, TraceStep, preview
from backend.languages import normalize
from backend.tools.registry import TOOL_DEFINITIONS, TOOL_NAMES, run_tool


@dataclass
class AgentResult:
    reply: str
    trace: Trace


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _to_contents(history: list[dict], message: str) -> list[types.Content]:
    contents = [
        types.Content(
            role="model" if turn["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=turn["content"])],
        )
        for turn in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))
    return contents


async def _execute_call(name: str, args: dict, http):
    call = ToolCallTrace(tool_use_id=name, tool=name, input=dict(args))
    start = time.perf_counter()
    try:
        result = await run_tool(name, dict(args), http)
        call.result_preview = preview(result)
        part = types.Part.from_function_response(name=name, response={"result": result})
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        call.ok = False
        call.error = message
        part = types.Part.from_function_response(name=name, response={"error": message})
    call.duration_ms = _ms(start)
    return call, part


async def run_agent(
    *,
    llm,
    http,
    message: str,
    history: list[dict] | None = None,
    language: str = "en",
    model: str | None = None,
    max_steps: int | None = None,
) -> AgentResult:
    model = model or config.GEMINI_MODEL
    max_steps = max_steps or config.MAX_AGENT_STEPS
    language = normalize(language)

    contents = _to_contents(history or [], message)
    tools = build_tools(TOOL_DEFINITIONS)
    gen_config = types.GenerateContentConfig(
        system_instruction=build_system_prompt(language),
        tools=tools,
        max_output_tokens=1024,
    )

    trace = Trace(model=model, language=language)
    run_start = time.perf_counter()
    reply = ""

    for step_no in range(1, max_steps + 1):
        call_start = time.perf_counter()
        response = await llm.aio.models.generate_content(
            model=model, contents=contents, config=gen_config
        )
        candidate = response.candidates[0]
        parts = candidate.content.parts or []

        text = "".join(p.text for p in parts if getattr(p, "text", None)).strip()
        function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

        usage = getattr(response, "usage_metadata", None)
        step = TraceStep(
            step=step_no,
            available_tools=TOOL_NAMES,
            model_text=text,
            stop_reason=str(getattr(candidate, "finish_reason", None)),
            model_latency_ms=_ms(call_start),
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
        trace.steps.append(step)

        if not function_calls:
            step.decision = "final_answer"
            reply = text
            break

        step.decision = "use_tools"
        contents.append(candidate.content)

        calls, response_parts = [], []
        for fc in function_calls:
            call, part = await _execute_call(fc.name, dict(fc.args or {}), http)
            calls.append(call)
            response_parts.append(part)

        step.tool_calls = calls
        contents.append(types.Content(role="user", parts=response_parts))
    else:
        if trace.steps:
            trace.steps[-1].decision = "stopped"
        reply = STEP_LIMIT_REPLY.get(language, STEP_LIMIT_REPLY["en"])

    trace.total_ms = _ms(run_start)
    return AgentResult(reply=reply, trace=trace)
