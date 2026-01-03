from __future__ import annotations

import pandas as pd

from pipeline.utils import derive_race_control_flags, make_race_id, timedelta_to_ms


def test_make_race_id() -> None:
    assert make_race_id(2024, 1, "R") == "2024_01_R"


def test_timedelta_to_ms() -> None:
    assert timedelta_to_ms(pd.Timedelta(seconds=92.345)) == 92345
    assert timedelta_to_ms(None) is None


def test_derive_race_control_flags() -> None:
    flags = derive_race_control_flags("146")
    assert flags["is_sc"] is True
    assert flags["is_vsc"] is True
    assert flags["is_red_flag"] is False
    assert flags["is_yellow_flag"] is False
