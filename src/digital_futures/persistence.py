"""Postgres checkpointer (short-term, per run) and store (long-term agent memory)."""

from collections.abc import Iterator
from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

from digital_futures.config import settings


@contextmanager
def postgres(url: str = settings.database_url) -> Iterator[tuple[PostgresSaver, PostgresStore]]:
    with PostgresSaver.from_conn_string(url) as saver, PostgresStore.from_conn_string(url) as store:
        saver.setup()
        store.setup()
        yield saver, store
