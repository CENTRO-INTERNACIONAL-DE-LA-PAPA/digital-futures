import pytest
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from digital_futures.llm import grader_view, with_retries


def broken(reason="error"):
    message = AIMessage("{\"clusters\": [", response_metadata={"finish_reason": reason})
    return StructuredOutputValidationError("Clusters", ValueError("cut off"), message)


def test_with_retries_recovers_from_a_broken_answer():
    attempts, messages = [], []

    def call():
        attempts.append(1)
        if len(attempts) < 2:
            raise broken()
        return "ok"

    assert with_retries(call, messages.append) == "ok"
    assert len(attempts) == 2
    assert "finish reason: error" in messages[0]


def test_with_retries_gives_up_after_the_last_attempt():
    def call():
        raise broken()

    with pytest.raises(StructuredOutputValidationError):
        with_retries(call, lambda m: None, attempts=2)


def test_with_retries_does_not_repeat_an_answer_cut_off_by_the_output_limit():
    attempts = []

    def call():
        attempts.append(1)
        raise broken("length")

    with pytest.raises(RuntimeError, match="ran out of output tokens"):
        with_retries(call, lambda m: None)
    assert len(attempts) == 1


def test_chat_model_uses_the_full_output_limit_and_caps_reasoning():
    from digital_futures.llm import chat_model

    model = chat_model("openrouter:google/gemini-3.8-flash", api_key="test")
    assert model.max_tokens == model.profile["max_output_tokens"] > 16_000
    assert model.reasoning == {"effort": "low"}
    assert model.profile["structured_output"] is True


class Items(BaseModel):
    items: list[str]


def test_grader_view_shows_the_answer_in_untruncated_chunks():
    answer = Items(items=[f"{i} " + "N" * 300 for i in range(40)]).model_dump_json()
    view = grader_view(Items, "the request", lambda a: [f"## {item}" for item in a.items])
    messages = view([HumanMessage("a very long prompt"), AIMessage(answer)])
    assert messages[0].text == "the request"
    assert all(len(m.text) <= 4_000 for m in messages)
    assert sum(m.text.count("## ") for m in messages[1:]) == 40


def test_grader_view_leaves_unparseable_transcripts_alone():
    messages = [HumanMessage("x"), AIMessage("not json")]
    assert grader_view(Items, "the request", lambda a: a.items)(messages) == messages
