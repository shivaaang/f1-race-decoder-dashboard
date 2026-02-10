"""Race Pace tab — Pace lines, box plot, sector heatmap."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from charts import (
    build_lap_distribution_chart,
    build_race_pace_chart,
    build_sector_heatmap,
)
from components import driver_selector


def render(
    bundle: dict[str, pd.DataFrame],
    results_df: pd.DataFrame,
    lap_times_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
    all_driver_names: list[str],
    driver_name_to_id: dict[str, str],
    show_sc_vsc: bool,
) -> None:
    st.markdown(
        '<p class="section-header first">Lap-by-Lap Pace</p>',
        unsafe_allow_html=True,
    )
    pace_cap_col, pace_ctrl_col = st.columns([5, 1.5])
    with pace_cap_col:
        st.markdown(
            '<p class="chart-caption">'
            "Each line shows a driver's smoothed pace across the race. "
            "Lower means faster. "
            "Faded dots are individual lap times. "
            "Pit stops, safety car laps, and the opening lap are removed "
            "to show true racing speed.</p>",
            unsafe_allow_html=True,
        )
    with pace_ctrl_col:
        pace_top_n, pace_ids = driver_selector(
            "pace",
            all_driver_names,
            driver_name_to_id,
            default_mode="Top 5",
        )
    fig_pace = build_race_pace_chart(
        lap_times_df=lap_times_df,
        results_df=results_df,
        race_control_df=race_control_df,
        highlight_top_n=pace_top_n,
        highlight_driver_ids=pace_ids,
        show_sc_vsc=show_sc_vsc,
    )
    st.plotly_chart(fig_pace, use_container_width=True)

    # -- Lap Time Consistency (box plot) --
    st.markdown(
        '<p class="section-header">Lap Time Consistency</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-caption">'
        "How consistent was each driver's pace? "
        "The box shows the typical range of lap times. "
        "a narrow box means very steady driving. "
        "The vertical line inside each box is the median "
        "(typical) lap time. Further left = faster.</p>",
        unsafe_allow_html=True,
    )
    fig_box = build_lap_distribution_chart(
        lap_times_df=lap_times_df,
        results_df=results_df,
        race_control_df=race_control_df,
        highlight_top_n=pace_top_n,
        highlight_driver_ids=pace_ids,
    )
    st.plotly_chart(fig_box, use_container_width=True)

    # -- Sector Performance Heatmap --
    st.markdown(
        '<p class="section-header">Sector Performance</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-caption">'
        "Every lap is split into 3 sectors. "
        "This heatmap shows each driver's typical time in each sector. "
        "Green = closest to the fastest time in that sector, "
        "red = furthest behind. "
        "Helps you see which part of the track each driver excels at.</p>",
        unsafe_allow_html=True,
    )
    fig_sectors = build_sector_heatmap(
        lap_times_df=lap_times_df,
        results_df=results_df,
        race_control_df=race_control_df,
    )
    st.plotly_chart(fig_sectors, use_container_width=True)
