import importlib

from langchain_core.messages import AIMessage, HumanMessage

clusters_node = importlib.import_module("digital_futures.nodes.clusters")

DRIVERS = [
    {"id": f"d{i}", "name": f"Driver {i}", "description": "x", "steeple": "social", "sources": []} for i in range(1, 5)
]


def test_cover_all_drops_unknown_and_duplicates_and_collects_missing():
    clusters = [
        {"name": "A", "rationale": "", "driver_ids": ["d1", "d2", "d9"]},
        {"name": "B", "rationale": "", "driver_ids": ["d2"]},
    ]
    result = clusters_node.cover_all(clusters, DRIVERS)
    assert [c["name"] for c in result] == ["A", "Unclustered"]
    assert result[0]["driver_ids"] == ["d1", "d2"]
    assert result[1]["driver_ids"] == ["d3", "d4"]


def test_task_lists_drivers_and_carries_feedback():
    previous = [{"name": "A", "rationale": "", "driver_ids": ["d1"]}]
    prompt = clusters_node.task({"drivers": DRIVERS, "clusters": previous, "feedback": "split A"})
    assert "d3 [social] Driver 3: x" in prompt
    assert "Reviewer feedback: split A" in prompt


def test_grader_view_shows_names_in_untruncated_chunks():
    many = [{**DRIVERS[0], "id": f"d{i}", "name": "N" * 60} for i in range(200)]
    output = clusters_node.Clusters(
        clusters=[{"name": f"C{k}", "rationale": "r", "driver_ids": [f"d{i}" for i in range(k * 10, k * 10 + 10)]} for k in range(20)]
    ).model_dump_json()
    view = clusters_node.grader_view(many)([HumanMessage("long prompt"), AIMessage(output)])
    assert isinstance(view[0], HumanMessage)
    assert all(len(m.text) <= 4_000 for m in view)
    assert sum(m.text.count("## C") for m in view[1:]) == 20
    assert "N" * 60 in view[1].text


def test_grader_view_leaves_unparseable_transcripts_alone():
    messages = [HumanMessage("x"), AIMessage("not json")]
    assert clusters_node.grader_view(DRIVERS)(messages) == messages
