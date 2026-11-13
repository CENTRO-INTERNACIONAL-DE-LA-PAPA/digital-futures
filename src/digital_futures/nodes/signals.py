"""Node 6b: signals of plausibility for every pole of every axis.

Is a pole already happening somewhere, or are there early signs of it (policies, lobbying,
conflicts, agreements, treaties, pilots, research)? Each pole gets a web search and each axis
a paper search; the AI then judges the pole from those results only and cites their links.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel

from digital_futures.llm import ask_all
from digital_futures.progress import reporter
from digital_futures.state import State
from digital_futures.tools import search_papers, search_web

GUIDE = """An axis of uncertainty has two poles: two states its driver could be in by the horizon year.
From the search results below, judge for each pole whether that state is already visible today.

status:
- "happening now": already the reality in at least some places in scope (laws in force,
  agreements signed, ongoing conflicts, established practice).
- "early signals": moves in that direction (proposals, draft laws, lobbying, negotiations,
  disputes, pilots, research findings).
- "no signal found": the results show nothing relevant.

signals: 2 or 3 sentences naming who, where and when. Say what kind of signal it is (policy,
lobby, conflict, agreement, treaty, pilot, research), and note when it comes from outside the
geography in scope. With "no signal found", say what was searched and found missing.

urls: the links that support your judgement, copied exactly from the results. Use nothing
that is not in the results, and do not fill gaps from memory."""


class PoleSignal(BaseModel):
    pole: Literal["a", "b"]
    status: Literal["happening now", "early signals", "no signal found"]
    signals: str
    urls: list[str]


class AxisSignals(BaseModel):
    poles: list[PoleSignal]


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
                    "sources": [{"title": titles[u], "url": u} for u in dict.fromkeys(p.urls) if u in titles],
                }
            )
    return {"signals": out}
