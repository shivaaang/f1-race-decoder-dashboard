from __future__ import annotations

import pandas as pd


def build_gap_timeline(fact_lap: pd.DataFrame) -> pd.DataFrame:
    if fact_lap.empty:
        return pd.DataFrame(
            columns=[
                "race_id",
                "lap_number",
                "leader_driver_id",
                "p2_driver_id",
                "gap_p2_to_leader_ms",
            ]
        )

    df = fact_lap[["race_id", "driver_id", "lap_number", "lap_time_ms"]].copy()
    df = df.dropna(subset=["lap_time_ms"])
    df["lap_time_ms"] = df["lap_time_ms"].astype(int)
    df = df.sort_values(["driver_id", "lap_number"])
    df["elapsed_ms"] = df.groupby("driver_id")["lap_time_ms"].cumsum()

    rows: list[dict] = []
    for lap, group in df.groupby("lap_number"):
        g = group.sort_values("elapsed_ms")
        if len(g) < 2:
            continue
        leader = g.iloc[0]
        p2 = g.iloc[1]
        rows.append(
            {
                "race_id": leader["race_id"],
                "lap_number": int(lap),
                "leader_driver_id": leader["driver_id"],
                "p2_driver_id": p2["driver_id"],
                "gap_p2_to_leader_ms": int(p2["elapsed_ms"] - leader["elapsed_ms"]),
            }
        )

    return pd.DataFrame(rows)


def build_position_chart(
    fact_lap: pd.DataFrame, fact_session_results: pd.DataFrame
) -> pd.DataFrame:
    if fact_lap.empty:
        return pd.DataFrame(columns=["race_id", "driver_id", "lap_number", "position", "team_id"])

    team_map = fact_session_results[["driver_id", "team_id"]].drop_duplicates()
    out = fact_lap[["race_id", "driver_id", "lap_number", "position"]].merge(
        team_map, on="driver_id", how="left"
    )
    out["lap_number"] = out["lap_number"].astype(int)
    return out.drop_duplicates(subset=["race_id", "driver_id", "lap_number"])


def build_stint_summary(fact_lap: pd.DataFrame) -> pd.DataFrame:
    if fact_lap.empty:
        return pd.DataFrame(
            columns=[
                "race_id",
                "driver_id",
                "stint",
                "start_lap",
                "end_lap",
                "compound",
                "stint_laps",
                "median_lap_ms",
                "avg_lap_ms",
                "pit_lap",
            ]
        )

    df = fact_lap.copy()
    df = df[df["stint"].notna()].copy()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "race_id",
                "driver_id",
                "stint",
                "start_lap",
                "end_lap",
                "compound",
                "stint_laps",
                "median_lap_ms",
                "avg_lap_ms",
                "pit_lap",
            ]
        )

    grouped = df.groupby(["race_id", "driver_id", "stint"], as_index=False)
    out = grouped.agg(
        start_lap=("lap_number", "min"),
        end_lap=("lap_number", "max"),
        compound=("compound", "first"),
        stint_laps=("lap_number", "count"),
        median_lap_ms=("lap_time_ms", "median"),
        avg_lap_ms=("lap_time_ms", "mean"),
    )

    pit_laps = (
        df[df["is_pit_in_lap"] == True]  # noqa: E712
        .groupby(["race_id", "driver_id", "stint"], as_index=False)["lap_number"]
        .max()
        .rename(columns={"lap_number": "pit_lap"})
    )
    out = out.merge(pit_laps, on=["race_id", "driver_id", "stint"], how="left")
    out["median_lap_ms"] = out["median_lap_ms"].round().astype("Int64")
    out["avg_lap_ms"] = out["avg_lap_ms"].round().astype("Int64")
    out["stint"] = out["stint"].astype(int)
    return out
