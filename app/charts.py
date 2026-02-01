from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go

COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFC300",
    "HARD": "#F0F0F0",
    "INTERMEDIATE": "#39D353",
    "WET": "#4A90D9",
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
                hovertemplate=(f"<b>{hover_label}</b><br>" "Lap %{x} — P%{y}<extra></extra>"),
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
# 4) Race Pace — lap time scatter
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
# 5) Grid vs Finish — dumbbell chart
# ---------------------------------------------------------------------------
def build_grid_finish_chart(
    results_df: pd.DataFrame,
) -> go.Figure:
    figure = go.Figure()

    if results_df.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    df = results_df.copy()
    df = df.dropna(subset=["grid_position", "finish_position"])
    df["grid_position"] = df["grid_position"].astype(int)
    df["finish_position"] = df["finish_position"].astype(int)
    df = df.sort_values("finish_position", ascending=False)  # P1 at top

    df["label"] = df.apply(_driver_short, axis=1)
    df["gained"] = df["grid_position"] - df["finish_position"]

    shown_legend = {"gained": False, "lost": False, "same": False}

    for _, row in df.iterrows():
        gained = int(row["gained"])
        if gained > 0:
            color = "#22C55E"
            cat = "gained"
            legend_name = "Gained positions"
        elif gained < 0:
            color = "#EF4444"
            cat = "lost"
            legend_name = "Lost positions"
        else:
            color = "#6B7280"
            cat = "same"
            legend_name = "Same position"

        show = not shown_legend[cat]
        shown_legend[cat] = True

        grid_pos = int(row["grid_position"])
        finish_pos = int(row["finish_position"])

        # Connecting line
        figure.add_trace(
            go.Scatter(
                x=[grid_pos, finish_pos],
                y=[row["label"], row["label"]],
                mode="lines",
                line={"color": color, "width": 2.5},
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Grid position (open marker)
        figure.add_trace(
            go.Scatter(
                x=[grid_pos],
                y=[row["label"]],
                mode="markers",
                marker={
                    "size": 9,
                    "color": "rgba(0,0,0,0)",
                    "line": {"width": 2, "color": color},
                    "symbol": "circle",
                },
                showlegend=False,
                hovertemplate=(f"<b>{row['label']}</b><br>" f"Grid: P{grid_pos}<extra></extra>"),
            )
        )

        # Finish position (filled marker)
        gained_str = f"+{gained}" if gained > 0 else str(gained) if gained < 0 else "0"
        figure.add_trace(
            go.Scatter(
                x=[finish_pos],
                y=[row["label"]],
                mode="markers",
                marker={"size": 10, "color": color, "symbol": "circle"},
                name=legend_name,
                showlegend=show,
                hovertemplate=(
                    f"<b>{row['label']}</b><br>"
                    f"Grid: P{grid_pos} \u2192 Finish: P{finish_pos}<br>"
                    f"Change: {gained_str}<extra></extra>"
                ),
            )
        )

    max_pos = max(df["grid_position"].max(), df["finish_position"].max())

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Position",
        xaxis={
            "range": [0.5, max_pos + 0.5],
            "dtick": 1,
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "autorange": "reversed",
        },
        yaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "automargin": True,
        },
        legend=_H_LEGEND,
        height=max(len(df) * 32 + 100, 450),
    )

    return figure


# ---------------------------------------------------------------------------
# 6) Sector Times Heatmap
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
# 7) Lap Time Distribution — box plot
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


