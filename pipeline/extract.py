from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fastf1
import pandas as pd

from pipeline.config import get_settings
from pipeline.utils import datetime_to_utc, make_race_id

logger = logging.getLogger(__name__)


@dataclass
class SessionExtract:
    season: int
    round_number: int
    session_type: str
    race_id: str
    event_name: str
    circuit: str | None
    country: str | None
    race_datetime_utc: pd.Timestamp | None
    fastf1_event_key: str | None
    laps: pd.DataFrame
    results: pd.DataFrame
    weather: pd.DataFrame


def _enable_cache() -> None:
    settings = get_settings()
    Path(settings.fastf1_cache_dir).mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(settings.fastf1_cache_dir)


def _with_retries(label: str, fn, attempts: int = 4, base_sleep_seconds: float = 2.0):
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == attempts:
                break
            sleep_for = base_sleep_seconds * (2 ** (attempt - 1))
            logger.warning(
                "%s failed on attempt %s/%s: %s. Retrying in %.1fs",
                label,
                attempt,
                attempts,
                exc,
                sleep_for,
            )
            time.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc


def fetch_event_schedule(season: int, session_type: str = "R") -> pd.DataFrame:
    _enable_cache()

    def _load_schedule() -> pd.DataFrame:
        schedule_df = fastf1.get_event_schedule(season, include_testing=False)
        if schedule_df is None or schedule_df.empty:
            raise ValueError(f"Empty schedule returned for season={season}")
        return schedule_df

    schedule = _with_retries(
        label=f"schedule fetch season={season}",
        fn=_load_schedule,
        attempts=5,
        base_sleep_seconds=2.0,
    )

    schedule = schedule.copy()
    schedule["season"] = season
    schedule["round"] = schedule["RoundNumber"].astype(int)
    schedule["event_name"] = schedule["EventName"].astype(str)
    schedule["circuit"] = schedule.get("Location", pd.Series([None] * len(schedule)))
    schedule["country"] = schedule.get("Country", pd.Series([None] * len(schedule)))
    schedule["race_datetime_utc"] = schedule.get(
        "EventDate", pd.Series([None] * len(schedule))
    ).apply(datetime_to_utc)
    schedule["session_type"] = session_type.upper()
    schedule["race_id"] = schedule.apply(
        lambda row: make_race_id(int(row["season"]), int(row["round"]), row["session_type"]), axis=1
    )
    schedule["fastf1_event_key"] = (
        schedule.get("OfficialEventName", pd.Series([None] * len(schedule)))
        .fillna(schedule["event_name"])
        .astype(str)
    )

    return schedule[
        [
            "race_id",
            "season",
            "round",
            "event_name",
            "circuit",
            "country",
            "race_datetime_utc",
            "fastf1_event_key",
            "session_type",
        ]
    ]


def fetch_session_data(season: int, round_number: int, session_type: str = "R") -> SessionExtract:
    _enable_cache()

    def _load_session() -> SessionExtract:
        session = fastf1.get_session(season, round_number, session_type)
        session.load(laps=True, telemetry=False, weather=True, messages=True)

        event: Any = session.event
        race_id = make_race_id(season, round_number, session_type)
        race_datetime_utc = datetime_to_utc(getattr(session, "date", None))

        laps = session.laps.copy().reset_index(drop=True)
        if laps.empty:
            raise ValueError(f"No lap rows returned for {race_id}")

        results = session.results.copy().reset_index(drop=True)
        weather = session.weather_data.copy().reset_index(drop=True)

        return SessionExtract(
            season=season,
            round_number=round_number,
            session_type=session_type,
            race_id=race_id,
            event_name=str(getattr(event, "EventName", f"{season} Round {round_number}")),
            circuit=getattr(event, "Location", None),
            country=getattr(event, "Country", None),
            race_datetime_utc=race_datetime_utc,
            fastf1_event_key=str(
                getattr(event, "OfficialEventName", getattr(event, "EventName", ""))
            ),
            laps=laps,
            results=results,
            weather=weather,
        )

    return _with_retries(
        label=f"session fetch season={season} round={round_number} type={session_type}",
        fn=_load_session,
        attempts=4,
        base_sleep_seconds=2.0,
    )
