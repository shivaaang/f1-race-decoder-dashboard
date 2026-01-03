from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

import pandas as pd

from pipeline.db import bootstrap_warehouse, get_conn, query_df
from pipeline.extract import SessionExtract, fetch_event_schedule, fetch_session_data
from pipeline.load import replace_mart_table, replace_staging_table, upsert_dataframe
from pipeline.marts import build_gap_timeline, build_position_chart, build_stint_summary
from pipeline.quality import run_quality_checks
from pipeline.transform import StagingBundle, build_curated_bundle, build_staging_bundle
from pipeline.utils import make_race_id, now_utc

logger = logging.getLogger(__name__)


def _start_run(season: int, round_number: int, session_type: str, code_version: str) -> str:
    run_id = str(uuid.uuid4())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO metadata.ingestion_runs (
                    run_id, started_at, status, season, round, session_type, code_version, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    now_utc(),
                    "running",
                    season,
                    round_number,
                    session_type,
                    code_version,
                    None,
                ),
            )
        conn.commit()
    return run_id


def _finish_run(run_id: str, status: str, notes: dict[str, Any] | None = None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE metadata.ingestion_runs
                SET finished_at = %s,
                    status = %s,
                    notes = %s
                WHERE run_id = %s
                """,
                (now_utc(), status, json.dumps(notes or {}), run_id),
            )
        conn.commit()


def upsert_races_catalog(schedule_df: pd.DataFrame) -> None:
    if schedule_df.empty:
        return

    payload = schedule_df.copy()
    payload["is_ingested"] = False
    payload["last_ingested_at"] = None

    upsert_dataframe(
        schema="metadata",
        table="races_catalog",
        df=payload,
        conflict_cols=["race_id"],
        update_cols=[
            "season",
            "round",
            "event_name",
            "circuit",
            "country",
            "race_datetime_utc",
            "fastf1_event_key",
            "session_type",
        ],
    )


def refresh_schedule_for_season(season: int, session_type: str = "R") -> None:
    schedule_df = fetch_event_schedule(season=season, session_type=session_type)
    upsert_races_catalog(schedule_df)


def _stage_load(staging: StagingBundle, race_id: str) -> None:
    replace_staging_table("staging", "session_laps", race_id=race_id, df=staging.laps)
    replace_staging_table("staging", "session_results", race_id=race_id, df=staging.results)
    replace_staging_table("staging", "session_weather", race_id=race_id, df=staging.weather)


def _upsert_curated(curated) -> None:
    upsert_dataframe("curated", "dim_race", curated.dim_race, conflict_cols=["race_id"])
    upsert_dataframe("curated", "dim_driver", curated.dim_driver, conflict_cols=["driver_id"])
    upsert_dataframe("curated", "dim_team", curated.dim_team, conflict_cols=["team_id"])
    upsert_dataframe(
        "curated",
        "dim_driver_team_season",
        curated.dim_driver_team_season,
        conflict_cols=["season", "driver_id", "team_id"],
        update_cols=[],
    )
    upsert_dataframe(
        "curated",
        "fact_lap",
        curated.fact_lap,
        conflict_cols=["race_id", "driver_id", "lap_number"],
    )
    upsert_dataframe(
        "curated",
        "fact_session_results",
        curated.fact_session_results,
        conflict_cols=["race_id", "driver_id"],
    )
    upsert_dataframe(
        "curated",
        "fact_race_control",
        curated.fact_race_control,
        conflict_cols=["race_id", "lap_number"],
    )
    upsert_dataframe(
        "curated",
        "fact_weather_minute",
        curated.fact_weather_minute,
        conflict_cols=["race_id", "timestamp_utc"],
    )


def _build_and_load_marts(race_id: str) -> None:
    fact_lap = query_df(
        "SELECT * FROM curated.fact_lap WHERE race_id = %(race_id)s",
        params={"race_id": race_id},
    )
    fact_results = query_df(
        "SELECT * FROM curated.fact_session_results WHERE race_id = %(race_id)s",
        params={"race_id": race_id},
    )

    mart_gap = build_gap_timeline(fact_lap)
    mart_position = build_position_chart(fact_lap, fact_results)
    mart_stint = build_stint_summary(fact_lap)

    replace_mart_table("marts", "mart_gap_timeline", race_id=race_id, df=mart_gap)
    replace_mart_table("marts", "mart_position_chart", race_id=race_id, df=mart_position)
    replace_mart_table("marts", "mart_stint_summary", race_id=race_id, df=mart_stint)


def _mark_race_ingested(race_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE metadata.races_catalog
                SET is_ingested = TRUE,
                    last_ingested_at = %(ts)s
                WHERE race_id = %(race_id)s
                """,
                {"race_id": race_id, "ts": now_utc()},
            )
        conn.commit()


def start_ingestion_run(
    season: int, round_number: int, session_type: str, code_version: str
) -> str:
    return _start_run(
        season=season,
        round_number=round_number,
        session_type=session_type,
        code_version=code_version,
    )


def finalize_ingestion_run(run_id: str, status: str, notes: dict[str, Any] | None = None) -> None:
    _finish_run(run_id=run_id, status=status, notes=notes)


