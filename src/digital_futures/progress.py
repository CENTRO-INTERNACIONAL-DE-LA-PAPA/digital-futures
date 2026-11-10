"""Progress messages from inside a node: logged, and streamed to the UI (stream_mode="custom")."""

from collections.abc import Callable

from langgraph.config import get_stream_writer

from digital_futures.config import log


def reporter() -> Callable[[str], None]:
    """Get it once at the start of a node. Outside a graph the messages are only logged."""
    try:
        write = get_stream_writer()
    except RuntimeError:
        return log.info

    def report(message: str) -> None:
        log.info(message)
        write({"progress": message})

    return report
