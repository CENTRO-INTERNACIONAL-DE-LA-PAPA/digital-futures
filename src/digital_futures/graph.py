"""The scenario graph: scope, then each step followed by a human review."""

import time
from functools import wraps

from langgraph.graph import END, START, StateGraph

from digital_futures import nodes
from digital_futures.config import log
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
    ("quadrants", "quadrants", nodes.quadrants),
    ("narratives", "narratives", nodes.narratives),
]


def logged(step: str, fn):
    """Log when a step starts, how long it takes, and how many items it returns."""

    @wraps(fn)
    def run(state: State) -> dict:
        log.info("Step %s: started", step)
        started = time.monotonic()
        update = fn(state)
        sizes = ", ".join(f"{len(v)} {k}" for k, v in update.items() if isinstance(v, list))
        log.info("Step %s: finished in %.0fs (%s)", step, time.monotonic() - started, sizes)
        return update

    return run


def build_graph(checkpointer=None, store=None):
    g = StateGraph(State)
    g.add_node("scope", nodes.scope)
    g.add_edge(START, "scope")
    g.add_edge("scope", STEPS[0][0])

    for i, (step, key, fn) in enumerate(STEPS):
        next_node = STEPS[i + 1][0] if i + 1 < len(STEPS) else END
        g.add_node(step, logged(step, fn))
        g.add_node(f"review_{step}", make_review(step, key))
        g.add_edge(step, f"review_{step}")
        g.add_conditional_edges(f"review_{step}", route_after_review(step, next_node), [step, next_node])

    return g.compile(checkpointer=checkpointer, store=store)


# Entry point for `langgraph dev` / LangGraph Studio, which supplies its own persistence.
graph = build_graph()
