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
# Header row — branding + GitHub link
# ---------------------------------------------------------------------------
_GITHUB_REPO = "https://github.com/shivaaang/f1-race-decoder-dashboard"

_f1_logo_path = Path(__file__).parent / "assets" / "F1.svg"
if _f1_logo_path.exists():
    _f1_logo_b64 = base64.b64encode(_f1_logo_path.read_bytes()).decode()
    _f1_logo_tag = (
        f'<img src="data:image/svg+xml;base64,{_f1_logo_b64}"'
        ' alt="F1" style="height:2.25rem;vertical-align:-0.35rem;'
        'margin-right:0.4rem;" />'
    )
else:
    _f1_logo_tag = (
        '<span style="font-size:2.5rem;font-weight:900;'
        'color:#E10600;letter-spacing:0.05em;">F1</span>'
    )

_gh_svg = (
    '<svg height="16" width="16" viewBox="0 0 16 16" fill="#E5E7EB">'
    '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 '
    "5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49"
    "-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13"
    "-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 "
    "1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2"
    "-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-"
    ".36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 "
    "2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82"
    ".44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 "
    "3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 "
    "1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 "
    '0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'
)

st.markdown(
    '<div style="display:flex;justify-content:space-between;'
    'align-items:center;padding:0.2rem 0 0.6rem 0;">'
    f'<div>{_f1_logo_tag}<span style="font-size:1.6rem;'
    'font-weight:600;color:#E5E7EB;">Race Decoder</span></div>'
    f'<a href="{_GITHUB_REPO}" target="_blank" '
    'style="display:inline-flex;align-items:center;gap:0.35rem;'
    "padding:0.45rem 0.75rem;border-radius:6px;"
    "background:#252A3A;color:#E5E7EB;text-decoration:none;"
    "font-size:0.8rem;font-weight:600;border:1px solid #374151;"
    f'white-space:nowrap;">{_gh_svg} GitHub</a>'
    "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Selector row — season & race (primary controls)
# ---------------------------------------------------------------------------
_season_col, _race_col = st.columns([1, 3])

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
    int(row.round): f"Round {int(row.round)} · {row.event_name}"
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
