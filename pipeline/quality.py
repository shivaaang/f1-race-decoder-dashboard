from __future__ import annotations

import json

from pipeline.db import get_conn

CHECKS_SQL = {
    "fact_lap_rowcount": """
        SELECT COUNT(*) > 100 AS passed, jsonb_build_object('rows', COUNT(*)) AS details
        FROM curated.fact_lap
        WHERE race_id = %(race_id)s
    """,
    "fact_lap_pk_duplicates": """
        SELECT COUNT(*) = 0 AS passed,
               jsonb_build_object('duplicate_rows', COUNT(*)) AS details
        FROM (
            SELECT race_id, driver_id, lap_number, COUNT(*) c
            FROM curated.fact_lap
            WHERE race_id = %(race_id)s
            GROUP BY race_id, driver_id, lap_number
            HAVING COUNT(*) > 1
        ) d
    """,
    "lap_number_sanity": """
        SELECT COALESCE(MIN(lap_number), 0) >= 1 AND COALESCE(MAX(lap_number), 0) <= 120 AS passed,
               jsonb_build_object('min_lap', MIN(lap_number), 'max_lap', MAX(lap_number)) AS details
        FROM curated.fact_lap
        WHERE race_id = %(race_id)s
    """,
    "winner_exists": """
        SELECT COUNT(*) >= 1 AS passed,
               jsonb_build_object('winner_rows', COUNT(*)) AS details
        FROM curated.fact_session_results
        WHERE race_id = %(race_id)s
          AND finish_position = 1
    """,
}


def run_quality_checks(run_id: str, race_id: str) -> tuple[bool, list[dict]]:
    check_rows: list[dict] = []
    overall_ok = True

    with get_conn() as conn:
        with conn.cursor() as cur:
            for check_name, sql in CHECKS_SQL.items():
                cur.execute(sql, {"race_id": race_id})
                passed, details = cur.fetchone()
                status = "pass" if passed else "fail"
                overall_ok = overall_ok and bool(passed)

                record = {
                    "run_id": run_id,
                    "check_name": check_name,
                    "status": status,
                    "details_json": json.dumps(details if details is not None else {}),
                }
                check_rows.append(record)

            cur.executemany(
                """
                INSERT INTO metadata.data_quality_checks (run_id, check_name, status, details_json)
                VALUES (%(run_id)s, %(check_name)s, %(status)s, %(details_json)s::jsonb)
                """,
                check_rows,
            )
        conn.commit()

    return overall_ok, check_rows
