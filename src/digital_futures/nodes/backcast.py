"""Node 9: backcasting. Work back from each scenario to today, and look for evidence of the first steps.

For every scenario the AI first writes the pathway backwards (milestones from the horizon year
to the next few years), the searches that would show its first steps today, and indicators to
watch. The step then runs those searches (web, news and papers) and the AI picks the signals
of change from the results only, including signals that point against the scenario.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel

from digital_futures.llm import ask_all
from digital_futures.progress import reporter
from digital_futures.state import Quadrant, State
from digital_futures.tools import search_papers, search_web

PLAN_GUIDE = """Backcast this scenario. Assume it is the reality in the horizon year and work backwards to today.

milestones: 4, latest first. Each has a year and one sentence on what must already have happened
by then for the scenario to hold. The earliest one is within five years of today: the first
visible steps. Be specific about who acts and where.

searches: 3 web search queries (at most 12 words each) that would find evidence today of those
first steps, or of their absence: news, policies, laws, investments, conflicts, agreements,
statistics. Name places and institutions where that helps.

paper_query: one query for the academic literature on the mechanism behind this scenario.

indicators: 3 measurable indicators that would show the world moving toward this scenario or
away from it. For each, a name and what a rise or a fall would mean."""

EVIDENCE_GUIDE = """Below is a scenario, the first steps that would lead to it, and search results. Pick the signals
of change: evidence from the results that those first steps are, or are not, under way today.

signals: up to 6, the most telling first. For each:
- kind: "news" (an event), "policy" (a law, plan, treaty or agreement), "research" (a study or
  paper) or "data" (a statistic or measured trend).
- direction: "towards" the scenario, or "against" it. Include signals against it when the
  results hold any: a report that only confirms is less useful.
- strength: "established" (already in force or widespread), "emerging" (concrete moves: pilots,
  drafts, investments, disputes) or "weak" (isolated cases, proposals, forecasts).
- what: 1 or 2 sentences with who, where and when.
- url: copied exactly from the results.

gaps: 1 or 2 sentences on what this scenario needs that the results show no sign of.

Use only the results. Skip results that are not relevant, and do not fill gaps from memory."""


class Milestone(BaseModel):
    year: int
    what: str


class Indicator(BaseModel):
    name: str
    meaning: str


class Plan(BaseModel):
    milestones: list[Milestone]
    searches: list[str]
    paper_query: str
    indicators: list[Indicator]


class Signal(BaseModel):
    kind: Literal["news", "policy", "research", "data"]
    direction: Literal["towards", "against"]
    strength: Literal["established", "emerging", "weak"]
    what: str
    url: str


class Evidence(BaseModel):
    signals: list[Signal]
    gaps: str


def scenario(state: State, quadrant: Quadrant) -> list[str]:
    s = state["scope"]
    return [
        f"Scope: {s['theme']} in {s['geography']}. Today is {s['current_year']}; horizon year {s['horizon_year']}.",
        f"\nScenario: {quadrant['title']}",
        f"Poles: {quadrant['x_pole']} · {quadrant['y_pole']}",
        f"Sketch: {quadrant['sketch']}",
    ]


def plan_prompt(state: State, quadrant: Quadrant) -> str:
    lines = [PLAN_GUIDE, *scenario(state, quadrant)]
    if state.get("feedback"):
        previous = [b for b in state.get("backcasts", []) if (b["axis_set"], b["title"]) == (quadrant["axis_set"], quadrant["title"])]
        lines += [f"\nYour previous pathway: {previous[0]['pathway']}"] if previous else []
        lines.append(f"Reviewer feedback: {state['feedback']}")
    return "\n".join(lines)


def evidence_prompt(state: State, quadrant: Quadrant, plan: Plan, results: list[dict]) -> str:
    first = min(plan.milestones, key=lambda m: m.year)
    lines = [EVIDENCE_GUIDE, *scenario(state, quadrant), f"First steps (by {first.year}): {first.what}", "\nSearch results:"]
    lines += [f"- {r['title']} ({r['url']}){' ' + str(r['date']) if r.get('date') else ''}: {r['content']}" for r in results] or ["- none"]
    return "\n".join(lines)


def gather(plan: Plan) -> list[dict]:
    """Run the plan's searches: the first one on news, the others on the whole web, plus papers."""
    results = []
    for n, query in enumerate(plan.searches[:3]):
        results += search_web(query, topic="news" if n == 0 else "general")
    for p in search_papers(plan.paper_query):
        results.append({"title": p["title"], "url": p["url"], "date": p["year"], "content": p["abstract"]})
    return [r for r in results if r["url"]]


def backcast(state: State) -> dict:
    report = reporter()
    quadrants = state["quadrants"]
    plans = ask_all(
        Plan,
        [plan_prompt(state, q) for q in quadrants],
        report,
        "Pathways",
        lambda _, plan: len(plan.milestones) >= 3 and len(plan.searches) >= 1,
    )
    report(f"Searching news, the web and the literature for {len(quadrants)} scenarios (about two minutes)…")
    with ThreadPoolExecutor(max_workers=8) as pool:
        found = list(pool.map(gather, plans))
    evidence = ask_all(
        Evidence, [evidence_prompt(state, q, p, r) for q, p, r in zip(quadrants, plans, found)], report, "Signals of change"
    )
    out = []
    for q, plan, results, answer in zip(quadrants, plans, found, evidence):
        titles = {r["url"]: r["title"] for r in results}
        out.append(
            {
                "axis_set": q["axis_set"],
                "title": q["title"],
                "pathway": [m.model_dump() for m in sorted(plan.milestones, key=lambda m: -m.year)],
                "signals": [  # only links that came from the searches
                    {**s.model_dump(exclude={"url"}), "source": {"title": titles[s.url], "url": s.url}}
                    for s in answer.signals
                    if s.url in titles
                ],
                "indicators": [i.model_dump() for i in plan.indicators],
                "gaps": answer.gaps,
            }
        )
    return {"backcasts": out}
