from backend.agent.agent import build_system_prompt, run_agent
from backend.tools.registry import TOOL_NAMES
from tests.conftest import FakeLLM, llm_response, text_block, tool_block


async def test_agent_picks_tool_and_records_trace(http):
    llm = FakeLLM(
        [
            llm_response(
                [
                    text_block("I'll use get_current_weather for right-now conditions."),
                    tool_block("tu_1", "get_current_weather", {"location": "Paris, France"}),
                ],
                "tool_use",
            ),
            llm_response([text_block("It's 24.5°C and partly cloudy in Paris.")], "end_turn"),
        ]
    )

    result = await run_agent(llm=llm, http=http, message="Weather in Paris?")

    assert result.reply == "It's 24.5°C and partly cloudy in Paris."
    steps = result.trace.steps
    assert [s.decision for s in steps] == ["use_tools", "final_answer"]
    assert steps[0].available_tools == TOOL_NAMES
    assert "get_current_weather" in steps[0].model_text
    call = steps[0].tool_calls[0]
    assert (call.tool, call.ok, call.input) == (
        "get_current_weather",
        True,
        {"location": "Paris, France"},
    )
    assert steps[0].input_tokens == 100

    # the tool result was sent back to the model
    sent = llm.calls[1]["messages"][-1]["content"][0]
    assert sent["type"] == "tool_result" and sent["tool_use_id"] == "tu_1"


async def test_agent_can_call_two_tools_in_one_step(http):
    llm = FakeLLM(
        [
            llm_response(
                [
                    tool_block("a", "get_current_weather", {"location": "Paris"}),
                    tool_block("b", "get_forecast", {"location": "Paris", "days": 2}),
                ],
                "tool_use",
            ),
            llm_response([text_block("Done.")], "end_turn"),
        ]
    )
    result = await run_agent(llm=llm, http=http, message="Now and tomorrow in Paris?")
    assert [c.tool for c in result.trace.steps[0].tool_calls] == [
        "get_current_weather",
        "get_forecast",
    ]


async def test_tool_failure_is_reported_to_model_and_trace(http):
    llm = FakeLLM(
        [
            llm_response(
                [tool_block("tu_1", "get_current_weather", {"location": "Nowhereville"})],
                "tool_use",
            ),
            llm_response([text_block("I couldn't find that place.")], "end_turn"),
        ]
    )
    result = await run_agent(llm=llm, http=http, message="Weather in Nowhereville?")

    call = result.trace.steps[0].tool_calls[0]
    assert call.ok is False and "No location found" in call.error
    sent = llm.calls[1]["messages"][-1]["content"][0]
    assert sent["is_error"] is True
    assert result.reply == "I couldn't find that place."


async def test_step_limit(http):
    looping = llm_response(
        [tool_block("x", "get_current_weather", {"location": "Paris"})], "tool_use"
    )
    llm = FakeLLM([looping, looping])
    result = await run_agent(llm=llm, http=http, message="loop", max_steps=2)
    assert result.trace.steps[-1].decision == "stopped"
    assert "step limit" in result.reply
