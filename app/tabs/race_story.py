"""Race Story tab — Position chart + Gap timeline."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from charts import build_gap_timeline_chart, build_position_chart
from components import driver_selector


@st.fragment
def render(
    bundle: dict[str, pd.DataFrame],
    all_driver_names: list[str],
    driver_name_to_id: dict[str, str],
    show_sc_vsc: bool,
) -> None:
    st.markdown(
        '<p class="section-header first">Position Chart</p>',
        unsafe_allow_html=True,
    )
    pos_cap_col, pos_ctrl_col = st.columns([5, 1.5])
    with pos_cap_col:
        st.markdown(
            '<p class="chart-caption">'
            "Where each driver ran throughout the race. "
            "P1 (the leader) is at the top. "
            "Watch for lines crossing each other "
            "to spot overtakes.</p>",
            unsafe_allow_html=True,
        )
    with pos_ctrl_col:
        pos_top_n, pos_ids = driver_selector(
            "pos", all_driver_names, driver_name_to_id, default_mode="Top 10"
        )
    fig_pos = build_position_chart(
        positions_df=bundle["positions"],
        results_df=bundle["results"],
        highlight_top_n=pos_top_n,
        highlight_driver_ids=pos_ids,
    )
    st.plotly_chart(fig_pos, use_container_width=True)

    st.markdown(
        '<p class="section-header">Leader vs Second Place Gap</p>',
        unsafe_allow_html=True,
    )
    cap_col, _ctrl_col = st.columns([4, 1])
    with cap_col:
        st.markdown(
            '<p class="chart-caption">'
            "The time gap between the race leader and the driver in second. "
            "When the line rises, the leader is pulling away. "
            "When it drops, P2 is closing in, "
            "signalling an exciting battle for the lead.</p>",
            unsafe_allow_html=True,
        )
    fig_gap = build_gap_timeline_chart(
        gap_df=bundle["gap"],
        race_control_df=bundle["race_control"],
        pit_markers_df=bundle["pit_markers"],
        show_sc_vsc=show_sc_vsc,
    )
    st.plotly_chart(fig_gap, use_container_width=True)
