import importlib

from digital_futures.nodes.scope import DEFAULT_SCOPE

scoring = importlib.import_module("digital_futures.nodes.scoring")
critical = importlib.import_module("digital_futures.nodes.critical")

DRIVERS = [{"id": f"d{i}", "name": f"Driver {i}", "description": "x", "steeple": "social", "sources": []} for i in range(1, 5)]
CLUSTERS = [
    {"name": "Water", "rationale": "linked", "driver_ids": ["d1", "d2"]},
    {"name": "Labour", "rationale": "linked", "driver_ids": ["d3", "d4"]},
]


def score(i, impact, uncertainty, policy):
    return {"driver_id": f"d{i}", "name": f"Driver {i}", "impact": impact, "uncertainty": uncertainty,
            "evidence": "e", "policy_attention": policy}


def test_impact_then_policy_scores_every_clustered_driver():
    state = {"scope": DEFAULT_SCOPE, "drivers": DRIVERS, "clusters": CLUSTERS}
    state |= scoring.score_impact(state)
    assert [s["driver_id"] for s in state["scores"]] == ["d1", "d2", "d3", "d4"]
    assert state["scores"][0]["name"] == "Driver 1"
    state |= scoring.score_policy(state)
    assert all(s["policy_attention"] == 2 for s in state["scores"])


def test_impact_prompt_carries_feedback_and_previous_scores():
    state = {"scope": DEFAULT_SCOPE, "scores": [score(1, 5, 5, 1)], "feedback": "lower d1"}
    prompt = scoring.impact_prompt(state, CLUSTERS[0], DRIVERS[:2])
    assert "Reviewer feedback: lower d1" in prompt and '"impact": 5' in prompt


def test_covers_rejects_missing_or_extra_drivers():
    check = scoring.covers([{"d1", "d2"}])
    full = scoring.ImpactScores(scores=[{"driver_id": i, "impact": 1, "uncertainty": 1, "evidence": ""} for i in ("d1", "d2")])
    partial = scoring.ImpactScores(scores=full.scores[:1])
    assert check(0, full) and not check(0, partial)


def test_rule_picks_highest_impact_times_uncertainty_then_lowest_policy_attention():
    scores = [score(1, 4, 3, 5), score(2, 3, 4, 2), score(3, 5, 5, 5), score(4, 2, 2, 1)]
    state = {"scope": DEFAULT_SCOPE, "drivers": DRIVERS, "clusters": CLUSTERS, "scores": scores}
    clusters = critical.candidates(state)
    assert clusters["C1"][1][0]["driver_id"] == "d2"  # 12 = 12, lower policy attention wins
    assert clusters["C2"][1][0]["driver_id"] == "d3"
    result = critical.critical(state)["critical"]
    assert [(c["driver_id"], c["cluster"]) for c in result] == [("d2", "Water"), ("d3", "Labour")]
