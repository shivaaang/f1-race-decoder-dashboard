from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from pipeline.db import get_conn


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _normalize_records(df: pd.DataFrame) -> list[dict]:
    records = df.to_dict(orient="records")
    for rec in records:
        for key, value in list(rec.items()):
            if pd.isna(value):
                rec[key] = None
    return records


def upsert_dataframe(
    schema: str,
    table: str,
    df: pd.DataFrame,
    conflict_cols: Iterable[str],
    update_cols: Iterable[str] | None = None,
) -> None:
    if df.empty:
        return

    cols = list(df.columns)
    conflict_cols = list(conflict_cols)
    update_cols = (
        list(update_cols)
        if update_cols is not None
        else [c for c in cols if c not in conflict_cols]
    )

    col_sql = ", ".join(_q(c) for c in cols)
    values_sql = ", ".join(f"%({c})s" for c in cols)
    conflict_sql = ", ".join(_q(c) for c in conflict_cols)

    if update_cols:
        update_sql = ", ".join(f"{_q(c)} = EXCLUDED.{_q(c)}" for c in update_cols)
        on_conflict_sql = f"DO UPDATE SET {update_sql}"
    else:
        on_conflict_sql = "DO NOTHING"

    sql = (
        f"INSERT INTO {_q(schema)}.{_q(table)} ({col_sql}) VALUES ({values_sql}) "
        f"ON CONFLICT ({conflict_sql}) {on_conflict_sql}"
    )

    records = _normalize_records(df)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, records)
        conn.commit()


def replace_race_slice(schema: str, table: str, race_id: str, df: pd.DataFrame) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {_q(schema)}.{_q(table)} WHERE race_id = %s", (race_id,))
        conn.commit()

    if not df.empty:
        upsert_dataframe(schema=schema, table=table, df=df, conflict_cols=["race_id"])


def replace_staging_table(schema: str, table: str, race_id: str, df: pd.DataFrame) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {_q(schema)}.{_q(table)} WHERE race_id = %s", (race_id,))
            if not df.empty:
                cols = list(df.columns)
                col_sql = ", ".join(_q(c) for c in cols)
                values_sql = ", ".join(f"%({c})s" for c in cols)
                sql = f"INSERT INTO {_q(schema)}.{_q(table)} ({col_sql}) VALUES ({values_sql})"
                cur.executemany(sql, _normalize_records(df))
        conn.commit()


def replace_mart_table(schema: str, table: str, race_id: str, df: pd.DataFrame) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {_q(schema)}.{_q(table)} WHERE race_id = %s", (race_id,))
            if not df.empty:
                cols = list(df.columns)
                col_sql = ", ".join(_q(c) for c in cols)
                values_sql = ", ".join(f"%({c})s" for c in cols)
                sql = f"INSERT INTO {_q(schema)}.{_q(table)} ({col_sql}) VALUES ({values_sql})"
                cur.executemany(sql, _normalize_records(df))
        conn.commit()
