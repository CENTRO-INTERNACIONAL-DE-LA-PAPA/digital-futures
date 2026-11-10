"""Node 5: critical drivers (most uncertain, highest impact, then least discussed). TODO(phase 5)."""

from digital_futures.state import State


def critical(state: State) -> dict:
    ranked = sorted(
        state["scores"],
        key=lambda s: (-s["impact"] * s["uncertainty"], s.get("policy_attention", 3)),
    )
    return {"critical": [s["driver_id"] for s in ranked[:4]]}
