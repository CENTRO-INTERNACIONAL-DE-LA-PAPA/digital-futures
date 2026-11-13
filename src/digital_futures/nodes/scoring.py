"""Node 4: AI pre-scores every driver; humans adjust at the review.

4a scores impact and uncertainty. 4b scores attention in policy arenas, separately and after,
so that "least discussed" does not crowd out relevance (a lesson from the 2025 probes).
Drivers are scored cluster by cluster, in parallel.
"""

import json
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field

from digital_futures.llm import ask_all
from digital_futures.progress import reporter
from digital_futures.state import Cluster, Driver, State
from digital_futures.tools import search_web

IMPACT_GUIDE = """Score each driver from 1 to 5 on two separate dimensions.

Impact: how much the driver could change the system in scope by the horizon year.
  1 marginal or very local · 2 noticeable in some places · 3 significant for some subsystems or
  regions · 4 major, across several subsystems or many countries · 5 transformative.
Uncertainty: how far its plausible trajectories diverge by the horizon year.
  1 established trend, direction and pace agreed · 2 direction agreed, pace uncertain ·
  3 several plausible paths · 4 evidence disagrees on direction · 5 could go in fundamentally
  different directions (unresolved choices, thresholds or tipping points).

Judge impact and uncertainty independently. Ignore how much the driver is discussed in policy.
Use the whole scale. Evidence: 1-2 sentences justifying both scores."""

POLICY_GUIDE = """Score how much attention each driver gets in policy arenas today, from 1 to 5,
using the search results given for it (and your knowledge where they are thin).
  1 almost absent from policy documents and debates · 2 mentioned occasionally or in niche
  forums · 3 on the agenda in some countries or forums · 4 prominent in many national
  strategies or international processes · 5 central, high-profile priority.
Policy evidence: 1-2 sentences, citing the URLs that support the score."""


class ImpactScore(BaseModel):
    driver_id: str
    impact: int = Field(ge=1, le=5)
    uncertainty: int = Field(ge=1, le=5)
    evidence: str


class ImpactScores(BaseModel):
    scores: list[ImpactScore]


class PolicyScore(BaseModel):
    driver_id: str
    policy_attention: int = Field(ge=1, le=5)
    policy_evidence: str


class PolicyScores(BaseModel):
    scores: list[PolicyScore]


def groups(state: State) -> list[tuple[Cluster, list[Driver]]]:
    drivers = {d["id"]: d for d in state["drivers"]}
    return [(c, [drivers[i] for i in c["driver_ids"] if i in drivers]) for c in state["clusters"]]


def header(state: State, cluster: Cluster) -> list[str]:
    s = state["scope"]
    return [
        f"Scope: {s['theme']} in {s['geography']}, from {s['current_year']} to {s['horizon_year']}.",
        f"Cluster: {cluster['name']}. {cluster['rationale']}",
    ]


def revision(state: State, ids: set[str]) -> list[str]:
    if not state.get("feedback"):
        return []
    previous = [s for s in state.get("scores", []) if s["driver_id"] in ids]
    return [f"Your previous scores: {json.dumps(previous, ensure_ascii=False)}", f"Reviewer feedback: {state['feedback']}"]


def covers(ids_per_prompt: list[set[str]]):
    """Check that an answer scores exactly the drivers its prompt asked about."""
    return lambda i, answer: {s.driver_id for s in answer.scores} == ids_per_prompt[i]


def impact_prompt(state: State, cluster: Cluster, drivers: list[Driver]) -> str:
    lines = [IMPACT_GUIDE, *header(state, cluster), "Drivers:"]
    for d in drivers:
        sources = "; ".join(s["title"] for s in d["sources"])
        lines.append(f"{d['id']} · {d['name']}: {d['description']} (sources: {sources})")
    return "\n".join(lines + revision(state, {d["id"] for d in drivers}))


def score_impact(state: State) -> dict:
    report = reporter()
    batches = [(c, ds) for c, ds in groups(state) if ds]
    ids = [{d["id"] for d in ds} for _, ds in batches]
    answers = ask_all(
        ImpactScores, [impact_prompt(state, c, ds) for c, ds in batches], report, "Impact and uncertainty", covers(ids)
    )
    names = {d["id"]: d["name"] for d in state["drivers"]}
    return {
        "scores": [
            {"driver_id": s.driver_id, "name": names[s.driver_id], **s.model_dump(exclude={"driver_id"})}
            for answer in answers
            for s in answer.scores
        ]
    }


def policy_search(driver: Driver, geography: str) -> list[dict]:
    return search_web(f"{driver['name']} policy strategy regulation {geography}")


def policy_prompt(state: State, cluster: Cluster, drivers: list[Driver], found: dict[str, list[dict]]) -> str:
    lines = [POLICY_GUIDE, *header(state, cluster)]
    for d in drivers:
        lines.append(f"\n{d['id']} · {d['name']}: {d['description']}\nSearch results:")
        lines += [f"- {r['title']} ({r['url']}): {r['content']}" for r in found[d["id"]]]
    return "\n".join(lines + revision(state, {d["id"] for d in drivers}))


def score_policy(state: State) -> dict:
    report = reporter()
    geography = state["scope"]["geography"]
    report(f"Searching policy documents and debates for {len(state['drivers'])} drivers…")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda d: policy_search(d, geography), state["drivers"])
        found = {d["id"]: r for d, r in zip(state["drivers"], results)}

    batches = [(c, ds) for c, ds in groups(state) if ds]
    ids = [{d["id"] for d in ds} for _, ds in batches]
    answers = ask_all(
        PolicyScores, [policy_prompt(state, c, ds, found) for c, ds in batches], report, "Policy attention", covers(ids)
    )
    policy = {s.driver_id: s.model_dump(exclude={"driver_id"}) for a in answers for s in a.scores}
    return {"scores": [{**s, **policy.get(s["driver_id"], {})} for s in state["scores"]]}