# ---------------------------------------------------------------------------
# 9) Driver Narrative — compound-colored stint chart with comparison overlay
# ---------------------------------------------------------------------------
def build_driver_narrative_chart(
    lap_times_df: pd.DataFrame,
    pit_markers_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    driver_id: str,
    compare_driver_id: str | None = None,
) -> go.Figure:
    """Lap-by-lap story: compound-colored stints for the primary driver,
    with an optional team-color pace overlay for a comparison driver.

    The comparison driver is drawn as a single semi-transparent line in
    their team colour — clean enough to compare pace without cluttering
    the compound-strategy visual of the primary driver.
    """
    figure = go.Figure()

    all_y_vals: list[pd.Series] = []
    max_lap = 1

    # --- Comparison driver overlay (drawn first → sits behind primary) ---
    if compare_driver_id:
        cmp = lap_times_df[lap_times_df["driver_id"] == compare_driver_id].copy()
        cmp = cmp[cmp["lap_time_ms"].notna() & (cmp["lap_time_ms"] > 0)]
        if not cmp.empty:
            cmp["lap_sec"] = cmp["lap_time_ms"].astype(float) / 1000.0
            cmp = cmp.sort_values("lap_number")
            all_y_vals.append(cmp["lap_sec"])
            max_lap = max(max_lap, int(cmp["lap_number"].max()))

            cmp_code = "DRV"
            if "driver_code" in cmp.columns and pd.notna(cmp["driver_code"].iloc[0]):
                cmp_code = str(cmp["driver_code"].iloc[0]).upper()
            cmp_full = cmp_code
            if "full_name" in cmp.columns and pd.notna(cmp["full_name"].iloc[0]):
                cmp_full = str(cmp["full_name"].iloc[0])

            cmp_color = _normalize_team_color(
                cmp["team_color"].iloc[0] if "team_color" in cmp.columns else None
            )

            hover = [
                f"<b>{cmp_full} — Lap {int(row.lap_number)}</b><br>"
                f"Time: {format_lap_time_ms(row.lap_time_ms)}<br>"
                f"Compound: {str(row.compound or 'Unknown').upper()}<br>"
                f"Position: P{int(row.position) if pd.notna(row.position) else '?'}<br>"
                f"Tyre life: {int(row.tyre_life_laps) if pd.notna(row.tyre_life_laps) else '?'}"
                " laps"
                for row in cmp.itertuples()
            ]

            figure.add_trace(
                go.Scatter(
                    x=cmp["lap_number"],
                    y=cmp["lap_sec"],
                    mode="lines",
                    line={"width": 1.5, "color": cmp_color},
                    opacity=0.55,
                    name=cmp_code,
                    text=hover,
                    hovertemplate="%{text}<extra></extra>",
                )
            )

    # --- Primary driver (compound-colored stint traces, full treatment) ---
    drv = lap_times_df[lap_times_df["driver_id"] == driver_id].copy()
    drv = drv[drv["lap_time_ms"].notna() & (drv["lap_time_ms"] > 0)]

    if drv.empty and not all_y_vals:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    if not drv.empty:
        drv["lap_sec"] = drv["lap_time_ms"].astype(float) / 1000.0
        drv = drv.sort_values("lap_number")
        all_y_vals.append(drv["lap_sec"])
        max_lap = max(max_lap, int(drv["lap_number"].max()))

        # One trace per contiguous stint so the same compound used in two
        # separate stints doesn't draw a line bridging across the gap.
        drv["_compound_upper"] = drv["compound"].fillna("UNKNOWN").str.upper()
        drv["_stint_id"] = (drv["_compound_upper"] != drv["_compound_upper"].shift()).cumsum()
        shown_compounds: set[str] = set()

        stint_groups = list(drv.groupby("_stint_id", sort=True))

        for i, (_stint_id, grp) in enumerate(stint_groups):
            compound = grp["_compound_upper"].iloc[0]
            color = COMPOUND_COLORS.get(compound, "#94A3B8")

            # Line trace — bridge from previous stint's last point
            if i > 0:
                prev_grp = stint_groups[i - 1][1]
                bridge = prev_grp.iloc[[-1]]
                line_grp = pd.concat([bridge, grp])
            else:
                line_grp = grp

            figure.add_trace(
                go.Scatter(
                    x=line_grp["lap_number"],
                    y=line_grp["lap_sec"],
                    mode="lines",
                    line={"width": 2, "color": color},
                    name=compound,
                    legendgroup=compound,
                    showlegend=compound not in shown_compounds,
                    hoverinfo="skip",
                )
            )

            # Marker trace — only actual stint laps (no bridge dot)
            hover = [
                f"<b>Lap {int(row.lap_number)}</b><br>"
                f"Time: {format_lap_time_ms(row.lap_time_ms)}<br>"
                f"Compound: {compound}<br>"
                f"Position: P{int(row.position) if pd.notna(row.position) else '?'}<br>"
                f"Tyre life: {int(row.tyre_life_laps) if pd.notna(row.tyre_life_laps) else '?'}"
                " laps"
                for row in grp.itertuples()
            ]
            figure.add_trace(
                go.Scatter(
                    x=grp["lap_number"],
                    y=grp["lap_sec"],
                    mode="markers",
                    marker={"size": 5, "color": color},
                    legendgroup=compound,
                    showlegend=False,
                    text=hover,
                    hovertemplate="%{text}<extra></extra>",
                )
            )
            shown_compounds.add(compound)

    # --- Y-axis range from all plotted drivers ---
    combined = pd.concat(all_y_vals)
    p02 = combined.quantile(0.02)
    p98 = combined.quantile(0.98)
    y_pad = (p98 - p02) * 0.15
    y_min = max(p02 - y_pad, 0)
    y_max = p98 + y_pad

    # Pit stop markers — primary driver only
    drv_pits = pit_markers_df[pit_markers_df["driver_id"] == driver_id]
    for _, pit_row in drv_pits.iterrows():
        figure.add_vline(
            x=int(pit_row["lap_number"]),
            line_dash="dash",
            line_color="#F97316",
            line_width=1.5,
            annotation_text="PIT",
            annotation_position="top",
            annotation_font={"color": "#F97316", "size": 11},
        )

    _add_sc_vsc_shading(figure, race_control_df)

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap",
        yaxis_title="Lap Time",
        xaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "dtick": 10,
            "range": [1, max_lap],
        },
        yaxis={
            "range": [y_min, y_max],
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "ticksuffix": "s",
        },
        legend=_H_LEGEND,
        height=440,
    )

    return figure


