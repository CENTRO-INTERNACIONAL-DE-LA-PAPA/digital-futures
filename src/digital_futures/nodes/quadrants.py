"""Node 7: all four quadrants of every set of axes, one question per set, in parallel."""

import json
from typing import Literal

from pydantic import BaseModel

from digital_futures.llm import ask_all
from digital_futures.progress import reporter
from digital_futures.state import AxisSet, State

GUIDE = """Develop the four scenarios of this 2x2 matrix. Each scenario combines one pole of the X axis
with one pole of the Y axis, as the world stands in the horizon year.

For each scenario give:
- title: 2 to 5 plain words, memorable and neutral. No names of paradise, domination or collapse.
- sketch: 4 or 5 short sentences, at most 110 words. How the two poles interact, what the
  system in scope looks like, who gains and who loses, and the main tension that remains.

Rules:
- Develop all four with the same depth. None is the best case, the worst case or "business as usual".
- Every scenario has both opportunities and hardships.
- Each must be reachable from the current year by a plausible path.
- Do not assume that technology or AI solves the problems, and avoid optimism by default.
- The four scenarios must differ clearly from one another.
- Write in plain words that a workshop participant follows at first reading. No jargon."""

CORNERS = {(x, y) for x in "ab" for y in "ab"}


class Quadrant(BaseModel):
    x: Literal["a", "b"]
    y: Literal["a", "b"]
    title: str
    sketch: str


class Quadrants(BaseModel):
    quadrants: list[Quadrant]


def prompt(state: State, axis_set: AxisSet) -> str:
    s = state["scope"]
    drivers = {d["id"]: d for d in state.get("drivers", [])}
    lines = [GUIDE, f"Scope: {s['theme']} in {s['geography']}, from {s['current_year']} to {s['horizon_year']}."]
    for key in ("x", "y"):
        axis = axis_set[key]
        about = drivers.get(axis["driver_id"], {}).get("description", "")
        lines += [
            f"\n{key.upper()} axis: {axis.get('driver', axis['driver_id'])}. {about}",
            f"  {key} = a: {axis['pole_a']}",
            f"  {key} = b: {axis['pole_b']}",
        ]
    if state.get("feedback"):
        previous = [q for q in state.get("quadrants", []) if q["axis_set"] == axis_set["name"]]
        lines += [
            f"\nYour previous scenarios: {json.dumps(previous, ensure_ascii=False)}",
            f"Reviewer feedback: {state['feedback']}",
        ]
    return "\n".join(lines)


def quadrants(state: State) -> dict:
    sets = state["axis_sets"]
    answers = ask_all(
        Quadrants,
        [prompt(state, s) for s in sets],
        reporter(),
        "Quadrants",
        lambda _, answer: len(answer.quadrants) == 4 and {(q.x, q.y) for q in answer.quadrants} == CORNERS,
    )
    return {
        "quadrants": [
            {
                "axis_set": s["name"],
                "x_pole": s["x"][f"pole_{q.x}"],
                "y_pole": s["y"][f"pole_{q.y}"],
                "title": q.title,
                "sketch": q.sketch,
            }
            for s, answer in zip(sets, answers)
            for q in sorted(answer.quadrants, key=lambda q: (q.x, q.y))
        ]
    }
