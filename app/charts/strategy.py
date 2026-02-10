from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ._shared import (
    _CHART_LAYOUT,
    _GRID,
    _H_LEGEND,
    _ZEROLINE,
    COMPOUND_COLORS,
    _clean_race_laps,
    _driver_label,
)


# ---------------------------------------------------------------------------
# 3) Stint / Tyre Strategy Chart
# ---------------------------------------------------------------------------
def build_stint_chart(
    stints_df: pd.DataFrame,
    results_df: pd.DataFrame | None = None,
) -> go.Figure:
    figure = go.Figure()

    if stints_df.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    stints_df = stints_df.copy()
    stints_df["driver_label"] = stints_df.apply(_driver_label, axis=1)

    if results_df is not None and not results_df.empty:
        finish_order = results_df.sort_values("finish_position", na_position="last")[
            "driver_id"
        ].tolist()
        order_map = {did: i for i, did in enumerate(finish_order)}
        stints_df["_sort"] = stints_df["driver_id"].map(order_map).fillna(999)
        stints_df = stints_df.sort_values(["_sort", "stint"], ascending=[False, True])

        ordered_labels = []
        for did in reversed(finish_order):
            match = stints_df[stints_df["driver_id"] == did]
            if not match.empty:
                lbl = match.iloc[0]["driver_label"]
                if lbl not in ordered_labels:
                    ordered_labels.append(lbl)
    else:
        ordered_labels = None

    shown_compounds: set[str] = set()

    for _, row in stints_df.iterrows():
        compound = str(row.get("compound") or "UNKNOWN").upper()
        color = COMPOUND_COLORS.get(compound, "#94A3B8")
        start_lap = int(row["start_lap"])
        stint_laps = int(row["stint_laps"])

        figure.add_trace(
            go.Bar(
                x=[stint_laps],
                y=[row["driver_label"]],
                base=[start_lap],
                orientation="h",
                marker={
                    "color": color,
                    "line": {"width": 0.5, "color": "rgba(0,0,0,0.3)"},
                },
                name=compound,
                showlegend=compound not in shown_compounds,
                hovertemplate=(
                    f"<b>{row['driver_label']}</b><br>"
                    f"{compound}<br>"
                    f"Laps {start_lap}\u2013{int(row['end_lap'])} "
                    f"({stint_laps} laps)<extra></extra>"
                ),
            )
        )
        shown_compounds.add(compound)

        pit_lap = row.get("pit_lap")
        if pd.notna(pit_lap):
            pit_x = start_lap + stint_laps
            figure.add_trace(
                go.Scatter(
                    x=[pit_x],
                    y=[row["driver_label"]],
                    mode="markers",
                    marker={
                        "symbol": "diamond",
                        "size": 8,
                        "color": "#F97316",
                    },
                    showlegend=False,
                    hovertemplate=(
                        f"{row['driver_label']} pit on " f"lap {int(pit_lap)}<extra></extra>"
                    ),
                )
            )

    yaxis_cfg: dict = {
        "gridcolor": _GRID,
        "zerolinecolor": _ZEROLINE,
        "automargin": True,
    }
    if ordered_labels is not None:
        yaxis_cfg["categoryorder"] = "array"
        yaxis_cfg["categoryarray"] = ordered_labels

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap",
        xaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "dtick": 10,  # Show grid lines every 10 laps
            "showgrid": True,
            "gridwidth": 1,
        },
        barmode="overlay",
        legend=_H_LEGEND,
        height=max(len(stints_df["driver_label"].unique()) * 36 + 100, 450),
        yaxis=yaxis_cfg,
    )

    return figure


# ---------------------------------------------------------------------------
# 8) Tyre Degradation — lap time vs tyre life
# ---------------------------------------------------------------------------
def build_tyre_degradation_chart(
    lap_times_df: pd.DataFrame,
    results_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    highlight_top_n: int = 10,
) -> go.Figure:
    """Scatter of lap time vs tyre age, grouped by compound with trend lines."""
    figure = go.Figure()

    clean = _clean_race_laps(lap_times_df, race_control_df)
    if clean.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    # Only top-N finishers to reduce noise
    if not results_df.empty:
        focus_ids = set(
            results_df.sort_values("finish_position", na_position="last")
            .head(highlight_top_n)["driver_id"]
            .dropna()
            .tolist()
        )
        clean = clean[clean["driver_id"].isin(focus_ids)]

    clean = clean[clean["tyre_life_laps"].notna() & (clean["tyre_life_laps"] > 0)]
    clean["lap_sec"] = clean["lap_time_ms"].astype(float) / 1000.0

    if clean.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    # Y-axis range
    p02 = clean["lap_sec"].quantile(0.02)
    p98 = clean["lap_sec"].quantile(0.98)
    y_pad = (p98 - p02) * 0.15
    y_min = max(p02 - y_pad, 0)
    y_max = p98 + y_pad
    max_life = int(clean["tyre_life_laps"].max())

    for compound, group in clean.groupby(clean["compound"].fillna("UNKNOWN").str.upper()):
        color = COMPOUND_COLORS.get(compound, "#94A3B8")

        figure.add_trace(
            go.Scatter(
                x=group["tyre_life_laps"],
                y=group["lap_sec"],
                mode="markers",
                marker={"size": 5, "color": color, "opacity": 0.45},
                name=compound,
                hovertemplate=(
                    f"<b>{compound}</b><br>"
                    "Tyre age: %{x} laps<br>"
                    "Lap time: %{y:.3f}s<extra></extra>"
                ),
            )
        )

        # Trend line (median per tyre-life lap, smoothed)
        if len(group) >= 5:
            trend = group.groupby("tyre_life_laps")["lap_sec"].median().sort_index()
            if len(trend) >= 3:
                window = max(2, len(trend) // 8)
                smoothed = trend.rolling(window, center=True, min_periods=1).median()
                figure.add_trace(
                    go.Scatter(
                        x=smoothed.index,
                        y=smoothed.values,
                        mode="lines",
                        line={"width": 3, "color": color},
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Tyre Age (laps)",
        yaxis_title="Lap Time (seconds)",
        xaxis={
            "range": [0, max_life + 1],
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
        },
        yaxis={
            "range": [y_min, y_max],
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
        },
        legend=_H_LEGEND,
        height=480,
    )

    return figure
