"""Search tools for the agents: Tavily for web signals, Asta for academic papers."""

import json
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from digital_futures.config import log


SOCIAL_MEDIA = ["facebook.com", "youtube.com", "instagram.com", "tiktok.com", "x.com", "twitter.com", "reddit.com"]


def web_search(topic: str = "general") -> TavilySearch:
    """`topic="news"` searches recent news and returns publication dates."""
    return TavilySearch(max_results=5, topic=topic, exclude_domains=SOCIAL_MEDIA)  # posts and videos are weak sources


def search_web(query: str, topic: str = "general") -> list[dict]:
    """Top web results as {title, url, content, date}. A failed search does not stop a step: the model is told."""
    try:
        results = web_search(topic).invoke({"query": query})["results"]
    except Exception as e:
        log.warning("Web search failed for %r: %r", query, e)
        return [{"title": f"search failed: {type(e).__name__}", "url": "", "content": ""}]
    return [{"title": r["title"], "url": r["url"], "content": r["content"][:300], "date": (r.get("published_date") or "")[:16]} for r in results]


def search_papers(query: str) -> list[dict]:
    """Most relevant academic papers (Asta / Semantic Scholar); empty when the search fails. About 40 s."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "papers.json"
        cmd = ["asta", "literature", "find", query, "-o", str(out), "--mode", "fast", "--timeout", "150"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
            papers = json.loads(out.read_text())["results"][:8]
        except (subprocess.SubprocessError, OSError, KeyError, json.JSONDecodeError) as e:
            log.warning("Paper search failed for %r: %r", query, e)
            return []
    return [
        {
            "title": p["title"],
            "year": p.get("year"),
            "url": p.get("url") or f"https://api.semanticscholar.org/CorpusId:{p['corpusId']}",
            "abstract": (p.get("abstract") or "").strip()[:400],
        }
        for p in papers
    ]


@tool
def find_papers(query: str) -> list[dict] | str:
    """Search the academic literature (Asta / Semantic Scholar) and return the most relevant papers.

    Slow (about 40 seconds per call): use a few rich, specific queries rather than many small ones.
    """
    return search_papers(query) or "Paper search failed or found nothing; rely on web search for this topic."
