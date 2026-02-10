from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st
from data_access import get_races_for_season, load_race_bundle
from sqlalchemy.exc import ProgrammingError

st.set_page_config(page_title="F1 Race Decoder", page_icon="🏎️", layout="wide")

from components import render_banner, render_summary  # noqa: E402
from components.metrics import derive_race_stats  # noqa: E402
from tabs import (  # noqa: E402
    driver_deep_dive,
    full_results,
    race_pace,
    race_story,
    strategy,
)
from theme import inject_theme  # noqa: E402

inject_theme()


# ---------------------------------------------------------------------------
# Cached data helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def cached_races_for_season(season: int) -> pd.DataFrame:
    return get_races_for_season(season)


@st.cache_data(ttl=600, show_spinner=False)
def cached_race_bundle(race_id: str) -> dict[str, pd.DataFrame]:
    return load_race_bundle(race_id)


# ---------------------------------------------------------------------------
# Top bar — branding + race selection (no sidebar)
# ---------------------------------------------------------------------------
_title_col, _season_col, _race_col = st.columns([3, 1, 2])

# Load F1 logo SVG for header
_f1_logo_path = Path(__file__).parent / "assets" / "F1.svg"
if _f1_logo_path.exists():
    _f1_logo_b64 = base64.b64encode(_f1_logo_path.read_bytes()).decode()
    _f1_logo_tag = (
        f'<img src="data:image/svg+xml;base64,{_f1_logo_b64}"'
        ' alt="F1" style="height:1.8rem;vertical-align:middle;'
        'margin-right:0.3rem;" />'
    )
else:
    _f1_logo_tag = (
        '<span style="font-size:2rem;font-weight:900;'
        'color:#E10600;letter-spacing:0.05em;">F1</span>'
    )

with _title_col:
    st.markdown(
        '<div style="padding-top:0.4rem;">'
        f"{_f1_logo_tag}"
        '<span style="font-size:1.3rem;font-weight:600;color:#E5E7EB;">'
        " Race Decoder</span></div>",
        unsafe_allow_html=True,
    )

with _season_col:
    season = st.selectbox("Season", list(range(2018, 2026)), index=7)

try:
    season_races = cached_races_for_season(season)
except ProgrammingError as exc:
    if "metadata.races_catalog" in str(exc):
        st.error(
            "Database tables are not initialized yet.\n\n"
            "Run these commands once:\n"
            "1) `make db-bootstrap`\n"
            "2) `make ingest-single`"
        )
        st.stop()
    raise

if season_races.empty:
    st.warning("No ingested races found for this season. " "Run `make ingest-single` first.")
    st.stop()

round_options = season_races["round"].astype(int).tolist()
round_labels = {
    int(row.round): f"Round {int(row.round)} \u2014 {row.event_name}"
    for row in season_races.itertuples()
}

with _race_col:
    round_number = st.selectbox(
        "Grand Prix",
        round_options,
        format_func=lambda value: round_labels.get(int(value), str(value)),
    )

selected_race = season_races.loc[season_races["round"] == round_number].iloc[0]
race_id = selected_race["race_id"]

show_sc_vsc = True


# ---------------------------------------------------------------------------
# Load race bundle
# ---------------------------------------------------------------------------
bundle = cached_race_bundle(race_id)

if bundle["drivers"].empty:
    st.error(
        "Race data exists in catalog but marts/curated rows are missing. "
        "Re-run ingestion for this race."
    )
    st.stop()

results_df = bundle["results"]
race_control_df = bundle["race_control"]
pit_df = bundle["pit_markers"]
lap_times_df = bundle["lap_times"]

# Build driver name ↔ id map (for multiselect)
all_driver_names: list[str] = []
driver_name_to_id: dict[str, str] = {}
if not bundle["drivers"].empty:
    for _, d in bundle["drivers"].iterrows():
        name = (
            str(d["full_name"]) if pd.notna(d.get("full_name")) else str(d.get("driver_code", "?"))
        )
        all_driver_names.append(name)
        driver_name_to_id[name] = d["driver_id"]


# ---------------------------------------------------------------------------
# Derive stats + render banner and summary
# ---------------------------------------------------------------------------
race_row = season_races[season_races["race_id"] == race_id]
if race_row.empty:
    race_row = pd.DataFrame([selected_race])
r = race_row.iloc[0]

render_banner(selected_race, r)
stats = derive_race_stats(bundle)
render_summary(stats)


# ---------------------------------------------------------------------------
# Tabbed Analysis — 5 tabs
# ---------------------------------------------------------------------------
tab_story, tab_pace, tab_strategy, tab_deep_dive, tab_results = st.tabs(
    [
        "\U0001f4ca Race Story",
        "\u23f1\ufe0f Race Pace",
        "\U0001f6de Strategy",
        "\U0001f50d Driver Deep Dive",
        "\U0001f4cb Full Results",
    ]
)

with tab_story:
    race_story.render(bundle, all_driver_names, driver_name_to_id, show_sc_vsc)

with tab_pace:
    race_pace.render(
        bundle,
        results_df,
        lap_times_df,
        race_control_df,
        all_driver_names,
        driver_name_to_id,
        show_sc_vsc,
    )

with tab_strategy:
    strategy.render(bundle, results_df, lap_times_df, race_control_df)

with tab_deep_dive:
    driver_deep_dive.render(bundle, results_df, lap_times_df, race_control_df, pit_df)

with tab_results:
    full_results.render(results_df, race_id)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="app-footer">Data sourced via FastF1 &middot; '
    "Stored in PostgreSQL &middot; Built with Streamlit</div>",
    unsafe_allow_html=True,
)
