from backend.agent.agent import build_system_prompt, run_agent
from backend.languages import as_list, language_name, normalize
from tests.conftest import FakeLLM, llm_response, text_block


def test_normalize_accepts_tags_and_casing():
    assert normalize("hi") == "hi"
    assert normalize("hi-IN") == "hi"
    assert normalize("TE_in") == "te"


def test_normalize_falls_back_for_unknown_or_missing():
    assert normalize("fr") == "en"
    assert normalize(None) == "en"
    assert normalize("") == "en"


def test_every_language_has_a_speech_tag_and_native_name():
    for lang in as_list():
        assert lang["speech_tag"].endswith("-IN")
        assert lang["native"]


def test_english_prompt_does_not_ask_for_translation():
    prompt = build_system_prompt("en", today="2026-09-19")
    assert "Answer in English." in prompt
    assert "2026-09-19" in prompt


def test_other_language_prompt_names_the_language():
    prompt = build_system_prompt("te", today="2026-09-19")
    assert language_name("te") in prompt
    assert "trace panel" in prompt  # tool reasoning stays in English


def test_unknown_language_prompt_falls_back_to_english():
    assert "Answer in English." in build_system_prompt("fr")


async def test_agent_records_the_language_on_the_trace(http):
    llm = FakeLLM([llm_response([text_block("नमस्ते")], "end_turn")])
    result = await run_agent(llm=llm, http=http, message="नमस्ते", language="hi-IN")

    assert result.trace.language == "hi"
    assert language_name("hi") in llm.calls[0]["system"]


async def test_step_limit_message_is_translated(http):
    from tests.conftest import tool_block

    looping = llm_response(
        [tool_block("x", "get_current_weather", {"location": "Paris"})], "tool_use"
    )
    llm = FakeLLM([looping, looping])
    result = await run_agent(
        llm=llm, http=http, message="loop", language="hi", max_steps=2
    )
    assert "step limit" not in result.reply
    assert result.reply.strip()
