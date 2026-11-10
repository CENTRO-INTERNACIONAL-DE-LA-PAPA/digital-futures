"""Search tools for the agents: Tavily for web signals, Asta for academic papers."""

import json
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool
from langchain_tavily import TavilySearch


def web_search() -> TavilySearch:
    return TavilySearch(max_results=5)


@tool
def find_papers(query: str) -> list[dict] | str:
    """Search the academic literature (Asta / Semantic Scholar) and return the most relevant papers.

    Slow (about 40 seconds per call): use a few rich, specific queries rather than many small ones.
    """
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "papers.json"
        cmd = ["asta", "literature", "find", query, "-o", str(out), "--mode", "fast", "--timeout", "150"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
            papers = json.loads(out.read_text())["results"][:8]
        except (subprocess.SubprocessError, OSError, KeyError, json.JSONDecodeError) as e:
            return f"Paper search failed ({type(e).__name__}); rely on web search for this topic."
    return [
        {
            "title": p["title"],
            "year": p.get("year"),
            "url": p.get("url") or f"https://api.semanticscholar.org/CorpusId:{p['corpusId']}",
            "abstract": (p.get("abstract") or "").strip()[:400],
        }
        for p in papers
    ]
