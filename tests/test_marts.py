from __future__ import annotations

import pandas as pd

from pipeline.marts import build_gap_timeline, build_position_chart, build_stint_summary


def test_build_gap_timeline() -> None:
    fact_lap = pd.DataFrame(
        [
            {"race_id": "2024_01_R", "driver_id": "A", "lap_number": 1, "lap_time_ms": 90000},
            {"race_id": "2024_01_R", "driver_id": "B", "lap_number": 1, "lap_time_ms": 91000},
            {"race_id": "2024_01_R", "driver_id": "A", "lap_number": 2, "lap_time_ms": 90500},
            {"race_id": "2024_01_R", "driver_id": "B", "lap_number": 2, "lap_time_ms": 91500},
        ]
    )

    out = build_gap_timeline(fact_lap)
    assert len(out) == 2
    assert out.iloc[0]["gap_p2_to_leader_ms"] == 1000


def test_build_position_chart() -> None:
    fact_lap = pd.DataFrame(
        [
            {"race_id": "2024_01_R", "driver_id": "A", "lap_number": 1, "position": 1},
            {"race_id": "2024_01_R", "driver_id": "B", "lap_number": 1, "position": 2},
        ]
    )
    fact_results = pd.DataFrame(
        [
            {"race_id": "2024_01_R", "driver_id": "A", "team_id": "T1"},
            {"race_id": "2024_01_R", "driver_id": "B", "team_id": "T2"},
        ]
    )

    out = build_position_chart(fact_lap, fact_results)
    assert sorted(out["team_id"].tolist()) == ["T1", "T2"]


def test_build_stint_summary() -> None:
    fact_lap = pd.DataFrame(
        [
            {
                "race_id": "2024_01_R",
                "driver_id": "A",
                "stint": 1,
                "lap_number": 1,
                "lap_time_ms": 90000,
                "compound": "SOFT",
                "is_pit_in_lap": False,
            },
            {
                "race_id": "2024_01_R",
                "driver_id": "A",
                "stint": 1,
                "lap_number": 2,
                "lap_time_ms": 91000,
                "compound": "SOFT",
                "is_pit_in_lap": True,
            },
        ]
    )

    out = build_stint_summary(fact_lap)
    assert len(out) == 1
    assert int(out.iloc[0]["stint_laps"]) == 2
    assert int(out.iloc[0]["pit_lap"]) == 2
