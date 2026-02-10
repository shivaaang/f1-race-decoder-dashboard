"""Strategy tab — Stint chart + Tyre degradation."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from charts import build_stint_chart, build_tyre_degradation_chart


def render(
    bundle: dict[str, pd.DataFrame],
    results_df: pd.DataFrame,
    lap_times_df: pd.DataFrame,
    race_control_df: pd.DataFrame,
) -> None:
    st.markdown(
        '<p class="section-header first">Tyre Strategy</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-caption">'
        "Each bar is a stint (the period between pit stops). "
        "Teams choose from three dry slick compounds: "
        '<span style="color:#FF3333;font-weight:700;">Soft</span> '
        "(fastest, wears out quickly), "
        '<span style="color:#FFC300;font-weight:700;">Medium</span> '
        "(balanced), and "
        '<span style="color:#F0F0F0;font-weight:700;">Hard</span> '
        "(slowest but lasts longest). "
        "In wet conditions, teams switch to "
        '<span style="color:#39D353;font-weight:700;">Intermediate</span> '
        "(light rain or a drying track) or "
        '<span style="color:#4A90D9;font-weight:700;">Wet</span> '
        "(heavy rain with standing water). "
        '<span style="color:#94A3B8;font-weight:700;">Gray</span> '
        "bars indicate laps where tyre data was unavailable. "
        "Diamond markers show pit stops. "
        "Drivers sorted by finishing position (winner at top).</p>",
        unsafe_allow_html=True,
    )
    fig_stint = build_stint_chart(bundle["stints"], results_df=results_df)
    st.plotly_chart(fig_stint, use_container_width=True)

    # -- Tyre Degradation --
    st.markdown(
        '<p class="section-header">Tyre Degradation</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-caption">'
        "As tyres wear out, lap times get slower. "
        "This chart shows how quickly each compound loses performance. "
        "Steeper upward trends mean faster degradation. "
        "Teams use this data to decide when to pit.</p>",
        unsafe_allow_html=True,
    )
    fig_deg = build_tyre_degradation_chart(
        lap_times_df=lap_times_df,
        results_df=results_df,
        race_control_df=race_control_df,
    )
    st.plotly_chart(fig_deg, use_container_width=True)
