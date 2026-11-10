"""Terminal runner: drive a scenario run and answer each review in the shell.

    uv run digital-futures            # new run
    uv run digital-futures <thread>   # resume a run
"""

import json
import os
import subprocess
import sys
import tempfile
import uuid

from langgraph.types import Command

from digital_futures.graph import build_graph
from digital_futures.persistence import postgres


def ask(step: str, data) -> dict:
    print(f"\n=== Review: {step} ===\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    while True:
        choice = input("[a]pprove, [e]dit, [r]evise > ").strip().lower()
        if choice.startswith("a"):
            return {"action": "approve"}
        if choice.startswith("r"):
            return {"action": "revise", "feedback": input("Feedback for the AI > ")}
        if choice.startswith("e"):
            return {"action": "edit", "data": edit_json(data)}


def edit_json(data):
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    subprocess.run([os.environ.get("EDITOR", "nano"), f.name], check=True)
    with open(f.name) as f:
        return json.load(f)


def main() -> None:
    thread_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"Thread: {thread_id}")

    with postgres() as (checkpointer, store):
        graph = build_graph(checkpointer, store)
        pending = graph.get_state(config).interrupts
        result = graph.invoke(None if pending else {"hitl": True}, config)
        while interrupts := result.get("__interrupt__"):
            request = interrupts[0].value
            result = graph.invoke(Command(resume=ask(request["step"], request["data"])), config)

    print(json.dumps(result.get("narratives", []), indent=2, ensure_ascii=False))
