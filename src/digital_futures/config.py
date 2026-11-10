"""Runtime settings, read from environment variables (and `.env`)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://futures:futures@localhost:5442/futures")
    reasoning_model: str = os.getenv("DF_REASONING_MODEL", "openrouter:anthropic/claude-opus-5.5")
    narrative_model: str = os.getenv("DF_NARRATIVE_MODEL", "openrouter:google/gemini-3.8-flash")
    # Rubric grader: a different model family from the agent, and one whose structured output
    # accepts the grader's JSON schema (Anthropic models reject its `oneOf`).
    grader_model: str = os.getenv("DF_GRADER_MODEL", "openrouter:google/gemini-3.8-flash")


settings = Settings()


def chat_model(name: str, **kwargs) -> BaseChatModel:
    """A chat model that LangChain knows supports native structured output.

    OpenRouter reports no profile for some models (e.g. Opus 5.5). Without the
    `structured_output` flag LangChain falls back to forced tool calls, which
    Opus 5.5 rejects.
    """
    model = init_chat_model(name, **kwargs)
    return model.model_copy(update={"profile": {**(model.profile or {}), "structured_output": True}})


def with_retries(call, report, attempts: int = 3):
    """Run an agent call again when its answer comes back broken.

    Providers sometimes fail mid-answer and OpenRouter passes on the cut-off JSON
    (finish reason "error"); a fresh attempt usually succeeds.
    """
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except StructuredOutputValidationError as e:
            if attempt == attempts:
                raise
            reason = e.ai_message.response_metadata.get("finish_reason") if e.ai_message else "unknown"
            report(f"The AI's answer came back broken (finish reason: {reason}); retrying ({attempt}/{attempts - 1})…")