def extract_to_staging(
    run_id: str,
    season: int,
    round_number: int,
    session_type: str = "R",
) -> dict[str, Any]:
    extracted: SessionExtract = fetch_session_data(season, round_number, session_type)
    staging = build_staging_bundle(extracted, run_id=run_id)
    _stage_load(staging=staging, race_id=extracted.race_id)
    return {
        "race_id": extracted.race_id,
        "event_name": extracted.event_name,
        "circuit": extracted.circuit,
        "country": extracted.country,
        "race_datetime_utc": (
            extracted.race_datetime_utc.isoformat()
            if extracted.race_datetime_utc is not None
            else None
        ),
    }


def load_staging_bundle(race_id: str) -> StagingBundle:
    laps = query_df(
        "SELECT * FROM staging.session_laps WHERE race_id = %(race_id)s",
        params={"race_id": race_id},
    )
    results = query_df(
        "SELECT * FROM staging.session_results WHERE race_id = %(race_id)s",
        params={"race_id": race_id},
    )
    weather = query_df(
        "SELECT * FROM staging.session_weather WHERE race_id = %(race_id)s",
        params={"race_id": race_id},
    )
    return StagingBundle(laps=laps, results=results, weather=weather)


def transform_to_curated(
    race_id: str,
    season: int,
    round_number: int,
    event_name: str,
    circuit: str | None,
    country: str | None,
    race_datetime_utc: str | None,
) -> None:
    staging = load_staging_bundle(race_id=race_id)
    curated = build_curated_bundle(
        race_id=race_id,
        season=season,
        round_number=round_number,
        event_name=event_name,
        circuit=circuit,
        country=country,
        race_date_utc=race_datetime_utc,
        staging=staging,
    )
    _upsert_curated(curated)


def load_marts_for_race(race_id: str) -> None:
    _build_and_load_marts(race_id=race_id)


def mark_race_ingested(race_id: str) -> None:
    _mark_race_ingested(race_id=race_id)


def run_quality_for_run(run_id: str, race_id: str) -> dict[str, Any]:
    passed, checks = run_quality_checks(run_id=run_id, race_id=race_id)
    return {"passed": passed, "checks": checks}


def ingest_single_race(
    season: int,
    round_number: int,
    session_type: str = "R",
    code_version: str = "dev",
) -> dict[str, Any]:
    bootstrap_warehouse()
    refresh_schedule_for_season(season=season, session_type=session_type)

    run_id = _start_run(
        season=season,
        round_number=round_number,
        session_type=session_type,
        code_version=code_version,
    )
    timings: dict[str, float] = {}

    race_id = make_race_id(season, round_number, session_type)

    try:
        start = time.perf_counter()
        extracted: SessionExtract = fetch_session_data(season, round_number, session_type)
        timings["extract_fetch"] = time.perf_counter() - start

        start = time.perf_counter()
        staging = build_staging_bundle(extracted, run_id=run_id)
        _stage_load(staging=staging, race_id=race_id)
        timings["extract_stage"] = time.perf_counter() - start

        start = time.perf_counter()
        curated = build_curated_bundle(
            race_id=race_id,
            season=season,
            round_number=round_number,
            event_name=extracted.event_name,
            circuit=extracted.circuit,
            country=extracted.country,
            race_date_utc=extracted.race_datetime_utc,
            staging=staging,
        )
        _upsert_curated(curated)
        timings["transform_curated"] = time.perf_counter() - start

        start = time.perf_counter()
        _build_and_load_marts(race_id)
        timings["load_marts"] = time.perf_counter() - start

        start = time.perf_counter()
        passed, checks = run_quality_checks(run_id=run_id, race_id=race_id)
        timings["quality"] = time.perf_counter() - start

        _mark_race_ingested(race_id)

        final_status = "success" if passed else "quality_failed"
        notes = {"timings_sec": timings, "quality_checks": checks}
        _finish_run(run_id, final_status, notes)

        return {"run_id": run_id, "race_id": race_id, "status": final_status, "timings": timings}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion failed for %s", race_id)
        _finish_run(run_id, "failed", {"error": str(exc), "timings_sec": timings})
        raise


def list_rounds_for_season(season: int, session_type: str = "R") -> list[int]:
    refresh_schedule_for_season(season, session_type=session_type)
    df = query_df(
        """
        SELECT round FROM metadata.races_catalog
        WHERE season = %(season)s
          AND session_type = %(session_type)s
          AND round > 0
        ORDER BY round
        """,
        params={"season": season, "session_type": session_type},
    )
    return [int(v) for v in df["round"].tolist()]


def backfill_season(
    season: int, session_type: str = "R", code_version: str = "dev"
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    try:
        rounds = list_rounds_for_season(season, session_type=session_type)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch rounds for season=%s", season)
        return [
            {
                "season": season,
                "status": "failed",
                "error": f"schedule_fetch_failed: {exc}",
            }
        ]

    for rnd in rounds:
        try:
            results.append(
                ingest_single_race(
                    season=season,
                    round_number=rnd,
                    session_type=session_type,
                    code_version=code_version,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Backfill failed for season=%s round=%s", season, rnd)
            results.append(
                {
                    "season": season,
                    "round": rnd,
                    "race_id": make_race_id(season, rnd, session_type),
                    "status": "failed",
                    "error": str(exc),
                }
            )
    return results


def backfill_range(
    season_start: int,
    season_end: int,
    session_type: str = "R",
    code_version: str = "dev",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for season in range(season_start, season_end + 1):
        try:
            results.extend(
                backfill_season(season=season, session_type=session_type, code_version=code_version)
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Backfill season crashed unexpectedly for season=%s", season)
            results.append(
                {
                    "season": season,
                    "status": "failed",
                    "error": str(exc),
                }
            )
    return results
