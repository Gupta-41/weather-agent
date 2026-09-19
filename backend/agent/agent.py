import asyncio
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from backend import config
from backend.agent.trace import ToolCallTrace, Trace, TraceStep, preview
from backend.languages import language_name, normalize
from backend.tools.registry import TOOL_DEFINITIONS, TOOL_NAMES, run_tool

BASE_PROMPT = """You are WeatherGPT, a weather assistant. You can only get weather data through your tools, so never invent conditions or numbers.

Before you call any tool, write one short sentence saying which tool you are choosing and why.

Choosing a tool:
- get_current_weather: conditions right now.
- get_forecast: today through the next 16 days — tomorrow, the weekend, planning questions.
- get_weather_alerts: when the user asks whether it is safe, whether there is a warning, or about a storm. It returns written warnings with safety advice; pass the user's language code so the advice comes back in their language.
- get_historical_weather: what the weather actually was over a past date range.
- get_climate_trend: whether a place is getting hotter, wetter or drier over many years.
- If a question needs more than one, call them together in the same turn.

Rules:
- Today is {today}. Work out any date the user implies ("last month", "the 2023 monsoon") from that and pass explicit YYYY-MM-DD dates.
- The historical archive lags about five days. For today, yesterday and the day before, use get_forecast.
- If the user has not named a place and none was mentioned earlier in the conversation, ask which location they mean instead of guessing.
- Use metric units unless the user asks for imperial or uses °F or mph.
- When a tool returns an alert, lead with it. Safety information goes before small talk.

{language_rule}

Keep answers concise and practical."""

ENGLISH_RULE = "Answer in English."

OTHER_LANGUAGE_RULE = (
    "Answer entirely in {name}, including numbers with their units and any "
    "place names that have a common form in that language. Do not add an "
    "English translation unless the user asks for one. Your one-sentence "
    "tool-choice explanation may stay in English — it is for the trace panel, "
    "not the user."
)


def build_system_prompt(language: str = "en", today: str | None = None) -> str:
    code = normalize(language)
    rule = (
        ENGLISH_RULE
        if code == "en"
        else OTHER_LANGUAGE_RULE.format(name=language_name(code))
    )
    return BASE_PROMPT.format(
        today=today or date.today().isoformat(), language_rule=rule
    )


STEP_LIMIT_REPLY = {
    "en": (
        "I wasn't able to finish that within my step limit. "
        "Could you try a simpler or more specific question?"
    ),
    "hi": (
        "मैं तय चरणों में यह पूरा नहीं कर सका। "
        "क्या आप सवाल को थोड़ा सरल या अधिक स्पष्ट पूछ सकते हैं?"
    ),
    "te": (
        "నిర్ణీత దశల్లో దీన్ని పూర్తి చేయలేకపోయాను. "
        "ప్రశ్నను కొంచెం సులభంగా లేదా మరింత స్పష్టంగా అడగగలరా?"
    ),
}


@dataclass
class AgentResult:
    reply: str
    trace: Trace


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


async def _execute_tool(tool_use: Any, http: httpx.AsyncClient):
    """Run one tool call. Failures go back to the model as error results."""
    call = ToolCallTrace(
        tool_use_id=tool_use.id, tool=tool_use.name, input=dict(tool_use.input)
    )
    start = time.perf_counter()
    try:
        result = await run_tool(tool_use.name, dict(tool_use.input), http)
        call.result_preview = preview(result)
        block = {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": json.dumps(result, ensure_ascii=False),
        }
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        call.ok = False
        call.error = message
        block = {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": f"Error: {message}",
            "is_error": True,
        }
    call.duration_ms = _ms(start)
    return call, block


async def run_agent(
    *,
    llm: Any,
    http: httpx.AsyncClient,
    message: str,
    history: list[dict] | None = None,
    language: str = "en",
    model: str = config.ANTHROPIC_MODEL,
    max_steps: int = config.MAX_AGENT_STEPS,
) -> AgentResult:
    messages: list[dict] = [*(history or []), {"role": "user", "content": message}]
    language = normalize(language)
    system_prompt = build_system_prompt(language)
    trace = Trace(model=model, language=language)
    tool_names = TOOL_NAMES
    run_start = time.perf_counter()
    reply = ""

    for step_no in range(1, max_steps + 1):
        call_start = time.perf_counter()
        response = await llm.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        step = TraceStep(
            step=step_no,
            available_tools=tool_names,
            model_text=text,
            stop_reason=response.stop_reason,
            model_latency_ms=_ms(call_start),
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
        )
        trace.steps.append(step)

        if not tool_uses:
            step.decision = "final_answer"
            reply = text
            break

        step.decision = "use_tools"
        messages.append({"role": "assistant", "content": response.content})
        outcomes = await asyncio.gather(*(_execute_tool(tu, http) for tu in tool_uses))
        step.tool_calls = [call for call, _ in outcomes]
        messages.append({"role": "user", "content": [block for _, block in outcomes]})
    else:
        if trace.steps:
            trace.steps[-1].decision = "stopped"
        reply = STEP_LIMIT_REPLY.get(language, STEP_LIMIT_REPLY["en"])

    trace.total_ms = _ms(run_start)
    return AgentResult(reply=reply, trace=trace)
