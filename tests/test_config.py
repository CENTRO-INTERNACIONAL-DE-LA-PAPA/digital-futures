import pytest
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import AIMessage

from digital_futures.config import with_retries


def broken():
    message = AIMessage("{\"clusters\": [", response_metadata={"finish_reason": "error"})
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
