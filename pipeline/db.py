from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import psycopg

from pipeline.config import get_settings


@contextmanager
def get_conn(autocommit: bool = False) -> Iterator[psycopg.Connection]:
    settings = get_settings()
    conn = psycopg.connect(settings.db_dsn, autocommit=autocommit)
    try:
        yield conn
    finally:
        conn.close()


def bootstrap_warehouse() -> None:
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "init_warehouse.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"Warehouse SQL not found at {sql_path}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
        conn.commit()


def query_df(sql: str, params: tuple | dict | None = None) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)
