from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import plotly.graph_objects as go

COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFC300",
    "HARD": "#F0F0F0",
    "INTERMEDIATE": "#39D353",
    "WET": "#4A90D9",
    "UNKNOWN": "#94A3B8",
}

_GRID = "rgba(255,255,255,0.06)"
_ZEROLINE = "rgba(255,255,255,0.08)"

# No title — HTML captions above each chart handle labelling.
_CHART_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#E8EAED", "size": 18},
    "margin": {"l": 20, "r": 20, "t": 30, "b": 40},
    "hoverlabel": {
        "bgcolor": "#1E2130",
        "font_size": 15,
        "font_color": "#F0F2F5",
        "align": "left",
    },
}

_H_LEGEND = {
    "orientation": "h",
    "yanchor": "bottom",
    "y": 1.0,
    "x": 0,
    "font": {"size": 16, "color": "#F0F2F5"},
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _contiguous_lap_ranges(laps: Iterable[int]) -> list[tuple[int, int]]:
    values = sorted(set(int(v) for v in laps))
    if not values:
        return []

    ranges: list[tuple[int, int]] = []
    start = values[0]
    prev = values[0]
    for lap in values[1:]:
        if lap == prev + 1:
            prev = lap
            continue
        ranges.append((start, prev))
        start = lap
        prev = lap
    ranges.append((start, prev))
    return ranges


def _normalize_team_color(value: object) -> str:
    if value is None or pd.isna(value):
        return "#22C55E"
    color = str(value).strip()
    if color.startswith("#") and len(color) == 7:
        return color
    if len(color) == 6:
        return f"#{color}"
    return "#22C55E"


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _driver_label(row: pd.Series) -> str:
    name = row.get("full_name")
    code = row.get("driver_code")
    team = row.get("team_name")
    label = name if pd.notna(name) and str(name).strip() else code
    if not (pd.notna(label) and str(label).strip()):
        label = row.get("driver_id", "Driver")
    if pd.notna(team) and str(team).strip():
        return f"{label} ({team})"
    return str(label)


def _driver_code_label(row: pd.Series) -> str:
    """Return compact driver label using 3-letter code for cleaner chart legends.

    Falls back to full name if code unavailable.
    """
    code = row.get("driver_code")
    if pd.notna(code) and str(code).strip():
        return str(code).upper()
    name = row.get("full_name")
    if pd.notna(name) and str(name).strip():
        return str(name)
    return str(row.get("driver_id", "DRV"))


def _driver_short(row: pd.Series) -> str:
    name = row.get("full_name")
    code = row.get("driver_code")
    if pd.notna(name) and str(name).strip():
        return str(name)
    if pd.notna(code) and str(code).strip():
        return str(code)
    return str(row.get("driver_id", "Driver"))


def format_lap_time_ms(ms: float | int) -> str:
    total_sec = float(ms) / 1000.0
    minutes = int(total_sec // 60)
    seconds = total_sec % 60
    return f"{minutes}:{seconds:06.3f}"


def _format_sector_ms(ms: float | int) -> str:
    """Format sector time in milliseconds to seconds string, e.g. '23.456'."""
    return f"{float(ms) / 1000.0:.3f}"


def _add_sc_vsc_shading(
    figure: go.Figure,
    race_control_df: pd.DataFrame,
) -> None:
    if race_control_df.empty:
        return
    sc_ranges = _contiguous_lap_ranges(race_control_df[race_control_df["is_sc"]]["lap_number"])
    vsc_ranges = _contiguous_lap_ranges(race_control_df[race_control_df["is_vsc"]]["lap_number"])
    for start, end in sc_ranges:
        figure.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(255, 193, 7, 0.12)",  # Reduced opacity for subtlety
            line_width=0,
            annotation_text="SC",
            annotation_position="top left",
            annotation_font={"color": "#FFC107", "size": 13},
        )
    for start, end in vsc_ranges:
        figure.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(74, 144, 217, 0.10)",  # Reduced opacity for subtlety
            line_width=0,
            annotation_text="VSC",
            annotation_position="bottom left",
            annotation_font={"color": "#4A90D9", "size": 13},
        )


def _clean_race_laps(
    lap_times_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
) -> pd.DataFrame:
    """Filter to clean racing laps only (no pit laps, SC/VSC, or lap 1)."""
    clean = lap_times_df.copy()
    clean = clean[clean["lap_time_ms"].notna() & (clean["lap_time_ms"] > 0)]
    clean = clean[clean["lap_number"] > 1]
    pit_mask = clean["is_pit_in_lap"].fillna(False) | clean["is_pit_out_lap"].fillna(False)
    clean = clean[~pit_mask]
    if not race_control_df.empty:
        sc_mask = race_control_df["is_sc"].fillna(False) | race_control_df["is_vsc"].fillna(False)
        sc_laps = set(race_control_df[sc_mask]["lap_number"].astype(int).tolist())
        if sc_laps:
            clean = clean[~clean["lap_number"].isin(sc_laps)]
    return clean


def _focus_driver_ids(
    results_df: pd.DataFrame,
    highlight_top_n: int,
    highlight_driver_ids: set[str] | None,
) -> set[str]:
    """Return the set of driver IDs to highlight."""
    if highlight_driver_ids:
        return highlight_driver_ids
    if not results_df.empty:
        return set(
            results_df.sort_values("finish_position", na_position="last")
            .head(highlight_top_n)["driver_id"]
            .dropna()
            .tolist()
        )
    return set()
