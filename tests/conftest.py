"""Keep tests offline: replace the AI research call with a fake that echoes its prompt."""

import importlib

import pytest

from digital_futures.progress import reporter

drivers_node = importlib.import_module("digital_futures.nodes.drivers")


def fake_research(prompt: str) -> list[dict]:
    reporter()("fake search")
    steeple = ["environmental", "technological", "social", "economic"]
    return [
        {"name": f"Driver {i}", "description": prompt, "steeple": steeple[i % 4], "sources": [{"title": "t", "url": "u"}]}
        for i in range(4)
    ]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(drivers_node, "research", fake_research)
