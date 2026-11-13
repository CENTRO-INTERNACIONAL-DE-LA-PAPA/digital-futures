"""Node 3: cluster drivers with a deep agent that grades itself against a rubric."""

import json

from pydantic import BaseModel

from digital_futures.llm import ask_graded
from digital_futures.progress import reporter
from digital_futures.state import Driver, State

SYSTEM = """You are a foresight analyst. Group drivers of change into clusters for a scenario exercise.

- Cluster by interconnection: drivers belong together when they influence each other or share
  a causal mechanism. Do not cluster by STEEPLE category or by broad theme.
- Keep clusters specific. Generic clusters such as "Technological innovation" or "Resource
  governance" lose the detail that makes drivers useful.
- Do not fragment either: most clusters hold 3 to 6 drivers, so expect roughly one cluster per
  4 drivers. A driver stands alone only when it truly connects to no other driver.
- Name each cluster neutrally (no good/bad framing) and explain in the rationale how its
  drivers are connected.
- Use every driver id exactly once.

Answer directly with the final clustering. Do not use files, to-do lists or sub-agents."""

RUBRIC = """1. Every cluster name is specific to its drivers; no generic label that would fit any scan
   (e.g. "Technological innovation", "Climate change", "Resource governance").
2. In every cluster the drivers are interconnected (they influence each other or share a causal
   mechanism) and the rationale names that connection.
3. No cluster lumps together drivers that should be analysed separately: no cluster has more
   than 8 drivers, and no rationale merely lists unrelated topics.
4. The clustering is not STEEPLE categories in disguise: clusters are defined by mechanisms,
   and most clusters with 3 or more drivers mix STEEPLE categories.
5. Cluster names and rationales are neutral: no normative framing as good or bad.
6. The clustering is not fragmented: at most one cluster in ten holds a single driver, and
   there are no more clusters than one per 3 drivers."""

class Cluster(BaseModel):
    name: str
    rationale: str
    driver_ids: list[str]


class Clusters(BaseModel):
    clusters: list[Cluster]


def task(state: State) -> str:
    lines = [f"Cluster these {len(state['drivers'])} drivers of change by interconnection (id [STEEPLE] name: description):"]
    lines += [f"{d['id']} [{d['steeple']}] {d['name']}: {d['description']}" for d in state["drivers"]]
    if state.get("feedback"):
        previous = [{"name": c["name"], "driver_ids": c["driver_ids"]} for c in state.get("clusters", [])]
        lines += [
            f"Your previous clustering: {json.dumps(previous, ensure_ascii=False)}",
            f"Reviewer feedback: {state['feedback']}",
            "Return the full revised clustering.",
        ]
    return "\n".join(lines)


def cover_all(clusters: list[dict], drivers: list[Driver]) -> list[dict]:
    """Every driver exactly once: drop unknown or repeated ids; put missing drivers in their own cluster."""
    known, seen = {d["id"] for d in drivers}, set()
    for c in clusters:
        kept = []
        for i in c["driver_ids"]:
            if i in known and i not in seen:
                kept.append(i)
                seen.add(i)
        c["driver_ids"] = kept
    clusters = [c for c in clusters if c["driver_ids"]]
    missing = [d["id"] for d in drivers if d["id"] not in seen]
    if missing:
        clusters.append({"name": "Unclustered", "rationale": "Drivers the AI left out; place them by hand.", "driver_ids": missing})
    return clusters


def research(prompt: str, drivers: list[Driver]) -> list[dict]:
    report = reporter()
    names = {d["id"]: f"{d['name']} [{d['steeple']}]" for d in drivers}

    def blocks(answer: Clusters) -> list[str]:
        return [
            f"## {c.name} ({len(c.driver_ids)} drivers)\nRationale: {c.rationale}\nDrivers: "
            + "; ".join(names.get(i, i) for i in c.driver_ids)
            for c in answer.clusters
        ]

    report(f"Clustering {len(drivers)} drivers…")
    answer = ask_graded(Clusters, SYSTEM, prompt, RUBRIC, blocks, report)
    report(f"Done: {len(answer.clusters)} clusters.")
    return [c.model_dump() for c in answer.clusters]


def clusters(state: State) -> dict:
    return {"clusters": cover_all(research(task(state), state["drivers"]), state["drivers"])}
