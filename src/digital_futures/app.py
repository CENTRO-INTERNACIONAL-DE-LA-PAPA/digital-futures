"""Web app: start a scenario run and review each step in the browser.

    uv run digital-futures-web
"""

import json
import sys
import time

import pandas as pd
import streamlit as st

from digital_futures import runs
from digital_futures.config import settings
from digital_futures.graph import STEPS, build_graph
from digital_futures.nodes.scope import DEFAULT_SCOPE
from digital_futures.persistence import connect

TITLES = {
    "drivers": "2 · Drivers of change",
    "clusters": "3 · Clusters",
    "score_impact": "4a · Impact and uncertainty",
    "score_policy": "4b · Attention in policy arenas",
    "critical": "5 · Critical drivers",
    "axes": "6 · Axes of uncertainty",
    "quadrants": "7 · Quadrants",
    "narratives": "8 · Narratives",
}


@st.cache_resource
def backend():
    checkpointer, store = connect()
    return build_graph(checkpointer, store), store


# --- tables: nested records become "x.pole_a" columns, lists are edited as JSON text ----------


def leaves(row: dict, prefix: str = ""):
    """Flatten nested dicts: {"x": {"pole_a": 1}} yields ("x.pole_a", 1)."""
    for k, v in row.items():
        if isinstance(v, dict):
            yield from leaves(v, f"{prefix}{k}.")
        else:
            yield prefix + k, v


def to_table(data: list) -> pd.DataFrame:
    if data and not isinstance(data[0], dict):
        return pd.DataFrame({"value": data})
    return pd.DataFrame(
        [{k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for k, v in leaves(r)} for r in data]
    )


def from_table(df: pd.DataFrame, like: list) -> list:
    if like and not isinstance(like[0], dict):
        return [v for v in df["value"] if isinstance(v, str) and v]
    lists = {k for r in like for k, v in leaves(r) if isinstance(v, list)}
    out = []
    for record in df.to_dict("records"):
        row: dict = {}
        for k, v in record.items():
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            if k in lists and isinstance(v, str):
                v = json.loads(v or "null")
            elif isinstance(v, float) and v.is_integer():
                v = int(v)
            *path, last = k.split(".")
            target = row
            for part in path:
                target = target.setdefault(part, {})
            target[last] = v
        out.append(row)
    return out


# --- progress -------------------------------------------------------------------------------


def working(label: str):
    """A live status panel; returns it and a callback that appends timed progress lines."""
    status = st.status(label, expanded=True)
    started = time.monotonic()

    def on_progress(message: str) -> None:
        status.write(f"`{time.monotonic() - started:>4.0f}s` {message}")
        status.update(label=message, expanded=True)

    return status, on_progress


def advance(graph, thread_id: str, label: str, action) -> None:
    """Run `action(on_progress)` with a live panel. A failed step is kept in the run and offered for retry."""
    status, on_progress = working(label)
    try:
        action(on_progress)
    except Exception:
        if not runs.failed(graph, thread_id):
            raise
        status.update(state="error")
    else:
        status.update(state="complete")
    st.rerun()


# --- views -----------------------------------------------------------------------------------


def show_axes(axis_sets: list) -> None:
    for s in axis_sets:
        st.markdown(
            f"**{s['name']}**\n"
            + "".join(f"- {k.upper()} · {s[k].get('driver', s[k]['driver_id'])}: {s[k]['pole_a']} ⟷ {s[k]['pole_b']}\n" for k in "xy")
            + f"\n{s.get('rationale', '')}"
        )


def show_quadrants(quadrants: list, narratives: list = ()) -> None:
    """Scenarios grouped by set of axes; with `narratives`, each one also shows its four accounts."""
    voices = {(n.get("axis_set"), n["title"]): n["personas"] for n in narratives}
    for axis_set in dict.fromkeys(q["axis_set"] for q in quadrants):
        st.subheader(axis_set)
        for q in (q for q in quadrants if q["axis_set"] == axis_set):
            with st.expander(f"{q['title']} — {q['x_pole']} · {q['y_pole']}", expanded=not narratives):
                st.write(q["sketch"])
                for persona, text in voices.get((axis_set, q["title"]), {}).items():
                    st.markdown(f"**{persona.title()}**\n\n{text}")


def show_narratives(narratives: list) -> None:
    for n in narratives:
        with st.expander(f"{n['title']} ({n.get('axis_set', '')})"):
            for persona, text in n["personas"].items():
                st.markdown(f"**{persona.title()}**\n\n{text}")


VIEWS = {"axes": show_axes, "quadrants": show_quadrants, "narratives": show_narratives}


