"""Human review between steps.

A review node pauses the graph with `interrupt()` and expects one of:

    {"action": "approve"}
    {"action": "edit", "data": <replacement for the step output>}
    {"action": "revise", "feedback": "<what the AI should change>"}

"revise" sends the graph back to the step, which reads `state["feedback"]`.
"""

from datetime import UTC, datetime

from langgraph.types import interrupt

from digital_futures.state import State

ACTIONS = {"approve", "edit", "revise"}


def make_review(step: str, key: str):
    """Build the review node for `step`, whose output lives in `state[key]`."""

    def review(state: State) -> dict:
        if state.get("hitl", True):
            decision = interrupt({"step": step, "data": state[key]})
        else:
            decision = {"action": "approve"}

        action = decision.get("action")
        if action not in ACTIONS:
            raise ValueError(f"Unknown review action {action!r}; expected one of {sorted(ACTIONS)}")

        update: dict = {
            "feedback": decision["feedback"] if action == "revise" else None,
            "reviews": [
                {
                    "step": step,
                    "action": action,
                    "feedback": decision.get("feedback", ""),
                    "at": datetime.now(UTC).isoformat(),
                }
            ],
        }
        if action == "edit":
            update[key] = decision["data"]
        return update

    review.__name__ = f"review_{step}"
    return review


def route_after_review(step: str, next_node: str):
    """Go back to `step` when the human asked for a revision, else move on."""

    def route(state: State) -> str:
        return step if state.get("feedback") else next_node

    return route
