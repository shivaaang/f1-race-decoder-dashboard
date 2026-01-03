from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pipeline.extract import SessionExtract
from pipeline.utils import derive_race_control_flags, stable_id, timedelta_to_ms


@dataclass
class StagingBundle:
    laps: pd.DataFrame
    results: pd.DataFrame
    weather: pd.DataFrame


@dataclass
class CuratedBundle:
    dim_race: pd.DataFrame
    dim_driver: pd.DataFrame
    dim_team: pd.DataFrame
    dim_driver_team_season: pd.DataFrame
    fact_lap: pd.DataFrame
    fact_session_results: pd.DataFrame
    fact_race_control: pd.DataFrame
    fact_weather_minute: pd.DataFrame


def _safe_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def build_staging_bundle(data: SessionExtract, run_id: str) -> StagingBundle:
    laps = data.laps.copy()
    results = data.results.copy()
    weather = data.weather.copy()

    laps_df = pd.DataFrame(
        {
            "run_id": run_id,
            "race_id": data.race_id,
            "season": data.season,
            "round": data.round_number,
            "session_type": data.session_type,
            "driver_code": laps.get("Driver", pd.Series(dtype="object")).astype(str),
            "driver_number": laps.get("DriverNumber", pd.Series(dtype="object")).astype(str),
            "lap_number": laps.get("LapNumber", pd.Series(dtype="float")).map(_safe_int),
            "position": laps.get("Position", pd.Series(dtype="float")).map(_safe_int),
            "lap_time_ms": laps.get("LapTime", pd.Series(dtype="object")).map(timedelta_to_ms),
            "stint": laps.get("Stint", pd.Series(dtype="float")).map(_safe_int),
            "compound": laps.get("Compound", pd.Series(dtype="object")).astype(str),
            "tyre_life_laps": laps.get("TyreLife", pd.Series(dtype="float")).map(_safe_int),
            "fresh_tyre": laps.get("FreshTyre", pd.Series(dtype="bool")),
            "is_accurate": laps.get("IsAccurate", pd.Series(dtype="bool")),
            "is_pit_in_lap": laps.get("PitInTime", pd.Series(dtype="object")).notna(),
            "is_pit_out_lap": laps.get("PitOutTime", pd.Series(dtype="object")).notna(),
            "pit_in_time_ms": laps.get("PitInTime", pd.Series(dtype="object")).map(timedelta_to_ms),
            "pit_out_time_ms": laps.get("PitOutTime", pd.Series(dtype="object")).map(
                timedelta_to_ms
            ),
            "track_status_flags": laps.get("TrackStatus", pd.Series(dtype="object")).astype(str),
            "sector1_ms": laps.get("Sector1Time", pd.Series(dtype="object")).map(timedelta_to_ms),
            "sector2_ms": laps.get("Sector2Time", pd.Series(dtype="object")).map(timedelta_to_ms),
            "sector3_ms": laps.get("Sector3Time", pd.Series(dtype="object")).map(timedelta_to_ms),
        }
    )
    laps_df = laps_df[laps_df["lap_number"].notna()].copy()
    laps_df["driver_code"] = laps_df["driver_code"].replace({"nan": None, "None": None})
    laps_df["driver_number"] = laps_df["driver_number"].replace({"nan": None, "None": None})
    laps_df["compound"] = laps_df["compound"].replace({"nan": None, "None": None})
    laps_df["track_status_flags"] = laps_df["track_status_flags"].replace(
        {"nan": None, "None": None}
    )

    results_df = pd.DataFrame(
        {
            "run_id": run_id,
            "race_id": data.race_id,
            "season": data.season,
            "round": data.round_number,
            "session_type": data.session_type,
            "driver_code": results.get("Abbreviation", pd.Series(dtype="object")).astype(str),
            "driver_number": results.get("DriverNumber", pd.Series(dtype="object")).astype(str),
            "first_name": results.get("FirstName", pd.Series(dtype="object")).astype(str),
            "last_name": results.get("LastName", pd.Series(dtype="object")).astype(str),
            "full_name": results.get("FullName", pd.Series(dtype="object")).astype(str),
            "team_name": results.get("TeamName", pd.Series(dtype="object")).astype(str),
            "team_color": results.get("TeamColor", pd.Series(dtype="object")).astype(str),
            "grid_position": results.get("GridPosition", pd.Series(dtype="float")).map(_safe_int),
            "finish_position": results.get("Position", pd.Series(dtype="float")).map(_safe_int),
            "classified_position": results.get(
                "ClassifiedPosition", pd.Series(dtype="object")
            ).astype(str),
            "status": results.get("Status", pd.Series(dtype="object")).astype(str),
            "points": results.get("Points", pd.Series(dtype="float")).map(_safe_float),
            "race_time_ms": results.get("Time", pd.Series(dtype="object")).map(timedelta_to_ms),
        }
    )
    for col in [
        "driver_code",
        "driver_number",
        "first_name",
        "last_name",
        "full_name",
        "team_name",
        "team_color",
        "classified_position",
        "status",
    ]:
        results_df[col] = results_df[col].replace({"nan": None, "None": None})

    weather_time = weather.get("Time", pd.Series(dtype="object"))
    weather_ts = pd.to_datetime(weather_time, utc=True, errors="coerce")
    if weather_ts.isna().all():
        weather_td = pd.to_timedelta(weather_time, errors="coerce")
        race_anchor = pd.to_datetime(data.race_datetime_utc, utc=True, errors="coerce")
        if pd.notna(race_anchor):
            weather_ts = race_anchor + weather_td

    weather_df = pd.DataFrame(
        {
            "run_id": run_id,
            "race_id": data.race_id,
            "timestamp_utc": weather_ts,
            "air_temp_c": weather.get("AirTemp", pd.Series(dtype="float")).map(_safe_float),
            "track_temp_c": weather.get("TrackTemp", pd.Series(dtype="float")).map(_safe_float),
            "humidity_pct": weather.get("Humidity", pd.Series(dtype="float")).map(_safe_float),
            "pressure_mbar": weather.get("Pressure", pd.Series(dtype="float")).map(_safe_float),
            "rainfall": weather.get("Rainfall", pd.Series(dtype="bool")),
            "wind_dir_deg": weather.get("WindDirection", pd.Series(dtype="float")).map(_safe_float),
            "wind_speed_ms": weather.get("WindSpeed", pd.Series(dtype="float")).map(_safe_float),
        }
    )
    weather_df = weather_df[weather_df["timestamp_utc"].notna()].copy()

    return StagingBundle(laps=laps_df, results=results_df, weather=weather_df)


