"""Postgres connection helper with a small pool.

Vectors are passed as string literals cast to ::vector (see to_pgvector), so we
don't depend on numpy or the pgvector python adapter — fewer install headaches.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import get_settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
        )
    return _pool


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def to_pgvector(values: Sequence[float]) -> str:
    """Format an embedding as a Postgres vector literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"
