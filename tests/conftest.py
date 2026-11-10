"""Keep tests offline: replace the AI calls with fakes."""

import importlib
import os
import re
import tempfile

import pytest

os.environ["DF_LOG_FILE"] = os.path.join(tempfile.mkdtemp(), "test.log")  # before the app is imported

from digital_futures.progress import reporter

drivers_node = importlib.import_module("digital_futures.nodes.drivers")
clusters_node = importlib.import_module("digital_futures.nodes.clusters")
scoring_node = importlib.import_module("digital_futures.nodes.scoring")
critical_node = importlib.import_module("digital_futures.nodes.critical")


def fake_drivers(prompt: str) -> list[dict]:
    reporter()("fake search")
    steeple = ["environmental", "technological", "social", "economic"]
    return [
        {"name": f"Driver {i}", "description": prompt, "steeple": steeple[i % 4], "sources": [{"title": "t", "url": "u"}]}
        for i in range(4)
    ]


def fake_clusters(prompt: str, drivers: list[dict]) -> list[dict]:
    ids = [d["id"] for d in drivers]
    halves = [ids[: (len(ids) + 1) // 2], ids[(len(ids) + 1) // 2 :]]
    return [{"name": f"Cluster {n}", "rationale": prompt[:40], "driver_ids": h} for n, h in enumerate(halves, 1) if h]


def fake_ask_all(schema, prompts, report, label, check=None, attempts=3):
    """Answer like the model would, reading driver ids and PICK marks from the prompts."""
    answers = []
    for prompt in prompts:
        ids = re.findall(r"^(\w+) · [^\n]*:", prompt, re.M)
        if schema is scoring_node.ImpactScores:
            data = {"scores": [{"driver_id": i, "impact": 4, "uncertainty": 3, "evidence": "e"} for i in ids]}
        elif schema is scoring_node.PolicyScores:
            data = {"scores": [{"driver_id": i, "policy_attention": 2, "policy_evidence": "p"} for i in ids]}
        else:
            picks = re.findall(r"^(C\d+) · .*?\n- (\w+) · .*? PICK$", prompt, re.M | re.S)
            data = {"picks": [{"cluster": c, "driver_id": d, "rationale": "r"} for c, d in picks]}
        answer = schema.model_validate(data)
        assert check is None or check(len(answers), answer), f"fake answer fails the check for {label}"
        answers.append(answer)
    return answers


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(drivers_node, "research", fake_drivers)
    monkeypatch.setattr(clusters_node, "research", fake_clusters)
    monkeypatch.setattr(scoring_node, "ask_all", fake_ask_all)
    monkeypatch.setattr(scoring_node, "policy_search", lambda driver, geography: [])
    monkeypatch.setattr(critical_node, "ask_all", fake_ask_all)
