"""Node 6: axes of uncertainty, proposed by a deep agent that grades itself against a rubric.

Every cluster contributes one candidate axis: its critical driver. The agent pairs candidates
into sets of two axes (one 2x2 matrix per set) and writes two neutral poles for each axis.
"""

import json

from pydantic import BaseModel

from digital_futures.llm import ask_graded
from digital_futures.nodes.scope import DEFAULT_SCOPE
from digital_futures.progress import reporter
from digital_futures.state import State

SYSTEM = """You are a foresight analyst building 2x2 scenario matrices from critical drivers of change.

- An axis is one critical driver. Its two poles are two contrasting end-states that this same
  driver could plausibly have reached by the horizon year, each as the prevailing state across
  the geography in scope.
- Stretch beyond today. At least one pole of every axis is a real break from the state that
  dominates today. Do not build an axis from the two sides of a present-day debate that already
  coexist (for example, an old practice versus a new one that is already spreading): ask what
  each side would have become decades from now.
- Poles are neutral: neither is the desirable or the undesirable outcome, and a reader could
  not tell which one the author prefers.
- Poles differ in kind, not in degree. Never more/less, high/low, strong/weak, fast/slow,
  success/failure, with/without, adopted/not adopted.
- Each pole has a single characteristic: one short phrase of at most 8 words, with no "and"
  joining two ideas.
- Write poles in plain words that a workshop participant understands at first reading. No
  invented terms and no technical jargon.
- The two axes of a set come from different STEEPLE categories and do not determine each
  other: all four combinations of poles must be plausible, clearly different worlds.
- Use a driver in at most one set. Prefer drivers with high impact and uncertainty and, among
  similar ones, lower attention in policy arenas.
- Watch for bias: technology and AI drivers must not dominate the sets, and no pole may be
  the optimistic future in disguise.

Illustration of the form only (do not reuse it): for a driver about land tenure, the poles
"Land held under customary collective tenure" and "Land held under individual tradable titles".

Answer directly with the final sets. Do not use files, to-do lists or sub-agents."""

RUBRIC = """1. Each axis is a single critical driver, and both of its poles are states of that same driver.
2. Poles are neutral: in no axis is one pole plainly the good outcome and the other the bad one.
3. Poles differ in kind, not in degree: no axis is more/less, high/low, strong/weak,
   success/failure, or presence/absence of the driver.
4. Each pole expresses a single characteristic in a short phrase of plain words; no pole
   joins two ideas or relies on jargon or invented terms.
5. In each set the two axes come from different STEEPLE categories and are independent enough
   that all four combinations of poles are plausible and distinct.
6. No driver is used in more than one set.
7. The sets are not dominated by technology or AI drivers, and the poles do not assume an
   optimistic future.
8. Every axis stretches beyond the present: at least one of its poles is a clear break from the
   state that dominates today, and no axis merely restates a present-day debate whose two
   sides already coexist."""


class Axis(BaseModel):
    driver_id: str
    pole_a: str
    pole_b: str


class AxisSet(BaseModel):
    x: Axis
    y: Axis
    rationale: str


class AxisSets(BaseModel):
    axis_sets: list[AxisSet]


def task(state: State) -> str:
    s = state["scope"]
    wanted = s.get("axis_sets", DEFAULT_SCOPE["axis_sets"])
    drivers = {d["id"]: d for d in state["drivers"]}
    lines = [
        f"Propose {wanted} sets of two axes of uncertainty from these critical drivers.",
        f"Scope: {s['theme']} in {s['geography']}, from {s['current_year']} to {s['horizon_year']}.",
        "In each rationale, say in 2 or 3 sentences why the two axes are independent and what makes the four worlds differ.",
        "Critical drivers (id [STEEPLE] name; scores 1-5: impact, uncertainty, policy attention):",
    ]
    for c in state["critical"]:
        d = drivers.get(c["driver_id"], {})
        lines.append(
            f"{c['driver_id']} [{d.get('steeple', '?')}] {c['name']} "
            f"(impact {c['impact']}, uncertainty {c['uncertainty']}, policy attention {c['policy_attention']}): "
            f"{d.get('description', '')}"
        )
    if state.get("feedback"):
        lines += [
            f"Your previous sets: {json.dumps(state.get('axis_sets', []), ensure_ascii=False)}",
            f"Reviewer feedback: {state['feedback']}",
            "Return the full revised list of sets.",
        ]
    return "\n".join(lines)


def research(prompt: str, labels: dict[str, str]) -> list[dict]:
    """`labels`: driver id -> "name [STEEPLE]", so the grader reads names instead of ids."""
    report = reporter()

    def blocks(answer: AxisSets) -> list[str]:
        return [
            f"## Set {n}\n"
            + "".join(
                f"{k} axis: {labels.get(a.driver_id, a.driver_id)}\n  pole A: {a.pole_a}\n  pole B: {a.pole_b}\n"
                for k, a in (("X", s.x), ("Y", s.y))
            )
            + f"Rationale: {s.rationale}"
            for n, s in enumerate(answer.axis_sets, 1)
        ]

    report(f"Proposing axes of uncertainty from {len(labels)} critical drivers…")
    answer = ask_graded(AxisSets, SYSTEM, prompt, RUBRIC, blocks, report)
    report(f"Done: {len(answer.axis_sets)} sets of axes.")
    return [s.model_dump() for s in answer.axis_sets]


def axes(state: State) -> dict:
    if len(state["critical"]) < 2:
        raise RuntimeError("Axes need at least two critical drivers, so at least two clusters.")
    steeple = {d["id"]: d["steeple"] for d in state["drivers"]}
    names = {c["driver_id"]: c["name"] for c in state["critical"]}
    labels = {i: f"{name} [{steeple.get(i, '?')}]" for i, name in names.items()}

    sets = []
    for s in research(task(state), labels):
        x, y = s["x"], s["y"]
        if x["driver_id"] in names and y["driver_id"] in names and x["driver_id"] != y["driver_id"]:
            x["driver"], y["driver"] = names[x["driver_id"]], names[y["driver_id"]]
            sets.append({"name": f"{x['driver']} × {y['driver']}", **s})
    if not sets:
        raise RuntimeError("The AI proposed no valid set of axes: each axis must be one of the critical drivers.")
    return {"axis_sets": sets}
