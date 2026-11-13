"""Node 6b: how far is today from each pole of each axis?

A scenario should stretch beyond the present. For each pole the step searches the web and the
literature for signs of it today (policies, lobbying, conflicts, agreements, treaties, pilots,
research), and the AI places the pole on a scale from "dominant today" to "no signal found",
citing only links from the results. An axis whose two poles both exist today has low stretch.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel

from digital_futures.llm import ask_all
from digital_futures.progress import reporter
from digital_futures.state import State
from digital_futures.tools import search_papers, search_web

Status = Literal["dominant today", "established in places", "emerging", "weak signals", "no signal found"]

GUIDE = """An axis of uncertainty has two poles: two end-states its driver could have reached by the horizon
year. From the search results below, judge for each pole how far today is from it.

status:
- "dominant today": this is already the prevailing state across most of the geography in scope.
- "established in places": the normal state in some countries or regions, but not the prevailing one.
- "emerging": not the normal state anywhere yet, but there are concrete moves: pilots, draft
  laws, signed agreements not yet in force, investments, open disputes, organised lobbying.
- "weak signals": only isolated cases, proposals, forecasts or research findings.
- "no signal found": the results show nothing relevant.
Be strict: one country or one programme does not make a pole "established in places".

signals: 2 or 3 sentences naming who, where and when. Say what kind of signal it is (policy,
lobby, conflict, agreement, treaty, pilot, research), and note when it comes from outside the
geography in scope. With "no signal found", say what was searched and found missing.

shift: 1 or 2 sentences on what would have to change for this pole to become the prevailing
state by the horizon year.

urls: the links that support your judgement, copied exactly from the results. Use nothing
that is not in the results, and do not fill gaps from memory."""


class PoleSignal(BaseModel):
    pole: Literal["a", "b"]
    status: Status
    signals: str
    shift: str
    urls: list[str]


class AxisSignals(BaseModel):
    poles: list[PoleSignal]


def low_stretch(statuses: list[str]) -> bool:
    """An axis whose poles all exist today describes the present more than an open future."""
    return bool(statuses) and all(s in ("dominant today", "established in places") for s in statuses)


def axes_of(state: State) -> list[tuple[str, dict]]:
    """(set name, axis) for every axis of every set."""
    return [(s["name"], s[k]) for s in state["axis_sets"] for k in ("x", "y")]


def prompt(state: State, axis: dict, web: dict[str, list[dict]], papers: list[dict]) -> str:
    s = state["scope"]
    name = axis.get("driver", axis["driver_id"])
    lines = [GUIDE, f"Scope: {s['theme']} in {s['geography']}. Today is {s['current_year']}; horizon year {s['horizon_year']}."]
    lines.append(f"\nAxis: {name}")
    for key in "ab":
        lines.append(f"\nPole {key}: {axis[f'pole_{key}']}\nWeb results:")
        lines += [f"- {r['title']} ({r['url']}): {r['content']}" for r in web[key]] or ["- none"]
    lines.append("\nPapers about this axis:")
    lines += [f"- {p['title']} ({p['year']}, {p['url']}): {p['abstract']}" for p in papers] or ["- none"]
    if state.get("feedback"):
        lines.append(f"\nReviewer feedback: {state['feedback']}")
    return "\n".join(lines)


def signals(state: State) -> dict:
    report = reporter()
    geography = state["scope"]["geography"]
    axes = axes_of(state)

    def gather(axis: dict) -> tuple[dict, list]:
        name = axis.get("driver", axis["driver_id"])
        web = {k: search_web(f"{axis[f'pole_{k}']} ({name}) {geography} policy conflict agreement news") for k in "ab"}
        return web, search_papers(f"{name}: {axis['pole_a']} versus {axis['pole_b']} in {geography}")

    report(f"Searching the web and the literature for signals on {len(axes)} axes (about a minute)…")
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = list(pool.map(gather, [axis for _, axis in axes]))

    answers = ask_all(
        AxisSignals,
        [prompt(state, axis, web, papers) for (_, axis), (web, papers) in zip(axes, found)],
        report,
        "Signals",
        lambda _, answer: sorted(p.pole for p in answer.poles) == ["a", "b"],
    )
    out = []
    for (set_name, axis), (web, papers), answer in zip(axes, found, answers):
        titles = {r["url"]: r["title"] for r in [*web["a"], *web["b"], *papers] if r["url"]}
        for p in sorted(answer.poles, key=lambda p: p.pole):
            out.append(
                {
                    "axis_set": set_name,
                    "driver": axis.get("driver", axis["driver_id"]),
                    "pole": axis[f"pole_{p.pole}"],
                    "status": p.status,
                    "signals": p.signals,
                    "shift": p.shift,
                    "sources": [{"title": titles[u], "url": u} for u in dict.fromkeys(p.urls) if u in titles],
                }
            )
    return {"signals": out}
