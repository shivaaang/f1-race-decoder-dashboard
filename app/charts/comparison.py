from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ._shared import (
    _CHART_LAYOUT,
    _GRID,
    _H_LEGEND,
    _ZEROLINE,
    COMPOUND_COLORS,
    _add_sc_vsc_shading,
    _clean_race_laps,
    _format_sector_ms,
    _hex_to_rgba,
    _normalize_team_color,
    format_lap_time_ms,
)


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
