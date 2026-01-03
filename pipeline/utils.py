from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime

import pandas as pd


def make_race_id(season: int, round_number: int, session_type: str) -> str:
    return f"{season}_{round_number:02d}_{session_type.upper()}"


def stable_id(namespace: str, values: Iterable[object]) -> str:
    base = "|".join(str(v).strip().upper() for v in values if v is not None)
    digest = hashlib.sha1(f"{namespace}|{base}".encode()).hexdigest()[:16]
    return f"{namespace}_{digest}"


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def timedelta_to_ms(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timedelta):
        return int(value.total_seconds() * 1000)
    try:
        td = pd.to_timedelta(value)
        if pd.isna(td):
            return None
        return int(td.total_seconds() * 1000)
    except Exception:
        return None


def datetime_to_utc(value: object) -> pd.Timestamp | None:
    if value is None or pd.isna(value):
        return None
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return None
    return ts


def parse_track_status_codes(status_value: object) -> set[str]:
    if status_value is None or pd.isna(status_value):
        return set()
    text = str(status_value)
    return {c for c in text if c.isdigit()}


def derive_race_control_flags(status_value: object) -> dict[str, bool]:
    # Track status conventions are compact digit flags from FastF1.
    codes = parse_track_status_codes(status_value)
    return {
        "is_sc": "4" in codes,
        "is_vsc": "6" in codes or "7" in codes,
        "is_red_flag": "5" in codes,
        "is_yellow_flag": "2" in codes or "3" in codes,
    }
