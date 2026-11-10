"""Keep tests offline: replace the AI calls with fakes."""

import importlib

import pytest

from digital_futures.progress import reporter

drivers_node = importlib.import_module("digital_futures.nodes.drivers")
clusters_node = importlib.import_module("digital_futures.nodes.clusters")


def fake_drivers(prompt: str) -> list[dict]:
    reporter()("fake search")
    steeple = ["environmental", "technological", "social", "economic"]
    return [
        {"name": f"Driver {i}", "description": prompt, "steeple": steeple[i % 4], "sources": [{"title": "t", "url": "u"}]}
        for i in range(4)
    ]


def fake_clusters(prompt: str, drivers: list[dict]) -> list[dict]:
    return [{"name": "All", "rationale": prompt[:40], "driver_ids": [d["id"] for d in drivers]}]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(drivers_node, "research", fake_drivers)
    monkeypatch.setattr(clusters_node, "research", fake_clusters)
