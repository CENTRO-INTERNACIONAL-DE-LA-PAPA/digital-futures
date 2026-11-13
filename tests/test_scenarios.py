"""Steps 6 to 8: axes, quadrants and narratives."""

import importlib

from digital_futures.nodes.scope import DEFAULT_SCOPE

axes = importlib.import_module("digital_futures.nodes.axes")
signals = importlib.import_module("digital_futures.nodes.signals")
quadrants = importlib.import_module("digital_futures.nodes.quadrants")
narratives = importlib.import_module("digital_futures.nodes.narratives")
backcast = importlib.import_module("digital_futures.nodes.backcast")
critical = importlib.import_module("digital_futures.nodes.critical")

DRIVERS = [
    {"id": "d1", "name": "Water rights", "description": "who holds them", "steeple": "legal", "sources": []},
    {"id": "d2", "name": "Rural labour", "description": "who works the land", "steeple": "social", "sources": []},
]
CRITICAL = [
    {"driver_id": d["id"], "name": d["name"], "cluster": "c", "impact": 5, "uncertainty": 4, "policy_attention": 2, "rationale": "r"}
    for d in DRIVERS
]
STATE = {"scope": DEFAULT_SCOPE, "drivers": DRIVERS, "critical": CRITICAL}


def test_axes_task_lists_critical_drivers_and_carries_feedback():
    prompt = axes.task({**STATE, "axis_sets": [{"name": "old"}], "feedback": "other poles"})
    assert prompt.startswith("Propose 3 sets")
    assert "d1 [legal] Water rights (impact 5, uncertainty 4, policy attention 2): who holds them" in prompt
    assert "Reviewer feedback: other poles" in prompt and '"old"' in prompt


def test_axes_names_sets_and_drops_axes_that_are_not_critical_drivers(monkeypatch):
    axis = lambda i: {"driver_id": i, "pole_a": "a", "pole_b": "b"}
    proposed = [{"x": axis("d1"), "y": axis("d2"), "rationale": "r"}, {"x": axis("d1"), "y": axis("d9"), "rationale": "r"}]
    monkeypatch.setattr(axes, "research", lambda prompt, labels: proposed)
    [only] = axes.axes(STATE)["axis_sets"]
    assert only["name"] == "Water rights × Rural labour"
    assert only["x"]["driver"] == "Water rights"


def test_every_set_gets_four_quadrants_and_every_quadrant_four_voices():
    state = STATE | axes.axes(STATE)
    state |= quadrants.quadrants(state)
    assert [(q["x_pole"], q["y_pole"]) for q in state["quadrants"]] == [
        ("d1 one way", "d2 one way"),
        ("d1 one way", "d2 another way"),
        ("d1 another way", "d2 one way"),
        ("d1 another way", "d2 another way"),
    ]
    state |= narratives.narratives(state)
    assert len(state["narratives"]) == 4
    assert list(state["narratives"][0]["personas"]) == ["farmer", "community leader", "scientist", "policy maker"]
    assert state["narratives"][0]["axis_set"] == state["axis_sets"][0]["name"]


def test_quadrant_prompt_shows_both_axes_with_their_poles():
    state = STATE | axes.axes(STATE)
    prompt = quadrants.prompt(state, state["axis_sets"][0])
    assert "X axis: Water rights. who holds them" in prompt
    assert "y = b: d2 another way" in prompt


def test_critical_pick_keeps_only_the_cluster_key():
    assert critical.Pick(cluster="C1 · Groundwater", driver_id="d1", rationale="r").cluster == "C1"


def test_every_pole_gets_a_signal_with_sources_from_the_search_only():
    state = STATE | axes.axes(STATE)
    found = signals.signals(state)["signals"]
    assert [g["pole"] for g in found] == ["d1 one way", "d1 another way", "d2 one way", "d2 another way"]
    assert found[0]["status"] == "emerging" and found[0]["shift"] == "c"
    assert found[0]["sources"] == [{"title": "News", "url": "http://news"}]  # the invented link is dropped


def test_quadrant_prompt_carries_what_is_seen_today():
    state = STATE | axes.axes(STATE)
    state |= signals.signals(state)
    assert "Seen today (emerging: s)" in quadrants.prompt(state, state["axis_sets"][0])


def test_an_axis_whose_poles_all_exist_today_has_low_stretch():
    assert signals.low_stretch(["dominant today", "established in places"])
    assert not signals.low_stretch(["dominant today", "emerging"])
    assert not signals.low_stretch([])


def test_every_scenario_is_backcast_with_evidence_from_the_searches_only():
    state = STATE | axes.axes(STATE)
    state |= signals.signals(state)
    state |= quadrants.quadrants(state)
    found = backcast.backcast(state)["backcasts"]
    assert [b["title"] for b in found] == [q["title"] for q in state["quadrants"]]
    assert [m["year"] for m in found[0]["pathway"]] == [2060, 2045, 2030]  # latest first
    assert found[0]["signals"] == [
        {"kind": "news", "direction": "against", "strength": "weak", "what": "w", "source": {"title": "News", "url": "http://news"}}
    ]
    assert found[0]["indicators"][0]["name"] == "Share of X" and found[0]["gaps"] == "g"


def test_evidence_prompt_names_the_first_steps():
    state = STATE | axes.axes(STATE)
    state |= quadrants.quadrants(state)
    plan = backcast.Plan(milestones=[{"year": 2060, "what": "late"}, {"year": 2030, "what": "early"}], searches=["q"], paper_query="p", indicators=[])
    prompt = backcast.evidence_prompt(state, state["quadrants"][0], plan, [{"title": "T", "url": "http://t", "content": "c", "date": "2026-05"}])
    assert "First steps (by 2030): early" in prompt and "- T (http://t) 2026-05: c" in prompt
