from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ._shared import (
    _CHART_LAYOUT,
    _GRID,
    _H_LEGEND,
    _ZEROLINE,
    _add_sc_vsc_shading,
    _clean_race_laps,
    _driver_short,
    _focus_driver_ids,
    _format_sector_ms,
    _hex_to_rgba,
    _normalize_team_color,
    format_lap_time_ms,
)


# ---------------------------------------------------------------------------
# 3) Race Pace — lap time scatter
# ---------------------------------------------------------------------------
def build_race_pace_chart(
    lap_times_df: pd.DataFrame,
    results_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    highlight_top_n: int = 5,
    highlight_driver_ids: set[str] | None = None,
    show_sc_vsc: bool = True,
) -> go.Figure:
    """Rolling-median pace lines with faded scatter dots behind."""
    figure = go.Figure()

    if lap_times_df.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    focus_ids = _focus_driver_ids(results_df, highlight_top_n, highlight_driver_ids)

    clean = _clean_race_laps(lap_times_df, race_control_df)
    if clean.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    clean["lap_sec"] = clean["lap_time_ms"].astype(float) / 1000.0

    # Y-axis range from focus-driver data only
    focus_data = clean[clean["driver_id"].isin(focus_ids)] if focus_ids else clean
    ref = focus_data if not focus_data.empty else clean
    p02 = ref["lap_sec"].quantile(0.02)
    p98 = ref["lap_sec"].quantile(0.98)
    y_pad = (p98 - p02) * 0.15
    y_min = max(p02 - y_pad, 0)
    y_max = p98 + y_pad

    max_lap = int(clean["lap_number"].max())

    # Pass 1: faded scatter dots (rendered first → behind the lines)
    for driver_id, group in clean.groupby("driver_id", sort=False):
        if driver_id not in focus_ids:
            continue
        first_row = group.iloc[0]
        team_color = _normalize_team_color(first_row.get("team_color"))

        figure.add_trace(
            go.Scatter(
                x=group["lap_number"],
                y=group["lap_sec"],
                mode="markers",
                marker={"size": 4, "color": team_color, "opacity": 0.3},
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Pass 2: rolling-median trend lines (primary visual, drawn on top)
    for driver_id, group in clean.groupby("driver_id", sort=False):
        if driver_id not in focus_ids:
            continue
        first_row = group.iloc[0]
        label = _driver_short(first_row)
        team_color = _normalize_team_color(first_row.get("team_color"))

        sorted_g = group.sort_values("lap_number")

        if len(sorted_g) >= 3:
            window = max(3, len(sorted_g) // 12)
            trend = sorted_g["lap_sec"].rolling(window, center=True, min_periods=1).median()

            hover_text = [
                f"<b>{label}</b><br>Lap {int(r.lap_number)}<br>"
                f"{format_lap_time_ms(r.lap_time_ms)}<br>"
                f"{str(r.compound or 'Unknown').upper()}"
                for r in sorted_g.itertuples()
            ]

            figure.add_trace(
                go.Scatter(
                    x=sorted_g["lap_number"],
                    y=trend,
                    mode="lines",
                    line={"width": 2.5, "color": team_color},
                    name=label,
                    text=hover_text,
                    hovertemplate="%{text}<extra></extra>",
                )
            )
        else:
            figure.add_trace(
                go.Scatter(
                    x=sorted_g["lap_number"],
                    y=sorted_g["lap_sec"],
                    mode="lines+markers",
                    marker={"size": 5, "color": team_color},
                    line={"width": 2, "color": team_color},
                    name=label,
                )
            )

    if show_sc_vsc:
        _add_sc_vsc_shading(figure, race_control_df)

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap",
        yaxis_title="Lap Time (seconds)",
        xaxis={
            "range": [1, max_lap + 1],
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
        },
        yaxis={
            "range": [y_min, y_max],
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "ticksuffix": "s",  # Show 's' suffix for seconds
            "dtick": 2,  # 2-second intervals
        },
        legend=_H_LEGEND,
        height=500,
    )

    return figure


# ---------------------------------------------------------------------------
# 4) Sector Times Heatmap
# ---------------------------------------------------------------------------
def build_sector_heatmap(
    lap_times_df: pd.DataFrame,
    results_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
) -> go.Figure:
    """Heatmap of median sector times.  Color = gap to best in each sector."""
    figure = go.Figure()

    clean = _clean_race_laps(lap_times_df, race_control_df)
    clean = clean.dropna(subset=["sector1_ms", "sector2_ms", "sector3_ms"])

    if clean.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    sectors = (
        clean.groupby("driver_id")
        .agg(
            s1=("sector1_ms", "median"),
            s2=("sector2_ms", "median"),
            s3=("sector3_ms", "median"),
        )
        .reset_index()
    )

    # Merge driver names and sort by finish position
    if not results_df.empty:
        name_cols = results_df[["driver_id", "full_name", "driver_code", "finish_position"]].copy()
        sectors = sectors.merge(name_cols, on="driver_id", how="left")
        sectors = sectors.sort_values("finish_position", na_position="last")

    sectors["label"] = sectors.apply(
        lambda r: (
            str(r["full_name"]) if pd.notna(r.get("full_name")) else str(r.get("driver_code", "?"))
        ),
        axis=1,
    )

    best_s1 = sectors["s1"].min()
    best_s2 = sectors["s2"].min()
    best_s3 = sectors["s3"].min()

    labels = sectors["label"].tolist()
    z_vals: list[list[float]] = []
    text_vals: list[list[str]] = []

    for _, row in sectors.iterrows():
        z_vals.append(
            [
                (row["s1"] - best_s1) / 1000.0,
                (row["s2"] - best_s2) / 1000.0,
                (row["s3"] - best_s3) / 1000.0,
            ]
        )
        text_vals.append(
            [
                _format_sector_ms(row["s1"]),
                _format_sector_ms(row["s2"]),
                _format_sector_ms(row["s3"]),
            ]
        )

    col_labels = ["Sector 1", "Sector 2", "Sector 3"]

    figure.add_trace(
        go.Heatmap(
            z=z_vals,
            x=col_labels,
            y=labels,
            text=text_vals,
            texttemplate="%{text}s",
            textfont={"size": 13, "color": "#FFFFFF"},
            colorscale=[
                [0.0, "#166534"],
                [0.3, "#15803D"],
                [0.5, "#A16207"],
                [0.75, "#C2410C"],
                [1.0, "#991B1B"],
            ],
            colorbar={
                "title": {"text": "Gap to best (s)", "font": {"size": 13}},
                "tickfont": {"size": 12},
            },
            hovertemplate=(
                "<b>%{y}</b><br>%{x}<br>" "Time: %{text}s<br>" "Gap: +%{z:.3f}s<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis={"side": "top"},
        yaxis={"autorange": "reversed", "automargin": True},
        height=max(len(labels) * 28 + 120, 400),
    )

    return figure


# ---------------------------------------------------------------------------
# 5) Lap Time Distribution — box plot
# ---------------------------------------------------------------------------
def build_lap_distribution_chart(
    lap_times_df: pd.DataFrame,
    results_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    highlight_top_n: int = 10,
    highlight_driver_ids: set[str] | None = None,
) -> go.Figure:
    """Horizontal box plot of clean lap time distributions per driver."""
    figure = go.Figure()

    clean = _clean_race_laps(lap_times_df, race_control_df)
    if clean.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    clean["lap_sec"] = clean["lap_time_ms"].astype(float) / 1000.0
    focus_ids = _focus_driver_ids(results_df, highlight_top_n, highlight_driver_ids)

    # Ordered focus driver list (by finish position)
    if not results_df.empty:
        ordered = results_df.sort_values("finish_position", na_position="last")
        driver_order = [d for d in ordered["driver_id"] if d in focus_ids]
    else:
        driver_order = list(focus_ids)

    focus_data = clean[clean["driver_id"].isin(focus_ids)]
    if focus_data.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    # X-axis range from focus driver data
    p01 = focus_data["lap_sec"].quantile(0.01)
    p99 = focus_data["lap_sec"].quantile(0.99)
    x_pad = (p99 - p01) * 0.1
    x_min = max(p01 - x_pad, 0)
    x_max = p99 + x_pad

    # Add boxes in reverse order so P1 appears at top
    # Store box data for hover markers
    hover_data = []

    for driver_id in reversed(driver_order):
        group = clean[clean["driver_id"] == driver_id]
        if group.empty:
            continue
        first = group.iloc[0]
        label = _driver_short(first)
        team_color = _normalize_team_color(first.get("team_color"))

        # Calculate stats for hover
        lap_times = group["lap_sec"]
        median = float(lap_times.median())
        q1 = float(lap_times.quantile(0.25))
        q3 = float(lap_times.quantile(0.75))

        hover_data.append(
            {
                "label": label,
                "median": median,
                "q1": q1,
                "q3": q3,
                "color": team_color,
            }
        )

        figure.add_trace(
            go.Box(
                x=group["lap_sec"],
                name=label,
                orientation="h",
                marker={
                    "color": team_color,
                    "outliercolor": team_color,
                    "size": 3,
                },
                line={"color": team_color, "width": 1.5},
                fillcolor=_hex_to_rgba(team_color, 0.25),
                boxpoints=False,
                hoverinfo="skip",  # Disable default hover - we'll add custom markers
            )
        )

    # Add invisible scatter markers for clean horizontal hover tooltips
    for hd in hover_data:
        figure.add_trace(
            go.Scatter(
                x=[hd["median"]],
                y=[hd["label"]],
                mode="markers",
                marker={"size": 20, "opacity": 0},  # Invisible but hoverable
                hovertemplate=(
                    f"<b>{hd['label']}</b><br>"
                    f"Median: {hd['median']:.3f}s<br>"
                    f"Q1–Q3: {hd['q1']:.3f}–{hd['q3']:.3f}s"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap Time (seconds)",
        xaxis={
            "range": [x_min, x_max],
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
        },
        yaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "automargin": True,
        },
        showlegend=False,
        height=max(len(driver_order) * 36 + 100, 400),
        # Fix tooltip angle - show only one tooltip at a time
        hovermode="closest",
    )

    return figure