# ---------------------------------------------------------------------------
# 10) Driver Sector Heatmap — per-lap sector breakdown for one driver
# ---------------------------------------------------------------------------
def build_driver_sector_heatmap(
    lap_times_df: pd.DataFrame,
    driver_id: str,
    race_control_df=None,
) -> go.Figure:
    """Per-lap sector heatmap for a single driver."""
    figure = go.Figure()

    drv = lap_times_df[lap_times_df["driver_id"] == driver_id].copy()
    drv = drv.dropna(subset=["sector1_ms", "sector2_ms", "sector3_ms"])
    drv = drv[drv["lap_time_ms"].notna() & (drv["lap_time_ms"] > 0)]

    # Exclude pit laps
    pit_in_laps = set(drv[drv["is_pit_in_lap"].fillna(False)]["lap_number"].astype(int).tolist())
    pit_out_laps = set(drv[drv["is_pit_out_lap"].fillna(False)]["lap_number"].astype(int).tolist())
    drv = drv[~drv["lap_number"].isin(pit_in_laps | pit_out_laps)]

    if drv.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    drv = drv.sort_values("lap_number")

    # SC/VSC lap sets
    sc_laps: set[int] = set()
    vsc_laps: set[int] = set()
    if race_control_df is not None and not race_control_df.empty:
        sc_laps = set(
            race_control_df[race_control_df["is_sc"].fillna(False)]["lap_number"].astype(int)
        )
        vsc_laps = set(
            race_control_df[race_control_df["is_vsc"].fillna(False)]["lap_number"].astype(int)
        )

    # Build annotated lap labels
    lap_nums = drv["lap_number"].astype(int).tolist()
    lap_num_set = set(lap_nums)
    lap_labels: list[str] = []
    for lap_num in lap_nums:
        label = f"Lap {lap_num}"
        tags: list[str] = []
        if lap_num in sc_laps:
            tags.append("SC")
        elif lap_num in vsc_laps:
            tags.append("VSC")
        # Mark laps adjacent to excluded pit laps
        if (lap_num - 1) in pit_in_laps and (lap_num - 1) not in lap_num_set:
            tags.append("after PIT")
        elif (lap_num + 1) in pit_out_laps and (lap_num + 1) not in lap_num_set:
            tags.append("before PIT")
        if tags:
            label += f"  ({', '.join(tags)})"
        lap_labels.append(label)

    z_vals: list[list[float]] = []
    text_vals: list[list[str]] = []
    sectors = ["sector1_ms", "sector2_ms", "sector3_ms"]
    best = [drv[s].min() for s in sectors]

    for _, row in drv.iterrows():
        z_vals.append([(row[s] - best[i]) / 1000.0 for i, s in enumerate(sectors)])
        text_vals.append([_format_sector_ms(row[s]) for s in sectors])

    col_labels = ["Sector 1", "Sector 2", "Sector 3"]

    figure.add_trace(
        go.Heatmap(
            z=z_vals,
            x=col_labels,
            y=lap_labels,
            text=text_vals,
            texttemplate="%{text}s",
            textfont={"size": 12, "color": "#FFFFFF"},
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
                "<b>%{y}</b><br>%{x}<br>Time: %{text}s<br>Gap: +%{z:.3f}s<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis={"side": "top"},
        yaxis={"autorange": "reversed", "automargin": True},
        height=max(len(lap_labels) * 24 + 120, 400),
    )

    return figure


# ---------------------------------------------------------------------------
# 11) Gap to Leader — cumulative gap chart
# ---------------------------------------------------------------------------
def build_gap_to_leader_chart(
    lap_times_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    driver_id: str,
    team_color: str = "#60A5FA",
    compare_driver_id: str | None = None,
    compare_team_color: str = "#F97316",
) -> go.Figure:
    """Gap between selected driver(s) and the race leader.

    0 when a driver IS the leader.  When compare_driver_id is set,
    the primary driver is drawn with a solid line and the comparison
    driver with a thinner line, both in their team colours.
    """
    figure = go.Figure()

    valid = lap_times_df[
        lap_times_df["lap_time_ms"].notna() & (lap_times_df["lap_time_ms"] > 0)
    ].copy()
    if valid.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    # Cumulative elapsed time per driver
    valid = valid.sort_values(["driver_id", "lap_number"])
    valid["cum_ms"] = valid.groupby("driver_id")["lap_time_ms"].cumsum()

    # Use the position column (from fact_lap) to identify the actual leader
    leader_df = (
        valid[valid["position"] == 1]
        .drop_duplicates("lap_number", keep="first")[["lap_number", "cum_ms", "driver_id"]]
        .rename(columns={"cum_ms": "leader_cum", "driver_id": "leader_id"})
    )

    # Build list of drivers to plot: (driver_id, raw_color, is_primary)
    drivers_to_plot = [(driver_id, team_color, True)]
    if compare_driver_id:
        drivers_to_plot.append((compare_driver_id, compare_team_color, False))

    max_lap = int(valid["lap_number"].max())
    any_plotted = False

    for did, raw_color, is_primary in drivers_to_plot:
        drv = valid[valid["driver_id"] == did][["lap_number", "cum_ms"]].rename(
            columns={"cum_ms": "drv_cum"}
        )
        if drv.empty:
            continue

        merged = drv.merge(leader_df, on="lap_number", how="inner")
        if merged.empty:
            continue

        # Gap = 0 when driver IS the leader, positive when behind
        is_leading = merged["leader_id"] == did
        merged["gap_sec"] = np.where(
            is_leading,
            0.0,
            (merged["drv_cum"] - merged["leader_cum"]) / 1000.0,
        )

        gap_series = merged[["lap_number", "gap_sec"]].rename(columns={"lap_number": "lap"})
        color = _normalize_team_color(raw_color)

        # Get driver code (legend) and full name (hover)
        drv_rows = valid[valid["driver_id"] == did]
        code = "DRV"
        full_name = "DRV"
        if "driver_code" in drv_rows.columns and not drv_rows.empty:
            dc = drv_rows["driver_code"].iloc[0]
            if pd.notna(dc):
                code = str(dc).upper()
                full_name = code
        if "full_name" in drv_rows.columns and not drv_rows.empty:
            fn = drv_rows["full_name"].iloc[0]
            if pd.notna(fn):
                full_name = str(fn)

        line_width = 2.5 if is_primary else 2.0

        # Area fill only for primary driver (avoid overlapping fills)
        if is_primary:
            figure.add_trace(
                go.Scatter(
                    x=gap_series["lap"],
                    y=gap_series["gap_sec"],
                    mode="lines",
                    line={"width": 0, "color": "rgba(0,0,0,0)"},
                    fill="tozeroy",
                    fillcolor=_hex_to_rgba(color, 0.15),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        figure.add_trace(
            go.Scatter(
                x=gap_series["lap"],
                y=gap_series["gap_sec"],
                mode="lines",
                line={"width": line_width, "color": color, "shape": "spline"},
                name=code,
                hovertemplate=(
                    f"<b>{full_name} — Lap %{{x}}</b><br>" f"Gap: +%{{y:.3f}}s<extra></extra>"
                ),
            )
        )
        any_plotted = True

    if not any_plotted:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    # Zero line (leading)
    figure.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(255,255,255,0.3)",
        line_width=1,
    )

    _add_sc_vsc_shading(figure, race_control_df)

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap",
        yaxis_title="Gap to Leader (s)",
        xaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "dtick": 10,
            "range": [1, max_lap],
        },
        yaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "rangemode": "tozero",
            "ticksuffix": "s",
        },
        legend=_H_LEGEND,
        height=400,
    )

    return figure


