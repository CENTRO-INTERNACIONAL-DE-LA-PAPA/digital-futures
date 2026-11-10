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
    reasoning_model: str = os.getenv("DF_REASONING_MODEL", "openrouter:google/gemini-3.8-flash")
    narrative_model: str = os.getenv("DF_NARRATIVE_MODEL", "openrouter:google/gemini-3.8-flash")
    # Rubric grader: its structured output must accept the grader's JSON schema
    # (Anthropic models reject its `oneOf`).
    grader_model: str = os.getenv("DF_GRADER_MODEL", "openrouter:google/gemini-3.8-flash")


settings = Settings()


def chat_model(name: str, **kwargs) -> BaseChatModel:
    """A chat model that LangChain knows supports native structured output.

    OpenRouter reports no profile for some models (e.g. Claude Opus 5.5). Without the
    `structured_output` flag LangChain falls back to forced tool calls, which
    Claude models reject.
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


def ask_all(schema, prompts: list[str], report, label: str, check=None, attempts: int = 3) -> list:
    """Ask the reasoning model independent structured questions in parallel.

    Answers that come back broken, or fail `check(index, answer)`, are asked again.
    """
    llm = chat_model(settings.reasoning_model, max_tokens=16_000).with_structured_output(schema, method="json_schema")
    answers: list = [None] * len(prompts)
    todo = list(range(len(prompts)))
    for attempt in range(1, attempts + 1):
        failed = []
        batch = llm.batch_as_completed([prompts[i] for i in todo], {"max_concurrency": 8}, return_exceptions=True)
        for k, answer in batch:
            i = todo[k]
            if isinstance(answer, Exception) or answer is None or (check and not check(i, answer)):
                failed.append(i)
            else:
                answers[i] = answer
                report(f"{label}: {sum(a is not None for a in answers)}/{len(prompts)} done")
        if not failed:
            return answers
        if attempt < attempts:
            report(f"{label}: {len(failed)} answers were broken or incomplete; asking again…")
        todo = failed
    raise RuntimeError(f"{label}: {len(todo)} of {len(prompts)} answers still broken after {attempts} attempts")
