"""Node 3: cluster drivers with a deep agent that grades itself against a rubric."""

import json

from deepagents import create_deep_agent
from deepagents.middleware.rubric import RubricMiddleware
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from pydantic import BaseModel

from digital_futures.config import chat_model, settings
from digital_futures.progress import reporter
from digital_futures.state import Driver, State

SYSTEM = """You are a foresight analyst. Group drivers of change into clusters for a scenario exercise.

- Cluster by interconnection: drivers belong together when they influence each other or share
  a causal mechanism. Do not cluster by STEEPLE category or by broad theme.
- Keep clusters specific. Generic clusters such as "Technological innovation" or "Resource
  governance" lose the detail that makes drivers useful. Prefer several small clusters to one
  broad one; a driver that fits nowhere can stand alone.
- Name each cluster neutrally (no good/bad framing) and explain in the rationale how its
  drivers are connected.
- Use every driver id exactly once."""

RUBRIC = """1. Every cluster name is specific to its drivers; no generic label that would fit any scan
   (e.g. "Technological innovation", "Climate change", "Resource governance").
2. In every cluster the drivers are interconnected (they influence each other or share a causal
   mechanism) and the rationale names that connection.
3. No cluster lumps together drivers that should be analysed separately: no cluster has more
   than 8 drivers, and no rationale merely lists unrelated topics.
4. The clustering is not STEEPLE categories in disguise: clusters are defined by mechanisms,
   and most clusters with 3 or more drivers mix STEEPLE categories.
5. Cluster names and rationales are neutral: no normative framing as good or bad."""

MAX_GRADER_CHARS = 3_800  # the grader truncates each transcript message at 4,000 characters


class Cluster(BaseModel):
    name: str
    rationale: str
    driver_ids: list[str]


class Clusters(BaseModel):
    clusters: list[Cluster]


def task(state: State) -> str:
    lines = ["Cluster these drivers of change (id [STEEPLE] name: description):"]
    lines += [f"{d['id']} [{d['steeple']}] {d['name']}: {d['description']}" for d in state["drivers"]]
    if state.get("feedback"):
        previous = [{"name": c["name"], "driver_ids": c["driver_ids"]} for c in state.get("clusters", [])]
        lines += [
            f"Your previous clustering: {json.dumps(previous, ensure_ascii=False)}",
            f"Reviewer feedback: {state['feedback']}",
            "Return the full revised clustering.",
        ]
    return "\n".join(lines)


def grader_view(drivers: list[Driver]):
    """Show the grader the final clusters with driver names, in chunks it will not truncate."""
    names = {d["id"]: f"{d['name']} [{d['steeple']}]" for d in drivers}

    def prepare(messages: list[AnyMessage]) -> list[AnyMessage]:
        last = next((m for m in reversed(messages) if isinstance(m, AIMessage) and m.text), None)
        try:
            clusters = Clusters.model_validate_json(last.text).clusters
        except (AttributeError, ValueError):
            return messages
        blocks = [
            f"## {c.name} ({len(c.driver_ids)} drivers)\nRationale: {c.rationale}\nDrivers: "
            + "; ".join(names.get(i, i) for i in c.driver_ids)
            for c in clusters
        ]
        chunks = [""]
        for block in blocks:
            if len(chunks[-1]) + len(block) > MAX_GRADER_CHARS:
                chunks.append("")
            chunks[-1] += block + "\n\n"
        request = HumanMessage(f"Cluster {len(drivers)} drivers of change by interconnection.")
        return [request] + [AIMessage(chunk) for chunk in chunks]

    return prepare


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

    def on_evaluation(evaluation) -> None:
        failed = [c for c in evaluation["criteria"] if not c["passed"]]
        detail = "; ".join(c["gap"] for c in failed)
        report(f"Rubric check {evaluation['iteration'] + 1}: {evaluation['result']}" + (f" ({detail})" if detail else ""))

    grader = RubricMiddleware(
        model=chat_model(settings.grader_model),
        prepare_messages_for_grader=grader_view(drivers),
        max_iterations=3,
        on_evaluation=on_evaluation,
    )
    agent = create_deep_agent(
        model=chat_model(settings.reasoning_model, max_tokens=16_000),
        system_prompt=SYSTEM,
        middleware=[grader],
        response_format=Clusters,
    )
    report(f"Clustering {len(drivers)} drivers…")
    result = agent.invoke({"messages": [HumanMessage(prompt)], "rubric": RUBRIC}, {"recursion_limit": 100})
    clusters = [c.model_dump() for c in result["structured_response"].clusters]
    report(f"Done: {len(clusters)} clusters.")
    return clusters


def clusters(state: State) -> dict:
    return {"clusters": cover_all(research(task(state), state["drivers"]), state["drivers"])}
