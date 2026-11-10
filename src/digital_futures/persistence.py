"""Postgres checkpointer (short-term, per run) and store (long-term memory, run registry)."""

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from digital_futures.config import settings


def connect(url: str = settings.database_url) -> tuple[PostgresSaver, PostgresStore]:
    pool = ConnectionPool(url, kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row})
    saver, store = PostgresSaver(pool), PostgresStore(pool)
    saver.setup()
    store.setup()
    return saver, store
