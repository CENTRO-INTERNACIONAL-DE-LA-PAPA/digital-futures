"""Runtime settings, read from environment variables (and `.env`)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://futures:futures@localhost:5442/futures")
    reasoning_model: str = os.getenv("DF_REASONING_MODEL", "openrouter:anthropic/claude-opus-5.5")
    narrative_model: str = os.getenv("DF_NARRATIVE_MODEL", "openrouter:google/gemini-3.8-flash")


settings = Settings()
