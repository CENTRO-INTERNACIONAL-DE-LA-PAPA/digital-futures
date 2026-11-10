"""Progress messages from inside a node, streamed to the UI (stream_mode="custom")."""

from collections.abc import Callable

from langgraph.config import get_stream_writer


def reporter() -> Callable[[str], None]:
    """Get it once at the start of a node; it is a no-op when called outside a graph."""
    try:
        write = get_stream_writer()
    except RuntimeError:
        return lambda message: None
    return lambda message: write({"progress": message})
