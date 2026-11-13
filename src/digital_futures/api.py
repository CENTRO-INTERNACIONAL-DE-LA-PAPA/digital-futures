"""Web API for the React app (frontend/), and the server that serves it.

    uv run digital-futures-web

AI steps take from seconds to minutes, so they run in a background thread: the app starts one,
then asks for its progress until it is done.
"""

import sys
import time
from functools import cache
from pathlib import Path
from threading import Thread

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from digital_futures import runs
from digital_futures.config import settings
from digital_futures.export import to_markdown
from digital_futures.graph import STEPS, build_graph
from digital_futures.metrics import arm, summary
from digital_futures.nodes.scope import DEFAULT_SCOPE
from digital_futures.persistence import connect

DIST = Path(__file__).parents[2] / "frontend" / "dist"

app = FastAPI(title="Digital Futures")
jobs: dict[str, dict] = {}  # run id -> {"busy", "started", "progress": [{"at", "message"}]}


@cache
def backend():
    checkpointer, store = connect()
    return build_graph(checkpointer, store), store


def launch(thread_id: str, action) -> None:
    """Run `action(on_progress)` in the background. A failure stays recorded in the run, for retry."""
    if jobs.get(thread_id, {}).get("busy"):
        raise HTTPException(409, "This run is already working.")
    job = jobs[thread_id] = {"busy": True, "started": time.monotonic(), "progress": []}

    def work() -> None:
        try:
            action(lambda message: job["progress"].append({"at": time.monotonic() - job["started"], "message": message}))
        except Exception:  # already logged by runs; the app shows the failed step
            pass
        finally:
            job["busy"] = False

    Thread(target=work, daemon=True).start()


def progress(thread_id: str) -> dict:
    """Whether the run is working, on which step, for how long, and what it has reported."""
    job = jobs.get(thread_id, {"busy": False, "started": time.monotonic(), "progress": []})
    following = backend()[0].get_state(runs.config(thread_id)).next if job["busy"] else ()
    working = following[0] if following and not following[0].startswith("review_") else None
    return {"busy": job["busy"], "working": working, "elapsed": time.monotonic() - job["started"], "progress": job["progress"]}


class NewRun(BaseModel):
    scope: dict
    hitl: bool = True


class Reopen(BaseModel):
    step: str


@app.get("/api/meta")
def meta() -> dict:
    return {"steps": [{"name": step, "key": key} for step, key, _ in STEPS], "default_scope": DEFAULT_SCOPE}


@app.get("/api/runs")
def list_runs() -> list[dict]:
    _, store = backend()
    return [{"id": key, **value, "arm": arm(value["scope"], value["hitl"])} for key, value in runs.listing(store)]


@app.get("/api/compare")
def compare() -> list[dict]:
    """One row per run, to compare experiment arms: how far it got and what it took."""
    graph, store = backend()
    rows = []
    for key, value in runs.listing(store):
        values = runs.state(graph, key)
        scope = values.get("scope", value["scope"])
        rows.append(
            {
                "id": key,
                "created": value["created"],
                "arm": arm(scope, value["hitl"]),
                "geography": scope.get("geography", ""),
                "drivers": len(values.get("drivers", [])),
                "clusters": len(values.get("clusters", [])),
                "finished": bool(values.get("narratives")) and not runs.pending(graph, key),
                **summary(values)["totals"],
            }
        )
    return rows


@app.post("/api/runs")
def new_run(body: NewRun) -> dict:
    graph, store = backend()
    thread_id = runs.create(store, body.scope, body.hitl)
    launch(thread_id, lambda on_progress: runs.start(graph, store, thread_id, on_progress))
    return {"id": thread_id}


@app.get("/api/runs/{thread_id}")
def get_run(thread_id: str) -> dict:
    """Everything the app shows for a run: results so far, the review it waits for, or its failed step."""
    graph, _ = backend()
    values = runs.state(graph, thread_id)
    status = progress(thread_id)
    failure = None if status["busy"] else runs.failed(graph, thread_id)  # a step that is running has not failed
    return {
        "id": thread_id,
        "values": values,
        "pending": runs.pending(graph, thread_id),
        "failed": {"step": failure[0], "error": failure[1]} if failure else None,
        "done": [r["step"] for r in values.get("reviews", []) if r["action"] != "revise"],
        **status,
    }


@app.get("/api/runs/{thread_id}/metrics")
def metrics(thread_id: str) -> dict:
    return summary(runs.state(backend()[0], thread_id))


@app.get("/api/runs/{thread_id}/export.md")
def export_markdown(thread_id: str) -> PlainTextResponse:
    text = to_markdown(runs.state(backend()[0], thread_id))
    name = f"digital-futures-{thread_id[:8]}.md"
    return PlainTextResponse(text, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/runs/{thread_id}/export.json")
def export_json(thread_id: str) -> JSONResponse:
    """Everything the run holds, as saved: results of every step, reviews and step records."""
    name = f"digital-futures-{thread_id[:8]}.json"
    return JSONResponse(runs.state(backend()[0], thread_id), headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/runs/{thread_id}/progress")
def get_progress(thread_id: str) -> dict:
    return progress(thread_id)


@app.post("/api/runs/{thread_id}/review")
def review(thread_id: str, decision: dict) -> dict:
    graph, _ = backend()
    if not runs.pending(graph, thread_id):
        raise HTTPException(409, "This run is not waiting for a review.")
    launch(thread_id, lambda on_progress: runs.resume(graph, thread_id, decision, on_progress))
    return {"ok": True}


@app.post("/api/runs/{thread_id}/retry")
def retry(thread_id: str) -> dict:
    graph, _ = backend()
    launch(thread_id, lambda on_progress: runs.retry(graph, thread_id, on_progress))
    return {"ok": True}


@app.post("/api/runs/{thread_id}/reopen")
def reopen(thread_id: str, body: Reopen) -> dict:
    graph, _ = backend()
    if jobs.get(thread_id, {}).get("busy"):
        raise HTTPException(409, "This run is working; wait for it to finish.")
    try:
        runs.reopen(graph, thread_id, body.step)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return {"ok": True}


@app.get("/api/activity")
def activity() -> dict:
    """The tail of the log file and the AI spend recorded in it."""
    if not settings.log_file.exists():
        return {"lines": [], "spent": 0.0}
    lines = settings.log_file.read_text(encoding="utf-8").splitlines()
    spent = sum(float(part[1:]) for line in lines if "AI call" in line for part in line.split(" | ") if part.startswith("$"))
    return {"lines": lines[-200:], "spent": spent}


if DIST.exists():  # the built React app; in development Vite serves it instead (npm run dev)
    app.mount("/", StaticFiles(directory=DIST, html=True), name="app")


def web() -> None:
    """Console entry point: serve the API and the built app."""
    if not DIST.exists():
        sys.exit("Build the web app first:  cd frontend && npm install && npm run build")
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8510)
