"""Node 4: AI pre-scores, humans adjust. TODO(phase 5): reasoning model + evidence.

4a scores impact and uncertainty; 4b adds attention in policy arenas, separately,
so "least discussed" does not crowd out relevance.
"""

from digital_futures.state import State


def score_impact(state: State) -> dict:
    return {
        "scores": [
            {"driver_id": d["id"], "impact": 3, "uncertainty": 3, "evidence": "Stub"} for d in state["drivers"]
        ]
    }


def score_policy(state: State) -> dict:
    return {"scores": [{**s, "policy_attention": 3} for s in state["scores"]]}
