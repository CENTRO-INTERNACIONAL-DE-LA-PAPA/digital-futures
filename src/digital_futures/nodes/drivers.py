"""Node 2: identify drivers of change with web and literature search."""

import json

from langchain.agents import create_agent
from pydantic import BaseModel, Field

from digital_futures.config import chat_model, settings
from digital_futures.progress import reporter
from digital_futures.state import State, Steeple
from digital_futures.tools import find_papers, web_search

SYSTEM = """You are a horizon-scanning researcher supporting a strategic foresight exercise.
Your job is to identify drivers of change: forces that will shape the system in scope between
the current year and the horizon year.

How to scan:
- Be wide and granular. Look well beyond the core theme: ecology, climate, hydrology, soils,
  genetics and biology, health, energy, materials, digital technology, finance and trade,
  demography and migration, geopolitics and conflict, law and governance, culture and values.
- Go past the well-known drivers. After the obvious ones, look for weak signals, emerging
  research and developments that few people connect to the theme yet.
- Keep a balance across STEEPLE categories. Do not over-represent technology or AI, and do not
  assume progress or optimism.
- Do not frame the scan from the perspective of any single organisation.
- Search the web for current signals and the literature for evidence. Use several searches.

What to return, per driver:
- name: a short, neutral label for the force of change (no "good"/"bad", no "more"/"less").
- description: 2-3 sentences: what is changing, the evidence, and why it matters for the
  theme and geography by the horizon year.
- steeple: one of social, technological, economic, environmental, political, legal, ethical.
- sources: 1-3 sources taken from your search results. Never invent a title or URL.

Keep distinct drivers separate; do not merge them into broad themes."""


class Source(BaseModel):
    title: str
    url: str


class Driver(BaseModel):
    name: str
    description: str
    steeple: Steeple
    sources: list[Source] = Field(min_length=1)


class Drivers(BaseModel):
    drivers: list[Driver]


def task(state: State) -> str:
    s = state["scope"]
    lines = [
        f"Theme: {s['theme']}",
        f"Geography: {s['geography']}",
        f"From {s['current_year']} to {s['horizon_year']}",
        f"Identify about {s['target_drivers']} drivers of change.",
    ]
    if s["seed_drivers"]:
        lines.append("Include these drivers brought by participants (add evidence and sources): " + "; ".join(s["seed_drivers"]))
    if state.get("feedback"):
        previous = [{"name": d["name"], "steeple": d["steeple"]} for d in state.get("drivers", [])]
        lines += [
            f"Your previous list: {json.dumps(previous, ensure_ascii=False)}",
            f"Reviewer feedback: {state['feedback']}",
            "Return the full revised list.",
        ]
    return "\n".join(lines)


SEARCH_LABELS = {"tavily_search": "web", "find_papers": "papers"}


def research(prompt: str) -> list[dict]:
    report = reporter()
    model = chat_model(settings.reasoning_model, max_tokens=32_000)
    agent = create_agent(model, tools=[web_search(), find_papers], system_prompt=SYSTEM, response_format=Drivers)

    report("Scanning the web and the literature for drivers of change…")
    searches, result = 0, {}
    stream = agent.stream(
        {"messages": [{"role": "user", "content": prompt}]},
        {"recursion_limit": 100},
        stream_mode=["updates", "values"],
    )
    for mode, chunk in stream:
        if mode == "values":
            result = chunk
        elif "tools" in chunk:
            report(f"Read results of {searches} searches; thinking…")
        else:
            for message in (chunk.get("model") or {}).get("messages", []):
                for call in getattr(message, "tool_calls", []):
                    searches += 1
                    label = SEARCH_LABELS.get(call["name"], call["name"])
                    report(f"Search {searches} · {label}: {call['args'].get('query', '')}")

    found = [d.model_dump() for d in result["structured_response"].drivers]
    report(f"Done: {len(found)} drivers from {searches} searches.")
    return found


def drivers(state: State) -> dict:
    found = research(task(state))
    return {"drivers": [{"id": f"d{i}", **d} for i, d in enumerate(found, 1)]}
