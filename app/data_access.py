from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine() -> Engine:
    dsn = os.getenv("F1_DB_DSN", "postgresql+psycopg://f1app:f1app@localhost:5432/f1dw")
    if dsn.startswith("postgresql://"):
        dsn = dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(dsn, pool_pre_ping=True)


def query_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def get_races_for_season(season: int) -> pd.DataFrame:
    try:
        return query_df(
            """
            SELECT race_id, season, round, event_name, circuit, country, race_datetime_utc,
                   wikipedia_url, formula1_url
            FROM metadata.races_catalog
            WHERE season = :season
              AND session_type = 'R'
              AND is_ingested = TRUE
            ORDER BY round
            """,
            {"season": season},
        )
    except Exception:
        # Columns may not exist yet — fall back without link columns
        df = query_df(
            """
            SELECT race_id, season, round, event_name, circuit, country, race_datetime_utc
            FROM metadata.races_catalog
            WHERE season = :season
              AND session_type = 'R'
              AND is_ingested = TRUE
            ORDER BY round
            """,
            {"season": season},
        )
        df["wikipedia_url"] = None
        df["formula1_url"] = None
        return df


def load_race_bundle(race_id: str) -> dict[str, pd.DataFrame]:
    data = {
        "gap": query_df(
            """
            SELECT g.race_id,
                   g.lap_number,
                   g.leader_driver_id,
                   g.p2_driver_id,
                   g.gap_p2_to_leader_ms,
                   d1.driver_code AS leader_driver_code,
                   d1.full_name AS leader_full_name,
                   d2.driver_code AS p2_driver_code,
                   d2.full_name AS p2_full_name
            FROM marts.mart_gap_timeline g
            LEFT JOIN curated.dim_driver d1 ON d1.driver_id = g.leader_driver_id
            LEFT JOIN curated.dim_driver d2 ON d2.driver_id = g.p2_driver_id
            WHERE g.race_id = :race_id
            ORDER BY g.lap_number
            """,
            {"race_id": race_id},
        ),
        "race_control": query_df(
            """
            SELECT race_id, lap_number, is_sc, is_vsc, is_red_flag, is_yellow_flag
            FROM curated.fact_race_control
            WHERE race_id = :race_id
            ORDER BY lap_number
            """,
            {"race_id": race_id},
        ),
        "pit_markers": query_df(
            """
            SELECT f.race_id,
                   f.driver_id,
                   f.lap_number,
                   d.driver_code,
                   d.full_name
            FROM curated.fact_lap f
            LEFT JOIN curated.dim_driver d ON d.driver_id = f.driver_id
            WHERE f.race_id = :race_id
              AND f.is_pit_in_lap = TRUE
            ORDER BY f.lap_number
            """,
            {"race_id": race_id},
        ),
        "positions": query_df(
            """
            SELECT p.race_id,
                   p.driver_id,
                   p.lap_number,
                   p.position,
                   p.team_id,
                   d.driver_code,
                   d.full_name,
                   t.team_color,
                   t.team_name
            FROM marts.mart_position_chart p
            LEFT JOIN curated.dim_driver d ON d.driver_id = p.driver_id
            LEFT JOIN curated.dim_team t ON t.team_id = p.team_id
            WHERE p.race_id = :race_id
            ORDER BY p.lap_number
            """,
            {"race_id": race_id},
        ),
        "stints": query_df(
            """
            SELECT s.race_id,
                   s.driver_id,
                   s.stint,
                   s.start_lap,
                   s.end_lap,
                   s.compound,
                   s.stint_laps,
                   s.median_lap_ms,
                   s.avg_lap_ms,
                   s.pit_lap,
                   d.driver_code,
                   d.full_name,
                   t.team_color,
                   t.team_name
            FROM marts.mart_stint_summary s
            LEFT JOIN curated.dim_driver d ON d.driver_id = s.driver_id
            LEFT JOIN curated.fact_session_results r
                ON r.race_id = s.race_id AND r.driver_id = s.driver_id
            LEFT JOIN curated.dim_team t ON t.team_id = r.team_id
            WHERE s.race_id = :race_id
            ORDER BY d.driver_code, s.stint
            """,
            {"race_id": race_id},
        ),
        "results": query_df(
            """
            SELECT r.driver_id,
                   r.team_id,
                   r.grid_position,
                   r.finish_position,
                   r.classified_position,
                   r.status,
                   r.points,
                   r.race_time_ms,
                   r.gap_to_winner_ms,
                   d.driver_code,
                   d.full_name,
                   t.team_name,
                   t.team_color
            FROM curated.fact_session_results r
            LEFT JOIN curated.dim_driver d ON d.driver_id = r.driver_id
            LEFT JOIN curated.dim_team t ON t.team_id = r.team_id
            WHERE r.race_id = :race_id
            ORDER BY r.finish_position NULLS LAST
            """,
            {"race_id": race_id},
        ),
        "lap_times": query_df(
            """
            SELECT f.race_id,
                   f.driver_id,
                   f.lap_number,
                   f.lap_time_ms,
                   f.sector1_ms,
                   f.sector2_ms,
                   f.sector3_ms,
                   f.compound,
                   f.tyre_life_laps,
                   f.position,
                   f.is_pit_in_lap,
                   f.is_pit_out_lap,
                   f.is_accurate,
                   d.driver_code,
                   d.full_name,
                   t.team_name,
                   t.team_color
            FROM curated.fact_lap f
            LEFT JOIN curated.dim_driver d ON d.driver_id = f.driver_id
            LEFT JOIN curated.fact_session_results r
                ON r.race_id = f.race_id AND r.driver_id = f.driver_id
            LEFT JOIN curated.dim_team t ON t.team_id = r.team_id
            WHERE f.race_id = :race_id
            ORDER BY f.lap_number, d.driver_code
            """,
            {"race_id": race_id},
        ),
        "drivers": query_df(
            """
            SELECT d.driver_id,
                   d.driver_code,
                   d.full_name,
                   t.team_name,
                   r.finish_position
            FROM curated.fact_session_results r
            JOIN curated.dim_driver d ON d.driver_id = r.driver_id
            LEFT JOIN curated.dim_team t ON t.team_id = r.team_id
            WHERE r.race_id = :race_id
            ORDER BY r.finish_position NULLS LAST, d.driver_code
            """,
            {"race_id": race_id},
        ),
        "weather": query_df(
            """
            SELECT race_id,
                   timestamp_utc,
                   air_temp_c,
                   track_temp_c,
                   humidity_pct,
                   rainfall
            FROM curated.fact_weather_minute
            WHERE race_id = :race_id
            ORDER BY timestamp_utc
            """,
            {"race_id": race_id},
        ),
    }

    return data
