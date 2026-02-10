"""Driver Deep Dive tab — per-driver analysis with comparison overlays."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from charts import (
    _hex_to_rgba,
    _normalize_team_color,
    build_driver_narrative_chart,
    build_driver_sector_heatmap,
    build_gap_to_leader_chart,
    build_lap_delta_chart,
    build_sector_comparison_chart,
    format_lap_time_ms,
)
from components.metrics import metric_html


def render(
    bundle: dict[str, pd.DataFrame],
    results_df: pd.DataFrame,
    lap_times_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    pit_df: pd.DataFrame,
) -> None:
    # Build position-prefixed driver labels for this tab
    dd_labels: list[str] = []
    dd_label_to_id: dict[str, str] = {}
    if not results_df.empty:
        for _, _drow in results_df.iterrows():
            _pos = _drow.get("finish_position")
            _pos_str = f"P{int(_pos)}" if pd.notna(_pos) else "DNF"
            _name = (
                str(_drow["full_name"])
                if pd.notna(_drow.get("full_name"))
                else str(_drow.get("driver_code", "?"))
            )
            _team = str(_drow.get("team_name", "")) if pd.notna(_drow.get("team_name")) else ""
            _lbl = f"{_pos_str} \u2014 {_name} ({_team})" if _team else f"{_pos_str} \u2014 {_name}"
            dd_labels.append(_lbl)
            dd_label_to_id[_lbl] = _drow["driver_id"]

    dd_col_a, dd_col_b = st.columns(2)
    with dd_col_a:
        dd_primary_label = st.selectbox(
            "Primary driver",
            dd_labels,
            index=0,
            key="dd_primary",
        )
    with dd_col_b:
        cmp_options = [lbl for lbl in dd_labels if lbl != dd_primary_label]
        dd_compare_label = st.selectbox(
            "Compare with (optional)",
            ["None"] + cmp_options,
            index=0,
            key="dd_compare",
        )

    dd_primary_id = dd_label_to_id.get(dd_primary_label, "")
    dd_compare_id = dd_label_to_id.get(dd_compare_label) if dd_compare_label != "None" else None

    # Short names for chart descriptions
    _pri_row = results_df[results_df["driver_id"] == dd_primary_id]
    dd_pri_name = (
        str(_pri_row.iloc[0]["full_name"])
        if not _pri_row.empty and pd.notna(_pri_row.iloc[0].get("full_name"))
        else dd_primary_label
    )
    dd_cmp_name = ""
    if dd_compare_id:
        _cmp_row = results_df[results_df["driver_id"] == dd_compare_id]
        dd_cmp_name = (
            str(_cmp_row.iloc[0]["full_name"])
            if not _cmp_row.empty and pd.notna(_cmp_row.iloc[0].get("full_name"))
            else dd_compare_label
        )

    # --- Summary cards ---
    dd_row = results_df[results_df["driver_id"] == dd_primary_id]
    dd_team_color = "#60A5FA"
    if not dd_row.empty:
        dd_r = dd_row.iloc[0]
        dd_grid = int(dd_r["grid_position"]) if pd.notna(dd_r.get("grid_position")) else "\u2014"
        dd_finish = (
            int(dd_r["finish_position"]) if pd.notna(dd_r.get("finish_position")) else "\u2014"
        )
        dd_pts = int(dd_r["points"]) if pd.notna(dd_r.get("points")) else 0
        dd_status = str(dd_r.get("status", "Finished"))
        dd_team_color = _normalize_team_color(dd_r.get("team_color"))

        # Best lap
        dd_drv_laps = lap_times_df[
            (lap_times_df["driver_id"] == dd_primary_id)
            & lap_times_df["lap_time_ms"].notna()
            & (lap_times_df["lap_time_ms"] > 0)
            & (lap_times_df["lap_number"] > 1)
            & ~lap_times_df["is_pit_in_lap"].fillna(False)
            & ~lap_times_df["is_pit_out_lap"].fillna(False)
        ]
        dd_best_lap = (
            format_lap_time_ms(dd_drv_laps["lap_time_ms"].min())
            if not dd_drv_laps.empty
            else "\u2014"
        )

        # Gap to winner
        dd_gap_raw = dd_r.get("gap_to_winner_ms")
        if pd.notna(dd_gap_raw) and float(dd_gap_raw) > 0:
            dd_gap_str = f"+{float(dd_gap_raw) / 1000.0:.3f}s"
        elif dd_finish == 1:
            dd_gap_str = "Winner"
        else:
            dd_gap_str = "\u2014"

        # Pit stops
        dd_pits = pit_df[pit_df["driver_id"] == dd_primary_id]
        dd_pit_count = len(dd_pits)

        # Positions gained/lost
        if isinstance(dd_grid, int) and isinstance(dd_finish, int):
            dd_pos_delta = dd_grid - dd_finish
            if dd_pos_delta > 0:
                dd_pos_delta_str = f"+{dd_pos_delta}"
                dd_pos_variant = "movement"
            elif dd_pos_delta < 0:
                dd_pos_delta_str = str(dd_pos_delta)
                dd_pos_variant = "incident"
            else:
                dd_pos_delta_str = "0"
                dd_pos_variant = "count"
        else:
            dd_pos_delta_str = "\u2014"
            dd_pos_variant = "count"

        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.markdown(
                metric_html(
                    "Grid",
                    f"P{dd_grid}" if isinstance(dd_grid, int) else dd_grid,
                    icon="ph-bold ph-flag-banner",
                    variant="count",
                ),
                unsafe_allow_html=True,
            )
        with sc2:
            st.markdown(
                metric_html(
                    "Finish",
                    (f"P{dd_finish}" if isinstance(dd_finish, int) else dd_finish),
                    icon="ph-bold ph-flag-checkered",
                    variant="timing",
                ),
                unsafe_allow_html=True,
            )
        with sc3:
            st.markdown(
                metric_html(
                    "Pos. Gained",
                    dd_pos_delta_str,
                    icon="ph-bold ph-trend-up",
                    variant=dd_pos_variant,
                ),
                unsafe_allow_html=True,
            )
        with sc4:
            st.markdown(
                metric_html(
                    "Points",
                    str(dd_pts),
                    icon="ph-bold ph-star",
                    variant="count",
                ),
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        sc5, sc6, sc7, sc8 = st.columns(4)
        with sc5:
            st.markdown(
                metric_html(
                    "Best Lap",
                    dd_best_lap,
                    icon="ph-bold ph-timer",
                    variant="timing",
                ),
                unsafe_allow_html=True,
            )
        with sc6:
            st.markdown(
                metric_html(
                    "Gap to P1",
                    dd_gap_str,
                    icon="ph-bold ph-arrow-line-right",
                    variant="timing",
                ),
                unsafe_allow_html=True,
            )
        with sc7:
            st.markdown(
                metric_html(
                    "Pit Stops",
                    str(dd_pit_count),
                    icon="ph-bold ph-wrench",
                    variant="count",
                ),
                unsafe_allow_html=True,
            )
        with sc8:
            st.markdown(
                metric_html(
                    "Status",
                    dd_status,
                    icon="ph-bold ph-engine",
                    variant="weather",
                ),
                unsafe_allow_html=True,
            )

    # --- Comparison section (shown first when active) ---
    cmp_team_color = "#F97316"
    if dd_compare_id:
        cmp_row = results_df[results_df["driver_id"] == dd_compare_id]
        cmp_color_raw = (
            cmp_row.iloc[0]["team_color"]
            if not cmp_row.empty and pd.notna(cmp_row.iloc[0].get("team_color"))
            else None
        )
        cmp_team_color = _normalize_team_color(cmp_color_raw)

        # Styled gradient banner
        pri_rgba = _hex_to_rgba(dd_team_color, 0.35)
        cmp_rgba = _hex_to_rgba(cmp_team_color, 0.35)

        dd_pri_code = dd_pri_name
        dd_cmp_code = dd_cmp_name

        st.markdown(
            f"""
            <div style="background: linear-gradient(90deg, {pri_rgba}, {cmp_rgba});
                        border-radius: 10px; padding: 0.7rem 1.2rem;
                        margin: 1rem 0 0.5rem 0; display: flex;
                        justify-content: space-between; align-items: center;">
                <span style="font-weight:700;color:{dd_team_color};">{dd_pri_code}</span>
                <span style="color:#9CA3AF; font-size:0.85rem;">vs</span>
                <span style="font-weight:700;color:{cmp_team_color};">{dd_cmp_code}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        h2h_left, h2h_right = st.columns([7, 3])
        with h2h_left:
            st.markdown(
                '<p class="chart-caption">'
                "Per-lap time delta between the two drivers. "
                '<span style="color:#22C55E;font-weight:700;">Green</span>'
                f" bars = {dd_pri_name} faster, "
                '<span style="color:#EF4444;font-weight:700;">Red</span>'
                f" bars = {dd_cmp_name} faster. "
                "Pit stops, safety car laps, and the opening lap are "
                "excluded &mdash; diamond markers show pit laps, "
                "shaded zones show SC/VSC periods.</p>",
                unsafe_allow_html=True,
            )
            fig_delta = build_lap_delta_chart(
                lap_times_df=lap_times_df,
                race_control_df=race_control_df,
                driver_a_id=dd_primary_id,
                driver_b_id=dd_compare_id,
                labels=(dd_pri_code, dd_cmp_code),
                colors=(dd_team_color, cmp_team_color),
            )
            st.plotly_chart(fig_delta, use_container_width=True)

        with h2h_right:
            st.markdown(
                '<p class="chart-caption">'
                "Median sector times head-to-head. Shows where each "
                "driver gained or lost time on the track.</p>",
                unsafe_allow_html=True,
            )
            fig_sec_cmp = build_sector_comparison_chart(
                lap_times_df=lap_times_df,
                race_control_df=race_control_df,
                driver_a_id=dd_primary_id,
                driver_b_id=dd_compare_id,
                labels=(dd_pri_code, dd_cmp_code),
                colors=(dd_team_color, cmp_team_color),
            )
            st.plotly_chart(fig_sec_cmp, use_container_width=True)

    # --- Race Narrative ---
    st.markdown(
        '<p class="section-header">Race Narrative</p>',
        unsafe_allow_html=True,
    )
    if dd_compare_id:
        st.markdown(
            '<p class="chart-caption">'
            "Lap-by-lap pace colored by tyre compound. "
            f"The lighter overlay line shows <b>{dd_cmp_name}</b>'s "
            "pace for comparison. "
            f"Dashed orange lines mark <b>{dd_pri_name}</b>'s "
            "pit stops. Hover on the overlay to see details.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p class="chart-caption">'
            "Lap-by-lap pace colored by tyre compound. "
            "Dashed orange lines mark pit stops. "
            "Look for how pace changes after each stop and "
            "during safety car periods.</p>",
            unsafe_allow_html=True,
        )
    fig_narrative = build_driver_narrative_chart(
        lap_times_df=lap_times_df,
        pit_markers_df=pit_df,
        race_control_df=race_control_df,
        driver_id=dd_primary_id,
        compare_driver_id=dd_compare_id,
    )
    st.plotly_chart(fig_narrative, use_container_width=True)

    # --- Gap to Leader ---
    st.markdown(
        '<p class="section-header">Gap to Leader</p>',
        unsafe_allow_html=True,
    )
    if dd_compare_id:
        st.markdown(
            '<p class="chart-caption">'
            "Time gap to the race leader throughout the race "
            f"for both <b>{dd_pri_name}</b> and "
            f"<b>{dd_cmp_name}</b>. "
            "Lines at zero mean that driver IS the leader. "
            "Where the lines cross, one driver overtook the "
            "other on track.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p class="chart-caption">'
            "Time gap to the race leader throughout the race. "
            "The line sits at zero when this driver IS the leader. "
            "When behind, it rises to show how many seconds back "
            "they are. Spikes typically correspond to pit stop "
            "windows.</p>",
            unsafe_allow_html=True,
        )

    dd_team_color_safe = dd_team_color if not dd_row.empty else "#60A5FA"
    fig_gap_leader = build_gap_to_leader_chart(
        lap_times_df=lap_times_df,
        race_control_df=race_control_df,
        driver_id=dd_primary_id,
        team_color=dd_team_color_safe,
        compare_driver_id=dd_compare_id,
        compare_team_color=(cmp_team_color if dd_compare_id else "#F97316"),
    )
    st.plotly_chart(fig_gap_leader, use_container_width=True)

    # --- Sector Heatmap ---
    st.markdown(
        '<p class="section-header">Sector Breakdown (per lap)</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-caption">'
        "Each cell shows a sector time for a specific lap. "
        "Green = close to personal best, red = further away. "
        "Pit laps are excluded (distorted times). "
        "SC/VSC and pit-adjacent laps are labelled.</p>",
        unsafe_allow_html=True,
    )
    fig_drv_sectors = build_driver_sector_heatmap(
        lap_times_df=lap_times_df,
        driver_id=dd_primary_id,
        race_control_df=race_control_df,
    )
    st.plotly_chart(fig_drv_sectors, use_container_width=True)
