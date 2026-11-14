"""Write the Mermaid source of the scenario graph and of the agent graphs its steps build.

    uv run python scripts/draw_graphs.py docs/graphs

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
        (out / f"{name}.mmd").write_text(drawing.draw_mermaid())
        print(f"{name}: {len(drawing.nodes)} nodes, {len(drawing.edges)} edges")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "docs/graphs"))
