"""Terminal runner: drive a scenario run and answer each review in the shell.

    uv run digital-futures            # new run
    uv run digital-futures <thread>   # resume a run
"""

import json
import os
import subprocess
import sys
import tempfile

from digital_futures import runs
from digital_futures.graph import build_graph
from digital_futures.persistence import connect


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
    checkpointer, store = connect()
    graph = build_graph(checkpointer, store)
    if len(sys.argv) > 1:
        thread_id = sys.argv[1]
        if runs.failed(graph, thread_id):
            runs.retry(graph, thread_id)
    else:
        thread_id = runs.create(store)
        print(f"Run: {thread_id}")
        runs.start(graph, store, thread_id)

    while request := runs.pending(graph, thread_id):
        runs.resume(graph, thread_id, ask(request["step"], request["data"]))

    narratives = graph.get_state(runs.config(thread_id)).values.get("narratives", [])
    print(json.dumps(narratives, indent=2, ensure_ascii=False))
