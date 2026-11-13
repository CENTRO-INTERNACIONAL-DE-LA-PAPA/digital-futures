"""The scenario graph: scope, then each step followed by a human review."""

import time
from datetime import UTC, datetime
from functools import wraps

from langgraph.graph import END, START, StateGraph

from digital_futures import cache, nodes
from digital_futures.config import log
from digital_futures.llm import tally
from digital_futures.progress import reporter
from digital_futures.review import make_review, route_after_review
from digital_futures.state import State

# (step name, state key it writes, node function)
STEPS = [
    ("drivers", "drivers", nodes.drivers),
    ("clusters", "clusters", nodes.clusters),
    ("score_impact", "scores", nodes.score_impact),
    ("score_policy", "scores", nodes.score_policy),
    ("critical", "critical", nodes.critical),
    ("axes", "axis_sets", nodes.axes),
    ("signals", "signals", nodes.signals),
    ("quadrants", "quadrants", nodes.quadrants),
    ("narratives", "narratives", nodes.narratives),
]


def make_step(index: int):
    """The node for a step: reuse its saved result when its inputs did not change, else run it.

    Logs when the step starts, how long it takes, and how many items it returns.
    """
    step, key, fn = STEPS[index]
    inputs = ["scope", *dict.fromkeys(k for _, k, _ in STEPS[:index])]  # what earlier steps wrote

    @wraps(fn)
    def run(state: State) -> dict:
        if state.get("feedback"):  # a revision: always ask the AI, and replace the saved result
            saved, input_hash = None, state.get("input_hash")
        else:
            input_hash = cache.digest(step, {k: state.get(k) for k in inputs})
            saved = cache.load(input_hash)
        record = {"step": step, "at": datetime.now(UTC).isoformat(), "seconds": 0.0, "reused": saved is not None}
        if saved is not None:
            reporter()("Nothing changed before this step: reused its saved result (no AI cost).")
            log.info("Step %s: reused the saved result", step)
            unused = {"ai_calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0}
            return {key: saved, "input_hash": input_hash, "step_runs": [{**record, **unused}]}

        log.info("Step %s: started", step)
        started = time.monotonic()
        with tally() as counts:
            update = fn(state)
        record["seconds"] = round(time.monotonic() - started, 1)
        sizes = ", ".join(f"{len(v)} {k}" for k, v in update.items() if isinstance(v, list))
        log.info("Step %s: finished in %.0fs (%s), %d AI calls, $%.4f", step, record["seconds"], sizes, counts["ai_calls"], counts["cost"])
        cache.save(input_hash, update[key])
        return {**update, "input_hash": input_hash, "step_runs": [{**record, **counts}]}

    return run


def build_graph(checkpointer=None, store=None):
    g = StateGraph(State)
    g.add_node("scope", nodes.scope)
    g.add_edge(START, "scope")
    g.add_edge("scope", STEPS[0][0])

    for i, (step, key, fn) in enumerate(STEPS):
        next_node = STEPS[i + 1][0] if i + 1 < len(STEPS) else END
        g.add_node(step, make_step(i))
        g.add_node(f"review_{step}", make_review(step, key))
        g.add_edge(step, f"review_{step}")
        g.add_conditional_edges(f"review_{step}", route_after_review(step, next_node), [step, next_node])

    return g.compile(checkpointer=checkpointer, store=store)


# Entry point for `langgraph dev` / LangGraph Studio, which supplies its own persistence.
graph = build_graph()