def new_run_form(graph, store) -> None:
    st.header("New scenario run")
    with st.form("scope"):
        theme = st.text_input("Theme", DEFAULT_SCOPE["theme"])
        geography = st.text_input("Geography", DEFAULT_SCOPE["geography"])
        c1, c2 = st.columns(2)
        current = c1.number_input("Current year", value=DEFAULT_SCOPE["current_year"], step=1)
        horizon = c2.number_input("Horizon year", value=DEFAULT_SCOPE["horizon_year"], step=1)
        target = st.number_input("Target number of drivers", value=DEFAULT_SCOPE["target_drivers"], min_value=5, step=5)
        sets = st.number_input(
            "Sets of axes to propose",
            value=DEFAULT_SCOPE["axis_sets"],
            min_value=1,
            max_value=6,
            help="Each set is one 2x2 matrix: four scenarios, each told by four people.",
        )
        seeds = st.text_area("Seed drivers (optional, one per line)", help="Drivers people bring in, e.g. from a workshop.")
        hitl = st.toggle("Human review after each step", value=True)
        if st.form_submit_button("Start", type="primary"):
            scope = {
                "theme": theme,
                "geography": geography,
                "current_year": int(current),
                "horizon_year": int(horizon),
                "seed_drivers": [s.strip() for s in seeds.splitlines() if s.strip()],
                "target_drivers": int(target),
                "axis_sets": int(sets),
            }
            thread_id = runs.create(store, scope, hitl)
            st.query_params["run"] = thread_id
            advance(graph, thread_id, "Starting…", lambda on_progress: runs.start(graph, store, thread_id, on_progress))


def review_panel(graph, thread_id: str, request: dict, round_: int) -> None:
    step, data = request["step"], request["data"]
    st.header(TITLES[step])
    if step in VIEWS:
        VIEWS[step](data)
        st.caption("Edit the text in the table below, or delete a row to drop it.")

    edited = st.data_editor(to_table(data), num_rows="dynamic", use_container_width=True, key=f"edit-{thread_id}-{round_}")

    decision = None
    if st.button("Continue", type="primary"):
        new = from_table(edited, data)
        decision = {"action": "approve"} if new == data else {"action": "edit", "data": new}
    with st.expander("Ask the AI to revise this step"):
        feedback = st.text_area("What should change?", key=f"feedback-{thread_id}-{round_}")
        if st.button("Revise") and feedback.strip():
            decision = {"action": "revise", "feedback": feedback.strip()}

    if decision:
        advance(graph, thread_id, "Working…", lambda on_progress: runs.resume(graph, thread_id, decision, on_progress))


def activity_log() -> None:
    """The tail of the log file: steps, AI calls with tokens and cost, failures."""
    with st.expander("Activity log"):
        if not settings.log_file.exists():
            st.caption("Nothing logged yet.")
            return
        lines = settings.log_file.read_text(encoding="utf-8").splitlines()
        spent = sum(float(part[1:]) for line in lines if "AI call" in line for part in line.split(" | ") if part.startswith("$"))
        st.caption(f"{settings.log_file} · AI spend recorded in this log: ${spent:.2f}")
        st.code("\n".join(lines[-80:]), language=None, wrap_lines=True)


def failed_panel(graph, thread_id: str, step: str, error: str) -> None:
    st.header(TITLES.get(step, step))
    st.error("This step did not finish. Retry runs only this step again; everything before it is kept.")
    with st.expander("Error details"):
        st.code(error, wrap_lines=True)
    if st.button("Retry", type="primary"):
        advance(graph, thread_id, "Retrying…", lambda on_progress: runs.retry(graph, thread_id, on_progress))


def run_view(graph, thread_id: str) -> None:
    values = graph.get_state(runs.config(thread_id)).values
    request = runs.pending(graph, thread_id)
    failure = runs.failed(graph, thread_id)
    done = [r["step"] for r in values.get("reviews", []) if r["action"] != "revise"]

    with st.sidebar:
        st.subheader("Progress")
        st.caption("Click a finished step to go back to its review.")
        for step, _, _ in STEPS:
            label = TITLES[step]
            if step in done:
                if st.button(f"✅ {label}", key=f"reopen-{step}", type="tertiary"):
                    runs.reopen(graph, thread_id, step)
                    st.rerun()
            elif failure and failure[0] == step:
                st.write(f"❌ {label}")
            else:
                st.write(f"{'👉' if request and request['step'] == step else '▫️'} {label}")

    if request:
        review_panel(graph, thread_id, request, len(values.get("reviews", [])))
    elif failure:
        failed_panel(graph, thread_id, *failure)
    else:
        st.header("Scenarios")
        show_quadrants(values.get("quadrants", []), values.get("narratives", []))

    activity_log()
    with st.expander("All results so far"):
        st.json({k: v for k, v in values.items() if k not in {"feedback"}}, expanded=False)


def page() -> None:
    st.set_page_config(page_title="Digital Futures", layout="wide")
    graph, store = backend()

    with st.sidebar:
        st.title("Digital Futures")
        options = {"": "➕ New run"} | {k: f"{v['created'][:16]} · {v['scope'].get('geography', '')}" for k, v in runs.listing(store)}
        current = st.query_params.get("run", "")
        choice = st.selectbox("Run", list(options), index=list(options).index(current) if current in options else 0, format_func=lambda k: options[k])
        st.query_params["run"] = choice

    if choice:
        run_view(graph, choice)
    else:
        new_run_form(graph, store)


def web() -> None:
    """Console entry point: launch Streamlit on this file."""
    from streamlit.web import cli

    sys.argv = ["streamlit", "run", __file__]
    sys.exit(cli.main())


if __name__ == "__main__":
    page()
