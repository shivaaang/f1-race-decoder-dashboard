from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ._shared import (
    _CHART_LAYOUT,
    _GRID,
    _H_LEGEND,
    _ZEROLINE,
    _add_sc_vsc_shading,
    _driver_code_label,
    _driver_label,
    _focus_driver_ids,
    _normalize_team_color,
)


# ---------------------------------------------------------------------------
# 1) Gap Timeline
# ---------------------------------------------------------------------------
def build_gap_timeline_chart(
    gap_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    pit_markers_df: pd.DataFrame,
    show_sc_vsc: bool,
) -> go.Figure:
    figure = go.Figure()

    if gap_df.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    plot_df = gap_df.copy()
    plot_df["gap_sec"] = plot_df["gap_p2_to_leader_ms"].astype(float) / 1000.0
    leader_col = (
        "leader_full_name" if "leader_full_name" in plot_df.columns else "leader_driver_code"
    )
    p2_col = "p2_full_name" if "p2_full_name" in plot_df.columns else "p2_driver_code"
    leaders = plot_df[leader_col].fillna("Leader")
    p2_drivers = plot_df[p2_col].fillna("P2")
    custom_data = np.column_stack([leaders, p2_drivers])

    # Calculate intelligent Y-axis range
    # Cap at 30s for readability, but show up to actual max if most gaps are within range
    max_gap = float(plot_df["gap_sec"].max())
    p95_gap = float(plot_df["gap_sec"].quantile(0.95)) if len(plot_df) > 5 else max_gap
    y_max = min(max(p95_gap * 1.2, 5.0), 30.0)  # At least 5s, cap at 30s

    # Clipped values for display (keeps line visible near top)
    plot_df["gap_sec_display"] = plot_df["gap_sec"].clip(upper=y_max * 0.95)

    # Area fill
    figure.add_trace(
        go.Scatter(
            x=plot_df["lap_number"],
            y=plot_df["gap_sec_display"],
            mode="lines",
            line={"width": 0, "color": "rgba(96,165,250,0)"},
            fill="tozeroy",
            fillcolor="rgba(96,165,250,0.10)",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Main gap line
    figure.add_trace(
        go.Scatter(
            x=plot_df["lap_number"],
            y=plot_df["gap_sec_display"],
            mode="lines",
            line={"width": 2.5, "color": "#60A5FA", "shape": "spline"},
            name="Gap (Leader to P2)",
            customdata=custom_data,
            hovertemplate=(
                "<b>Lap %{x}</b><br>"
                "Leader: %{customdata[0]}<br>"
                "P2: %{customdata[1]}<br>"
                "Gap: %{y:.3f}s<extra></extra>"
            ),
        )
    )

    if show_sc_vsc:
        _add_sc_vsc_shading(figure, race_control_df)

    if not pit_markers_df.empty:
        pit_laps = pit_markers_df["lap_number"].dropna().astype(int).unique()
        pit_laps = np.sort(pit_laps)
        if len(pit_laps) > 0:
            marker_df = plot_df[plot_df["lap_number"].isin(pit_laps)].drop_duplicates("lap_number")
            if not marker_df.empty:
                figure.add_trace(
                    go.Scatter(
                        x=marker_df["lap_number"],
                        y=marker_df["gap_sec_display"],
                        mode="markers",
                        marker={"size": 7, "symbol": "x", "color": "#F97316"},
                        name="Pit Window",
                        hovertemplate="Pit activity on lap %{x}<extra></extra>",
                    )
                )

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap",
        yaxis_title="Gap (seconds)",
        xaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "dtick": 10,  # Show grid every 10 laps
        },
        yaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "range": [0, y_max],
            "ticksuffix": "s",  # Show 's' suffix
            "dtick": 5,  # 5-second intervals
        },
        height=420,
        legend=_H_LEGEND,
    )

    return figure


# ---------------------------------------------------------------------------
# 2) Position Chart
# ---------------------------------------------------------------------------
def build_position_chart(
    positions_df: pd.DataFrame,
    results_df: pd.DataFrame,
    highlight_top_n: int = 10,
    highlight_driver_ids: set[str] | None = None,
) -> go.Figure:
    """Always shows every driver.  Focused drivers are bold with team colours;
    the rest are dim background lines (legend-hidden)."""
    figure = go.Figure()

    if positions_df.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    focus_ids = _focus_driver_ids(results_df, highlight_top_n, highlight_driver_ids)
    max_lap = int(positions_df["lap_number"].max())

    for driver_id, group in positions_df.groupby("driver_id", sort=False):
        is_focus = driver_id in focus_ids

        first_row = group.iloc[0]
        # Use compact code for legend, full name for hover
        legend_label = _driver_code_label(first_row)
        hover_label = _driver_label(first_row)
        team_color = _normalize_team_color(first_row.get("team_color"))
        color = team_color if is_focus else "#4B5563"
        width = 2.8 if is_focus else 1.2
        opacity = 1.0 if is_focus else 0.22

        figure.add_trace(
            go.Scatter(
                x=group["lap_number"],
                y=group["position"],
                mode="lines",
                line={"width": width, "color": color},
                opacity=opacity,
                name=legend_label,
                showlegend=is_focus,
                hovertemplate=(f"<b>{hover_label}</b><br>" "Lap %{x} · P%{y}<extra></extra>"),
            )
        )

        if is_focus:
            start_row = group[group["lap_number"] == group["lap_number"].min()]
            end_row = group[group["lap_number"] == group["lap_number"].max()]
            markers = pd.concat([start_row, end_row])
            figure.add_trace(
                go.Scatter(
                    x=markers["lap_number"],
                    y=markers["position"],
                    mode="markers",
                    marker={
                        "size": 7,
                        "color": color,
                        "line": {"width": 1, "color": "#FFF"},
                    },
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap",
        yaxis_title="Position",
        yaxis={
            "autorange": "reversed",
            "dtick": 2,  # Show every 2 positions
            "tickprefix": "P",  # Add P prefix (P1, P2, etc.)
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
        },
        xaxis={
            "range": [0, max_lap + 1],
            "dtick": 10,  # Show grid every 10 laps
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
        },
        legend=_H_LEGEND,
        height=560,
    )

    return figure