# ---------------------------------------------------------------------------
# 12) Lap Delta — per-lap bar chart between two drivers
# ---------------------------------------------------------------------------
def build_lap_delta_chart(
    lap_times_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    driver_a_id: str,
    driver_b_id: str,
    labels: tuple[str, str] = ("Driver A", "Driver B"),
    colors: tuple[str, str] = ("#60A5FA", "#F97316"),
) -> go.Figure:
    """Per-lap delta between two drivers.  Positive = A slower, negative = A faster."""
    figure = go.Figure()

    clean = _clean_race_laps(lap_times_df, race_control_df)
    if clean.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    a = clean[clean["driver_id"] == driver_a_id][["lap_number", "lap_time_ms"]].rename(
        columns={"lap_time_ms": "a_ms"}
    )
    b = clean[clean["driver_id"] == driver_b_id][["lap_number", "lap_time_ms"]].rename(
        columns={"lap_time_ms": "b_ms"}
    )
    merged = a.merge(b, on="lap_number").sort_values("lap_number")
    if merged.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    merged["delta_sec"] = (merged["a_ms"] - merged["b_ms"]).astype(float) / 1000.0
    bar_colors = ["#EF4444" if d > 0 else "#22C55E" for d in merged["delta_sec"]]

    figure.add_trace(
        go.Bar(
            x=merged["lap_number"],
            y=merged["delta_sec"],
            marker_color=bar_colors,
            showlegend=False,
            hovertemplate="<b>Lap %{x}</b><br>Delta: %{y:+.3f}s<extra></extra>",
        )
    )

    figure.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=1)

    # --- Context markers for excluded laps ---

    # SC/VSC shading
    _add_sc_vsc_shading(figure, race_control_df)

    # Opening lap annotation
    figure.add_vline(
        x=1,
        line_dash="dot",
        line_color="rgba(255,255,255,0.25)",
        line_width=1,
        annotation_text="Lap 1",
        annotation_position="top",
        annotation_font={"color": "rgba(255,255,255,0.5)", "size": 11},
    )

    # Pit lap markers — extract from raw data before cleaning.
    # Offset driver A above zero and driver B below so both are visible
    # when they pit on the same lap.
    both = lap_times_df[lap_times_df["driver_id"].isin([driver_a_id, driver_b_id])]
    pit_in = both[both["is_pit_in_lap"].fillna(False)]
    y_range = merged["delta_sec"].abs().max()
    pit_offset = max(y_range * 0.06, 0.02)

    for did, label, color, offset in zip(
        [driver_a_id, driver_b_id],
        labels,
        colors,
        [pit_offset, -pit_offset],
        strict=False,
    ):
        drv_pits = pit_in[pit_in["driver_id"] == did]["lap_number"].dropna().unique()
        if len(drv_pits) == 0:
            continue
        tc = _normalize_team_color(color)
        figure.add_trace(
            go.Scatter(
                x=drv_pits,
                y=[offset] * len(drv_pits),
                mode="markers",
                marker={"symbol": "diamond", "size": 9, "color": tc},
                name=f"{label} pit",
                hovertemplate=f"<b>{label}</b> pit on lap %{{x}}<extra></extra>",
            )
        )

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Lap",
        yaxis_title="Delta (s)",
        xaxis={"gridcolor": _GRID, "zerolinecolor": _ZEROLINE, "dtick": 10},
        yaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "ticksuffix": "s",
        },
        legend=_H_LEGEND,
        height=380,
    )

    return figure


