"""Run metrics for the working paper: time, cost and human involvement per step.

Computed from what the graph records while it runs: `step_runs` (each execution of a step) and
`reviews` (each human decision). Runs made before these were recorded give partial metrics.
"""

from datetime import datetime

from digital_futures.graph import STEPS


def arm(scope: dict, hitl: bool) -> str:
    """The experiment arm a run belongs to."""
    seeds = " + seed drivers" if scope.get("seed_drivers") else ""
    return f"AI{seeds} + human review" if hitl else f"AI{seeds} alone"


def _seconds(start: str, end: str) -> float:
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()


def summary(values: dict) -> dict:
    """Per step and in total: AI time and cost, human review time, revisions and edits."""
    step_runs, reviews = values.get("step_runs", []), values.get("reviews", [])
    rows = []
    for step, key, _ in STEPS:
        mine = [r for r in step_runs if r["step"] == step]
        answered = [r for r in reviews if r["step"] == step]
        waits = []
        for review in answered:  # review time: from the step's result being ready to the human's answer
            ready = [r for r in mine if r["at"] <= review["at"]]
            if ready:
                waits.append(max(0.0, _seconds(ready[-1]["at"], review["at"]) - ready[-1]["seconds"]))
        last_edit = next((r["edits"] for r in reversed(answered) if r.get("edits")), None)
        rows.append(
            {
                "step": step,
                "items": len(values[key]) if key in values and (mine or answered) else None,
                "recorded": bool(mine) or not answered,  # False: reviewed, but it ran before step runs were recorded
                "ai_runs": sum(not r["reused"] for r in mine),
                "reused": sum(r["reused"] for r in mine),
                "ai_seconds": round(sum(r["seconds"] for r in mine), 1),
                "ai_calls": sum(r["ai_calls"] for r in mine),
                "cost": round(sum(r["cost"] for r in mine), 4),
                "approved": sum(r["action"] == "approve" for r in answered),
                "edited": sum(r["action"] == "edit" for r in answered),
                "revised": sum(r["action"] == "revise" for r in answered),
                "review_seconds": round(sum(waits), 1) if waits else None,
                "kept": last_edit,  # {"before", "after", "unchanged"} of the last human edit
            }
        )
    times = sorted([r["at"] for r in step_runs] + [r["at"] for r in reviews])
    waits = [r["review_seconds"] for r in rows if r["review_seconds"] is not None]
    return {
        "arm": arm(values.get("scope", {}), values.get("hitl", True)),
        "complete": all(r["recorded"] for r in rows),  # False: some steps ran before step runs were recorded
        "steps": rows,
        "totals": {
            "elapsed_seconds": round(_seconds(times[0], times[-1]), 1) if times else None,
            "ai_seconds": round(sum(r["ai_seconds"] for r in rows), 1),
            "review_seconds": round(sum(waits), 1) if waits else None,
            "ai_calls": sum(r["ai_calls"] for r in rows),
            "cost": round(sum(r["cost"] for r in rows), 4),
            "edited": sum(r["edited"] for r in rows),
            "revised": sum(r["revised"] for r in rows),
            "scenarios": len(values.get("quadrants", [])),
        },
    }
