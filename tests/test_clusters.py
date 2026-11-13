import importlib

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
