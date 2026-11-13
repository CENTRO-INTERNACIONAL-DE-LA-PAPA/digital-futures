"""Node 8: every quadrant told from four viewpoints, one question per quadrant, in parallel."""

from pydantic import BaseModel

from digital_futures.config import settings
from digital_futures.llm import ask_all
from digital_futures.progress import reporter
from digital_futures.state import Quadrant, State

GUIDE = """Tell this scenario through four people who live in it in the horizon year: a farmer, a
community leader, a scientist and a policy maker.

For each person write a first-person account of 100 to 140 words about an ordinary moment that
shows how this world works for them: what they do, decide or worry about.

Rules:
- Both poles of the scenario must be visible in each account, through what happens, not by naming them.
- Be concrete: a place, a crop or resource, an institution. Put each person in a different
  country or region within the geography in scope.
- Plain language a general reader follows at first reading. No jargon, no moral, no summary.
- Each account mixes what works and what is hard for that person. No heroes and no victims.
- Avoid stereotypes, and vary gender and age across the four people.
- Do not use the words "scenario", "axis" or "quadrant"."""


class Voices(BaseModel):
    farmer: str
    community_leader: str
    scientist: str
    policy_maker: str


PERSONAS = [name.replace("_", " ") for name in Voices.model_fields]


def prompt(state: State, quadrant: Quadrant) -> str:
    s = state["scope"]
    lines = [
        GUIDE,
        f"Scope: {s['theme']} in {s['geography']}. Current year {s['current_year']}, horizon year {s['horizon_year']}.",
        f"\nScenario: {quadrant['title']}",
        f"Poles: {quadrant['x_pole']} · {quadrant['y_pole']}",
        f"Sketch: {quadrant['sketch']}",
    ]
    if state.get("feedback"):
        previous = next(
            (n["personas"] for n in state.get("narratives", []) if (n["axis_set"], n["title"]) == (quadrant["axis_set"], quadrant["title"])),
            None,
        )
        lines += [f"\nYour previous accounts: {previous}"] if previous else []
        lines.append(f"Reviewer feedback: {state['feedback']}")
    return "\n".join(lines)


def narratives(state: State) -> dict:
    quadrants = state["quadrants"]
    answers = ask_all(
        Voices, [prompt(state, q) for q in quadrants], reporter(), "Narratives", model=settings.narrative_model
    )
    return {
        "narratives": [
            {"axis_set": q["axis_set"], "title": q["title"], "personas": dict(zip(PERSONAS, a.model_dump().values()))}
            for q, a in zip(quadrants, answers)
        ]
    }
