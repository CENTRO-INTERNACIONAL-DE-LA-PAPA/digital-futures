"""Runtime settings (from environment variables and `.env`) and logging."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://futures:futures@localhost:5442/futures")
    reasoning_model: str = os.getenv("DF_REASONING_MODEL", "openrouter:google/gemini-3.8-flash")
    narrative_model: str = os.getenv("DF_NARRATIVE_MODEL", "openrouter:google/gemini-3.8-flash")
    # Rubric grader: its structured output must accept the grader's JSON schema
    # (Anthropic models reject its `oneOf`).
    grader_model: str = os.getenv("DF_GRADER_MODEL", "openrouter:google/gemini-3.8-flash")
    # How much hidden reasoning the models may do: minimal, low, medium or high.
    # Reasoning tokens are billed as output and count against the output limit.
    reasoning_effort: str = os.getenv("DF_REASONING_EFFORT", "low")
    log_file: Path = Path(os.getenv("DF_LOG_FILE", "logs/digital_futures.log"))


settings = Settings()


def get_logger() -> logging.Logger:
    """The app logger. Writes every step, AI call (tokens, cost) and failure to `settings.log_file`."""
    log = logging.getLogger("digital_futures")
    if not log.handlers:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(settings.log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


log = get_logger()
