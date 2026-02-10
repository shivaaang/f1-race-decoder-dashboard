"""Full Results tab — Grid-vs-finish dumbbell + results table."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from charts import build_grid_finish_chart


@st.fragment
def render(
    results_df: pd.DataFrame,
    race_id: str,
) -> None:
    st.markdown(
        '<p class="section-header first">Grid vs Finish</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-caption">'
        "Where each driver started (open circle) versus where they "
        "finished (filled circle). "
        '<span style="color:#22C55E;font-weight:700;">Green</span> = '
        "gained positions, "
        '<span style="color:#EF4444;font-weight:700;">Red</span> = '
        "lost positions.</p>",
        unsafe_allow_html=True,
    )
    fig_gf = build_grid_finish_chart(results_df)
    st.plotly_chart(fig_gf, use_container_width=True)

    st.markdown(
        '<p class="section-header">Race Classification</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="chart-caption">'
        "Final standings with positions gained or lost from the starting "
        "grid to the finish.</p>",
        unsafe_allow_html=True,
    )

    if not results_df.empty:
        display_df = results_df.copy()
        display_df["Grid"] = display_df["grid_position"].fillna(0).astype(int)
        display_df["Finish"] = display_df["finish_position"].fillna(0).astype(int)
        display_df["Gained/Lost"] = display_df["Grid"] - display_df["Finish"]
        display_df["Driver"] = display_df.apply(
            lambda row: (row["full_name"] if pd.notna(row["full_name"]) else row["driver_code"]),
            axis=1,
        )
        display_df["Team"] = display_df["team_name"].fillna("-")
        display_df["Status"] = display_df["status"].fillna("Finished")
        display_df["Points"] = display_df["points"].fillna(0).astype(int)

        show_df = display_df[
            [
                "Finish",
                "Driver",
                "Team",
                "Grid",
                "Gained/Lost",
                "Status",
                "Points",
            ]
        ].copy()
        show_df = show_df.rename(columns={"Finish": "Pos"})
        show_df = show_df.reset_index(drop=True)

        # Build custom HTML table with inline dark theme styles
        rows_html = ""
        for _, row in show_df.iterrows():
            gained = row["Gained/Lost"]
            if gained > 0:
                gained_style = "color: #22C55E; font-weight: 700;"
                gained_str = f"+{gained}"
            elif gained < 0:
                gained_style = "color: #EF4444; font-weight: 700;"
                gained_str = str(gained)
            else:
                gained_style = "color: #9CA3AF;"
                gained_str = "0"

            rows_html += (
                '<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">'
                '<td style="padding: 10px 16px; color: #FFFFFF; '
                f'font-weight: 700;">{row["Pos"]}</td>'
                f'<td style="padding: 10px 16px; color: #E5E7EB;">{row["Driver"]}</td>'
                f'<td style="padding: 10px 16px; color: #E5E7EB;">{row["Team"]}</td>'
                f'<td style="padding: 10px 16px; color: #E5E7EB;">{row["Grid"]}</td>'
                f'<td style="padding: 10px 16px; {gained_style}">{gained_str}</td>'
                f'<td style="padding: 10px 16px; color: #E5E7EB;">{row["Status"]}</td>'
                f'<td style="padding: 10px 16px; color: #E5E7EB;">{row["Points"]}</td>'
                "</tr>"
            )

        _ths = "padding:12px 16px;text-align:left;color:#9CA3AF;font-weight:600"
        table_html = (
            '<div style="background: #1A1D26; border-radius: 8px; overflow: hidden;">'
            '<table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">'
            "<thead>"
            f'<tr style="background: #252A3A;">'
            f'<th style="{_ths}">Pos</th>'
            f'<th style="{_ths}">Driver</th>'
            f'<th style="{_ths}">Team</th>'
            f'<th style="{_ths}">Grid</th>'
            f'<th style="{_ths}">Gained/Lost</th>'
            f'<th style="{_ths}">Status</th>'
            f'<th style="{_ths}">Points</th>'
            "</tr>"
            "</thead>"
            f'<tbody style="background: #1A1D26;">{rows_html}</tbody>'
            "</table></div>"
        )

        st.markdown(table_html, unsafe_allow_html=True)

        # CSV download
        csv_data = show_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download results as CSV",
            csv_data,
            file_name=f"race_results_{race_id}.csv",
            mime="text/csv",
        )
    else:
        st.info("No results data available for this race.")
