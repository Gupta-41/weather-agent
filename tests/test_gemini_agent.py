from types import SimpleNamespace

from google.genai import types

from backend.agent.gemini_agent import run_agent
from backend.agent.gemini_tools import build_tools, to_function_declaration
from backend.tools.registry import TOOL_DEFINITIONS


def usage(prompt=100, candidates=20):
    return SimpleNamespace(prompt_token_count=prompt, candidates_token_count=candidates)


def gemini_response(parts, finish_reason="STOP", tokens=usage()):
    """Shape a fake google-genai response: response.candidates[0].content.parts"""
    content = types.Content(role="model", parts=parts)
    candidate = SimpleNamespace(content=content, finish_reason=finish_reason)
    return SimpleNamespace(candidates=[candidate], usage_metadata=tokens)


def text_part(text):
    return types.Part.from_text(text=text)


def call_part(name, args):
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


class FakeGemini:
    """Mimics client.aio.models.generate_content, one scripted response per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.aio = SimpleNamespace(models=self)

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def test_tool_conversion_maps_types_and_nesting():
    declaration = to_function_declaration(TOOL_DEFINITIONS[1])  # get_forecast
    assert declaration.name == "get_forecast"
    props = declaration.parameters.properties
    assert props["location"].type == types.Type.STRING
    assert props["days"].type == types.Type.INTEGER


def test_build_tools_wraps_every_definition():
    tools = build_tools(TOOL_DEFINITIONS)
    names = {fn.name for fn in tools[0].function_declarations}
    assert names == {t["name"] for t in TOOL_DEFINITIONS}


async def test_agent_picks_a_tool_and_records_the_trace(http):
    llm = FakeGemini(
        [
            gemini_response(
                [
                    text_part("Using get_current_weather for right now."),
                    call_part("get_current_weather", {"location": "Paris, France"}),
                ]
            ),
            gemini_response([text_part("It's 24.5°C and partly cloudy in Paris.")]),
        ]
    )

    result = await run_agent(llm=llm, http=http, message="Weather in Paris?")

    assert result.reply == "It's 24.5°C and partly cloudy in Paris."
    steps = result.trace.steps
    assert [s.decision for s in steps] == ["use_tools", "final_answer"]
    assert "get_current_weather" in steps[0].model_text
    call = steps[0].tool_calls[0]
    assert (call.tool, call.ok, call.input) == (
        "get_current_weather",
        True,
        {"location": "Paris, France"},
    )
    assert steps[0].input_tokens == 100


async def test_failed_tool_call_is_reported_back_and_in_the_trace(http):
    llm = FakeGemini(
        [
            gemini_response([call_part("get_current_weather", {"location": "Nowhereville"})]),
            gemini_response([text_part("I couldn't find that place.")]),
        ]
    )

    result = await run_agent(llm=llm, http=http, message="Weather in Nowhereville?")

    call = result.trace.steps[0].tool_calls[0]
    assert call.ok is False and "No location found" in call.error
    assert result.reply == "I couldn't find that place."


async def test_two_tools_in_one_step(http):
    llm = FakeGemini(
        [
            gemini_response(
                [
                    call_part("get_current_weather", {"location": "Paris"}),
                    call_part("get_forecast", {"location": "Paris", "days": 2}),
                ]
            ),
            gemini_response([text_part("Done.")]),
        ]
    )
    result = await run_agent(llm=llm, http=http, message="Now and tomorrow?")
    assert [c.tool for c in result.trace.steps[0].tool_calls] == [
        "get_current_weather",
        "get_forecast",
    ]


async def test_step_limit_stops_and_translates(http):
    looping = gemini_response([call_part("get_current_weather", {"location": "Paris"})])
    llm = FakeGemini([looping, looping])
    result = await run_agent(llm=llm, http=http, message="loop", max_steps=2, language="hi")
    assert result.trace.steps[-1].decision == "stopped"
    assert "step limit" not in result.reply


async def test_trace_records_the_requested_language(http):
    llm = FakeGemini([gemini_response([text_part("नमस्ते")])])
    result = await run_agent(llm=llm, http=http, message="नमस्ते", language="hi-IN")
    assert result.trace.language == "hi"