# ---------------------------------------------------------------------------
# 13) Sector Comparison — grouped bar chart
# ---------------------------------------------------------------------------
def build_sector_comparison_chart(
    lap_times_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    driver_a_id: str,
    driver_b_id: str,
    labels: tuple[str, str] = ("Driver A", "Driver B"),
    colors: tuple[str, str] = ("#60A5FA", "#F97316"),
) -> go.Figure:
    """Grouped bar chart comparing median sector times for two drivers."""
    figure = go.Figure()

    clean = _clean_race_laps(lap_times_df, race_control_df)
    clean = clean.dropna(subset=["sector1_ms", "sector2_ms", "sector3_ms"])
    if clean.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    sectors_list = ["sector1_ms", "sector2_ms", "sector3_ms"]
    x_labels = ["Sector 1", "Sector 2", "Sector 3"]

    for did, label, color in zip([driver_a_id, driver_b_id], labels, colors, strict=False):
        drv = clean[clean["driver_id"] == did]
        if drv.empty:
            vals = [0, 0, 0]
            texts = ["N/A", "N/A", "N/A"]
        else:
            vals = [float(drv[s].median()) / 1000.0 for s in sectors_list]
            texts = [f"{v:.3f}s" for v in vals]

        figure.add_trace(
            go.Bar(
                x=x_labels,
                y=vals,
                name=label,
                marker_color=_normalize_team_color(color),
                text=texts,
                textposition="outside",
                textfont={"size": 13, "color": "#E8EAED"},
                hovertemplate=f"<b>{label}</b><br>%{{x}}: %{{y:.3f}}s<extra></extra>",
            )
        )

    figure.update_layout(
        **_CHART_LAYOUT,
        barmode="group",
        xaxis={"gridcolor": _GRID, "zerolinecolor": _ZEROLINE},
        yaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "ticksuffix": "s",
        },
        legend=_H_LEGEND,
        height=380,
    )

    return figure
