"""Chat models and the helpers every AI step uses: logging of each call, retries, parallel
questions, and agents graded against a rubric."""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock

from deepagents import create_deep_agent
from deepagents.middleware.rubric import RubricMiddleware
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from digital_futures.config import log, settings

MAX_GRADER_CHARS = 3_800  # the rubric grader truncates each transcript message at 4,000 characters


_tally: ContextVar[dict | None] = ContextVar("tally", default=None)
_tally_lock = Lock()


@contextmanager
def tally():
    """Count the AI calls made inside the block: number of calls, cost in USD and tokens."""
    counts = {"ai_calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0}
    token = _tally.set(counts)
    try:
        yield counts
    finally:
        _tally.reset(token)


class CallLog(BaseCallbackHandler):
    """Log every model call: duration, tokens (and hidden reasoning tokens), finish reason and cost."""

    def __init__(self) -> None:
        self.started: dict = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs) -> None:
        self.started[run_id] = time.monotonic()

    def on_llm_end(self, response, *, run_id, **kwargs) -> None:
        seconds = time.monotonic() - self.started.pop(run_id, time.monotonic())
        message = response.generations[0][0].message
        usage, meta = message.usage_metadata or {}, message.response_metadata
        if (counts := _tally.get()) is not None:
            with _tally_lock:  # parallel questions finish on different threads
                counts["ai_calls"] += 1
                counts["cost"] += meta.get("cost") or 0
                counts["tokens_in"] += usage.get("input_tokens") or 0
                counts["tokens_out"] += usage.get("output_tokens") or 0
        log.info(
            "AI call %s | %.0fs | in %s, out %s (reasoning %s) tokens | finish=%s | $%.4f | %d chars, %d tool calls",
            meta.get("model_name"),
            seconds,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            usage.get("output_token_details", {}).get("reasoning"),
            meta.get("finish_reason"),
            meta.get("cost") or 0,
            len(message.text),
            len(message.tool_calls),
        )

    def on_llm_error(self, error, *, run_id, **kwargs) -> None:
        self.started.pop(run_id, None)
        log.error("AI call failed: %r", error)


def chat_model(name: str, **kwargs) -> BaseChatModel:
    """A chat model set up for this app.

    - Output limit: the model's maximum. Hidden reasoning counts against it, so a low limit
      cuts the answer off (Gemini 3 can spend thousands of tokens reasoning).
    - Reasoning effort: `settings.reasoning_effort`.
    - Profile flag `structured_output`: OpenRouter reports no profile for some models; without
      the flag LangChain falls back to forced tool calls, which Claude models reject.
    - Every call is logged.
    """
    model = init_chat_model(name, reasoning={"effort": settings.reasoning_effort}, callbacks=[CallLog()], **kwargs)
    profile = {**(model.profile or {}), "structured_output": True}
    return model.model_copy(update={"profile": profile, "max_tokens": profile.get("max_output_tokens", 32_000)})


def finish_reason(error: StructuredOutputValidationError) -> str:
    return (error.ai_message.response_metadata.get("finish_reason") if error.ai_message else None) or "unknown"


def with_retries(call, report, attempts: int = 3):
    """Run an agent call again when a provider fails mid-answer (finish reason "error").

    An answer cut off by the output limit (finish reason "length") is not retried: a new
    attempt would cost the same and fail the same way.
    """
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except StructuredOutputValidationError as e:
            reason = finish_reason(e)
            text = e.ai_message.text if e.ai_message else ""
            log.warning("Broken answer (finish=%s, %d chars, attempt %d/%d): …%s", reason, len(text), attempt, attempts, text[-200:])
            if reason == "length":
                raise RuntimeError(
                    "The AI ran out of output tokens before finishing its answer. "
                    "Lower DF_REASONING_EFFORT or use a model with a larger output limit."
                ) from e
            if attempt == attempts:
                raise
            report(f"The AI's answer came back broken (finish reason: {reason}); retrying ({attempt}/{attempts - 1})…")


def grader_view(schema, request: str, blocks):
    """What the grader reads: the request and the final answer as text, in chunks it will not truncate.

    `blocks(answer)` renders the parsed answer as a list of text blocks (with names, not only ids).
    """

    def prepare(messages: list[AnyMessage]) -> list[AnyMessage]:
        last = next((m for m in reversed(messages) if isinstance(m, AIMessage) and m.text), None)
        try:
            answer = schema.model_validate_json(last.text)
        except (AttributeError, ValueError):
            return messages
        chunks = [""]
        for block in blocks(answer):
            if len(chunks[-1]) + len(block) > MAX_GRADER_CHARS:
                chunks.append("")
            chunks[-1] += block + "\n\n"
        return [HumanMessage(request)] + [AIMessage(chunk) for chunk in chunks]

    return prepare


def ask_graded(schema, system: str, prompt: str, rubric: str, blocks, report):
    """Ask a deep agent for a structured answer; a grader checks it against `rubric` and sends it
    back for another try (up to 3 checks) when a criterion fails."""

    def on_evaluation(evaluation) -> None:
        gaps = "; ".join(c["gap"] for c in evaluation["criteria"] if not c["passed"])
        report(f"Rubric check {evaluation['iteration'] + 1}: {evaluation['result']}" + (f" ({gaps})" if gaps else ""))

    grader = RubricMiddleware(
        model=chat_model(settings.grader_model),
        prepare_messages_for_grader=grader_view(schema, prompt.splitlines()[0], blocks),
        max_iterations=3,
        on_evaluation=on_evaluation,
    )
    agent = create_deep_agent(
        model=chat_model(settings.reasoning_model), system_prompt=system, middleware=[grader], response_format=schema
    )
    result = with_retries(
        lambda: agent.invoke({"messages": [HumanMessage(prompt)], "rubric": rubric}, {"recursion_limit": 100}), report
    )
    return result["structured_response"]


def ask_all(schema, prompts: list[str], report, label: str, check=None, attempts: int = 3, model: str | None = None) -> list:
    """Ask a model (the reasoning model unless `model` is given) independent structured questions in parallel.

    Answers that come back broken, or fail `check(index, answer)`, are asked again.
    """
    llm = chat_model(model or settings.reasoning_model).with_structured_output(schema, method="json_schema")
    answers: list = [None] * len(prompts)
    todo = list(range(len(prompts)))
    for attempt in range(1, attempts + 1):
        failed = []
        batch = llm.batch_as_completed([prompts[i] for i in todo], {"max_concurrency": 8}, return_exceptions=True)
        for k, answer in batch:
            i = todo[k]
            if isinstance(answer, Exception) or answer is None:
                log.warning("%s: question %d failed (attempt %d/%d): %r", label, i, attempt, attempts, answer)
                failed.append(i)
            elif check and not check(i, answer):
                log.warning("%s: answer %d is incomplete (attempt %d/%d): %s", label, i, attempt, attempts, str(answer)[:300])
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
