"""Write the Mermaid source of the scenario graph and of the agent graphs its steps build.

    uv run python scripts/draw_graphs.py docs/graphs

The nodes and edges come from the compiled graphs (`get_graph()`). They are written here in
plain Mermaid (quoted labels, no HTML, no configuration header) because the text that
LangGraph's own `draw_mermaid()` produces does not render in every Markdown preview.

Nothing is sent to a model: the graphs are only compiled and drawn. The API keys in `.env`
must be set, because the model and search clients are created.
"""

import importlib
import sys
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.middleware.rubric import RubricMiddleware
from langchain.agents import create_agent

from digital_futures.config import settings
from digital_futures.graph import build_graph
from digital_futures.llm import chat_model
from digital_futures.tools import find_papers, web_search

# `digital_futures.nodes` exports the step functions under the same names as their modules.
axes, clusters, drivers = (importlib.import_module(f"digital_futures.nodes.{name}") for name in ("axes", "clusters", "drivers"))

STYLES = {
    "terminal": "fill:#ffffff,stroke:#555555,color:#111111",
    "plain": "fill:#eeeeee,stroke:#555555,color:#111111",
    "tool": "fill:#cfe3ff,stroke:#2b5fa8,color:#111111",
    "deep": "fill:#ffe08a,stroke:#9a6b00,color:#111111",
    "calls": "fill:#d8f0d8,stroke:#2f7d32,color:#111111",
    "review": "fill:#f6e3f3,stroke:#8a3d7c,color:#111111",
}
# What runs inside each step of the scenario graph (see docs/GRAPH.md).
STEP_STYLE = {"scope": "plain", "drivers": "tool", "clusters": "deep", "axes": "deep"}


def label(node) -> str:
    if node.id in ("__start__", "__end__"):
        return node.id.strip("_")
    tools = (node.metadata or {}).get("__tools")
    return f"{node.id}: {', '.join(tools)}" if tools else node.id


def style(node, steps: bool) -> str:
    if node.id in ("__start__", "__end__"):
        return "terminal"
    if node.id.startswith("review_"):
        return "review"
    return STEP_STYLE.get(node.id, "calls") if steps else "plain"


def mermaid(drawing, steps: bool = False) -> str:
    """Plain Mermaid for a drawn graph. `steps`: colour the nodes as steps of the scenario graph."""
    ids = {name: f"n{i}" for i, name in enumerate(drawing.nodes)}
    lines = ["flowchart TB"]
    lines += [f'    {ids[name]}["{label(node)}"]' for name, node in drawing.nodes.items()]
    lines += [f"    {ids[e.source]} {'-.->' if e.conditional else '-->'} {ids[e.target]}" for e in drawing.edges]
    used: dict[str, list[str]] = {}
    for name, node in drawing.nodes.items():
        used.setdefault(style(node, steps), []).append(ids[name])
    lines += [f"    classDef {name} {STYLES[name]}" for name in used]
    lines += [f"    class {','.join(members)} {name}" for name, members in used.items()]
    return "\n".join(lines) + "\n"


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    model = chat_model(settings.reasoning_model)
    grader = RubricMiddleware(model=chat_model(settings.grader_model), max_iterations=3)
    graphs = {
        "scenario_graph": build_graph(),
        "drivers_agent": create_agent(model, tools=[web_search(), find_papers], system_prompt=drivers.SYSTEM, response_format=drivers.Drivers),
        "clusters_deep_agent": create_deep_agent(model=model, system_prompt=clusters.SYSTEM, middleware=[grader], response_format=clusters.Clusters),
        "axes_deep_agent": create_deep_agent(model=model, system_prompt=axes.SYSTEM, middleware=[grader], response_format=axes.AxisSets),
    }
    for name, compiled in graphs.items():
        drawing = compiled.get_graph()
        (out / f"{name}.mmd").write_text(mermaid(drawing, steps=name == "scenario_graph"))
        print(f"{name}: {len(drawing.nodes)} nodes, {len(drawing.edges)} edges")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "docs/graphs"))
