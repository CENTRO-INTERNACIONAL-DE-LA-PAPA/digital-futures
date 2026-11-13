"""Node 5: critical drivers, one per cluster.

The rule picks each cluster's driver with the highest impact × uncertainty (ties: lower policy
attention, then higher impact). The AI explains each pick, and changes one only when the
reviewer's feedback asks for it.
"""

from pydantic import BaseModel, field_validator

from digital_futures.llm import ask_all
from digital_futures.nodes.scoring import groups
from digital_futures.progress import reporter
from digital_futures.state import Score, State

GUIDE = """These are clusters of drivers of change with their scores (impact, uncertainty and attention
in policy arenas, each 1-5). In each cluster the driver marked PICK was chosen by rule: highest
impact × uncertainty, ties broken by lower policy attention.

For every cluster, return its key (C1, C2, …), the pick and 1-2 sentences on why it is a critical uncertainty for the
scope: what is at stake and why its future is open. Keep each pick unless the reviewer feedback
asks to change it; then you may choose another driver from the same cluster."""


class Pick(BaseModel):
    cluster: str
    driver_id: str
    rationale: str

    @field_validator("cluster")
    @classmethod
    def key_only(cls, value: str) -> str:
        """The model sometimes answers "C1 · Cluster name"; keep the key."""
        return value.split()[0] if value.strip() else value


class Picks(BaseModel):
    picks: list[Pick]


def rank(score: Score) -> tuple:
    return (-score["impact"] * score["uncertainty"], score.get("policy_attention", 3), -score["impact"])


def candidates(state: State) -> dict[str, tuple[str, list[Score]]]:
    """Cluster key -> (cluster name, its scored drivers, best first)."""
    scores = {s["driver_id"]: s for s in state["scores"]}
    out = {}
    for n, (cluster, drivers) in enumerate(groups(state), 1):
        ranked = sorted((scores[d["id"]] for d in drivers if d["id"] in scores), key=rank)
        if ranked:
            out[f"C{n}"] = (cluster["name"], ranked)
    return out


def prompt(state: State, clusters: dict[str, tuple[str, list[Score]]]) -> str:
    s = state["scope"]
    lines = [GUIDE, f"Scope: {s['theme']} in {s['geography']}, from {s['current_year']} to {s['horizon_year']}."]
    for key, (name, ranked) in clusters.items():
        lines.append(f"\n{key} · {name}")
        for i, d in enumerate(ranked):
            mark = " PICK" if i == 0 else ""
            lines.append(
                f"- {d['driver_id']} · {d['name']}: impact {d['impact']}, uncertainty {d['uncertainty']}, "
                f"policy attention {d.get('policy_attention', '?')}{mark}"
            )
    if state.get("feedback"):
        lines.append(f"\nReviewer feedback: {state['feedback']}")
    return "\n".join(lines)


def critical(state: State) -> dict:
    report = reporter()
    clusters = candidates(state)
    allowed = {key: {d["driver_id"] for d in ranked} for key, (_, ranked) in clusters.items()}

    def valid(_, answer: Picks) -> bool:
        picks = {p.cluster: p.driver_id for p in answer.picks}
        return picks.keys() == allowed.keys() and all(picks[k] in allowed[k] for k in picks)

    [answer] = ask_all(Picks, [prompt(state, clusters)], report, "Critical drivers", valid)
    scores = {s["driver_id"]: s for s in state["scores"]}
    return {
        "critical": [
            {
                "driver_id": p.driver_id,
                "name": scores[p.driver_id]["name"],
                "cluster": clusters[p.cluster][0],
                "impact": scores[p.driver_id]["impact"],
                "uncertainty": scores[p.driver_id]["uncertainty"],
                "policy_attention": scores[p.driver_id].get("policy_attention", 0),
                "rationale": p.rationale,
            }
            for p in answer.picks
        ]
    }