def build_curated_bundle(
    race_id: str,
    season: int,
    round_number: int,
    event_name: str,
    circuit: str | None,
    country: str | None,
    race_date_utc: object,
    staging: StagingBundle,
) -> CuratedBundle:
    laps = staging.laps.copy()
    results = staging.results.copy()
    weather = staging.weather.copy()

    dim_race = pd.DataFrame(
        [
            {
                "race_id": race_id,
                "season": season,
                "round": round_number,
                "event_name": event_name,
                "circuit": circuit,
                "country": country,
                "race_date_utc": pd.to_datetime(race_date_utc, utc=True, errors="coerce"),
            }
        ]
    )

    result_driver = results[
        ["driver_code", "driver_number", "first_name", "last_name", "full_name"]
    ].drop_duplicates()
    lap_driver = laps[["driver_code", "driver_number"]].drop_duplicates()
    driver_base = result_driver.merge(
        lap_driver, on="driver_code", how="outer", suffixes=("", "_lap")
    )
    driver_base["driver_number"] = driver_base["driver_number"].fillna(
        driver_base["driver_number_lap"]
    )
    driver_base = driver_base.drop(columns=["driver_number_lap"])

    driver_base = driver_base[driver_base["driver_code"].notna()].copy()
    # Ensure one stable driver row per 3-letter driver code across all seasons.
    # FastF1 metadata can vary by race (e.g., missing first/last name), so we pick
    # the most complete row for each code and derive ID from code only.
    for col in ["driver_number", "first_name", "last_name", "full_name"]:
        driver_base[f"has_{col}"] = driver_base[col].notna().astype(int)
    driver_base["completeness"] = driver_base[
        ["has_driver_number", "has_first_name", "has_last_name", "has_full_name"]
    ].sum(axis=1)
    driver_base = driver_base.sort_values(
        ["driver_code", "completeness"],
        ascending=[True, False],
    )
    driver_base = driver_base.drop_duplicates(subset=["driver_code"], keep="first")
    driver_base["driver_id"] = driver_base["driver_code"].map(lambda code: stable_id("drv", [code]))
    dim_driver = driver_base[
        ["driver_id", "driver_code", "driver_number", "first_name", "last_name", "full_name"]
    ]

    team_base = results[["team_name", "team_color"]].drop_duplicates()
    team_base = team_base[team_base["team_name"].notna()].copy()
    team_base["team_id"] = team_base["team_name"].map(lambda t: stable_id("team", [t]))
    dim_team = team_base[["team_id", "team_name", "team_color"]].drop_duplicates(subset=["team_id"])

    mapping_driver = dim_driver[["driver_code", "driver_id"]]
    mapping_team = dim_team[["team_name", "team_id"]]

    fact_lap = laps.merge(mapping_driver, on="driver_code", how="left")
    fact_lap["race_id"] = race_id
    fact_lap = fact_lap[
        [
            "race_id",
            "driver_id",
            "lap_number",
            "position",
            "lap_time_ms",
            "stint",
            "compound",
            "tyre_life_laps",
            "fresh_tyre",
            "is_accurate",
            "is_pit_in_lap",
            "is_pit_out_lap",
            "pit_in_time_ms",
            "pit_out_time_ms",
            "track_status_flags",
            "sector1_ms",
            "sector2_ms",
            "sector3_ms",
        ]
    ].dropna(subset=["driver_id", "lap_number"])
    fact_lap["lap_number"] = fact_lap["lap_number"].astype(int)
    fact_lap = fact_lap.drop_duplicates(subset=["race_id", "driver_id", "lap_number"])

    fact_results = results.merge(mapping_driver, on="driver_code", how="left").merge(
        mapping_team, on="team_name", how="left"
    )

    winner_time = None
    winner_rows = fact_results[fact_results["finish_position"] == 1]
    if not winner_rows.empty:
        winner_time = winner_rows.iloc[0]["race_time_ms"]

    def _gap_to_winner(value: object) -> int | None:
        if winner_time is None or pd.isna(winner_time) or value is None or pd.isna(value):
            return None
        return int(value - winner_time)

    fact_results["gap_to_winner_ms"] = fact_results["race_time_ms"].map(_gap_to_winner)

    fact_session_results = fact_results[
        [
            "race_id",
            "driver_id",
            "team_id",
            "grid_position",
            "finish_position",
            "classified_position",
            "status",
            "points",
            "race_time_ms",
            "gap_to_winner_ms",
        ]
    ].dropna(subset=["driver_id"])
    fact_session_results = fact_session_results.drop_duplicates(subset=["race_id", "driver_id"])

    dts = fact_results[["driver_id", "team_id"]].dropna().drop_duplicates()
    dts["season"] = season
    dim_driver_team_season = dts[["season", "driver_id", "team_id"]]

    race_control = fact_lap[["race_id", "lap_number", "track_status_flags"]].copy()
    flag_df = race_control["track_status_flags"].apply(derive_race_control_flags).apply(pd.Series)
    race_control = pd.concat([race_control[["race_id", "lap_number"]], flag_df], axis=1)
    fact_race_control = (
        race_control.groupby(["race_id", "lap_number"], as_index=False)
        .agg(
            {
                "is_sc": "max",
                "is_vsc": "max",
                "is_red_flag": "max",
                "is_yellow_flag": "max",
            }
        )
        .sort_values(["race_id", "lap_number"])
    )

    weather_min = weather.copy()
    weather_min["timestamp_utc"] = pd.to_datetime(weather_min["timestamp_utc"], utc=True).dt.floor(
        "min"
    )
    fact_weather_minute = (
        weather_min.groupby(["race_id", "timestamp_utc"], as_index=False)
        .agg(
            {
                "air_temp_c": "mean",
                "track_temp_c": "mean",
                "humidity_pct": "mean",
                "pressure_mbar": "mean",
                "rainfall": "max",
                "wind_dir_deg": "mean",
                "wind_speed_ms": "mean",
            }
        )
        .sort_values(["race_id", "timestamp_utc"])
    )

    return CuratedBundle(
        dim_race=dim_race,
        dim_driver=dim_driver,
        dim_team=dim_team,
        dim_driver_team_season=dim_driver_team_season,
        fact_lap=fact_lap,
        fact_session_results=fact_session_results,
        fact_race_control=fact_race_control,
        fact_weather_minute=fact_weather_minute,
    )
