from __future__ import annotations

import pandas as pd
import streamlit as st
from charts import (
    build_gap_timeline_chart,
    build_grid_finish_chart,
    build_lap_distribution_chart,
    build_position_chart,
    build_race_pace_chart,
    build_sector_heatmap,
    build_stint_chart,
    build_tyre_degradation_chart,
    format_lap_time_ms,
)
from data_access import get_races_for_season, load_race_bundle
from sqlalchemy.exc import ProgrammingError

st.set_page_config(page_title="F1 Race Decoder", page_icon="🏎️", layout="wide")

# ---------------------------------------------------------------------------
# Phosphor Icons CDN + Custom CSS — F1-inspired dark theme
# ---------------------------------------------------------------------------
# Load Phosphor Icons from CDN
st.markdown(
    """
    <link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web@2.0.3/src/regular/style.css" />
    <link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web@2.0.3/src/bold/style.css" />
    """,
    unsafe_allow_html=True,
)

# Custom CSS styles
st.markdown(
    """
    <style>
    /* ---- Page background ---- */
    .stApp {
        background: linear-gradient(135deg, #0F1117 0%, #131720 40%, #0D0F14 100%);
        color: #E5E7EB;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* ---- Hide default Streamlit header/footer ---- */
    header[data-testid="stHeader"] { background: transparent; }
    footer { display: none; }

    /* ---- Hide blinking cursor in dropdowns ---- */
    div[data-baseweb="select"] input {
        caret-color: transparent !important;
    }

    /* ---- Race header banner (reduced padding) ---- */
    .race-banner {
        background: linear-gradient(90deg, #E10600 0%, #8B0000 60%, #1A1D26 100%);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
    }
    .race-banner h1 {
        color: #FFFFFF;
        font-size: 1.75rem;
        margin: 0 0 0.2rem 0;
        font-weight: 800;
        letter-spacing: 0.02em;
    }
    .race-banner p {
        color: #E0D8D8;
        font-size: 0.95rem;
        margin: 0;
        letter-spacing: 0.03em;
    }

    /* ---- Podium cards with medal glow effects ---- */
    .podium-card {
        background: linear-gradient(180deg, #1E2130 0%, #1A1D26 100%);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .podium-card:hover {
        transform: translateY(-2px);
    }
    .podium-card .position-badge {
        font-size: 2rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 0.4rem;
    }
    .podium-card .driver-name {
        font-size: 1rem;
        font-weight: 700;
        color: #F0F0F0;
        margin-bottom: 0.15rem;
    }
    .podium-card .team-name {
        font-size: 0.8rem;
        color: #9CA3AF;
    }
    .podium-card .color-bar {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    /* P1 - Gold glow */
    .podium-p1 {
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.15), 0 4px 12px rgba(0,0,0,0.3);
        border: 1px solid rgba(255, 215, 0, 0.25);
    }
    .podium-p1 .position-badge { 
        color: #FFD700; 
        text-shadow: 0 0 12px rgba(255, 215, 0, 0.5);
    }
    /* P2 - Silver glow */
    .podium-p2 {
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.12), 0 3px 10px rgba(0,0,0,0.25);
        border: 1px solid rgba(192, 192, 192, 0.2);
    }
    .podium-p2 .position-badge { 
        color: #C0C0C0;
        text-shadow: 0 0 10px rgba(192, 192, 192, 0.4);
    }
    /* P3 - Bronze glow */
    .podium-p3 {
        box-shadow: 0 0 15px rgba(205, 127, 50, 0.12), 0 3px 10px rgba(0,0,0,0.25);
        border: 1px solid rgba(205, 127, 50, 0.2);
    }
    .podium-p3 .position-badge { 
        color: #CD7F32;
        text-shadow: 0 0 10px rgba(205, 127, 50, 0.4);
    }

    /* ---- Metric cards with icon support ---- */
    .metric-card {
        background: linear-gradient(180deg, #1E2130 0%, #1A1D26 100%);
        border-radius: 10px;
        padding: 0.75rem 0.6rem;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.05);
        transition: border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: rgba(255,255,255,0.12);
    }
    .metric-card .metric-icon {
        font-size: 1.1rem;
        margin-bottom: 0.25rem;
        opacity: 0.9;
    }
    .metric-card .metric-label {
        font-size: 0.65rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.2rem;
    }
    .metric-card .metric-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #FFFFFF;
    }
    .metric-card .metric-sub {
        font-size: 0.7rem;
        color: #6B7280;
        margin-top: 0.1rem;
    }
    /* Color-coded metric card variants */
    .metric-card.timing .metric-icon { color: #60A5FA; }
    .metric-card.timing .metric-value { color: #93C5FD; }
    .metric-card.count .metric-icon { color: #A78BFA; }
    .metric-card.incident .metric-icon { color: #FBBF24; }
    .metric-card.incident .metric-value { color: #FCD34D; }
    .metric-card.weather .metric-icon { color: #34D399; }
    .metric-card.movement .metric-icon { color: #F472B6; }

    /* ---- Tab styling with better states ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: #1A1D26;
        border-radius: 8px 8px 0 0;
        color: #6B7280;
        padding: 0.6rem 1.3rem;
        font-weight: 600;
        font-size: 0.9rem;
        border: 1px solid transparent;
        border-bottom: none;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #D1D5DB;
        background: #232736;
    }
    .stTabs [aria-selected="true"] {
        background: #E10600 !important;
        color: #FFFFFF !important;
        border-color: #E10600;
    }

    /* ---- Chart caption (slightly smaller) ---- */
    .chart-caption {
        color: #9CA3AF;
        font-size: 0.88rem;
        margin-bottom: 0.4rem;
        line-height: 1.5;
    }

    /* ---- Section sub-header ---- */
    .section-header {
        color: #E5E7EB;
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 0.3rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    /* ---- Footer ---- */
    .app-footer {
        text-align: center;
        color: #4B5563;
        font-size: 0.75rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #1F2937;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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

with _title_col:
    st.markdown(
        '<div style="padding-top:0.4rem;">'
        '<span style="font-size:2rem;font-weight:900;color:#E10600;'
        'letter-spacing:0.05em;">F1</span>'
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
    st.warning("No ingested races found for this season. Run `make ingest-single` first.")
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
positions_df = bundle["positions"]
race_control_df = bundle["race_control"]
pit_df = bundle["pit_markers"]
lap_times_df = bundle["lap_times"]
weather_df = bundle.get("weather", pd.DataFrame())

# ---------------------------------------------------------------------------
# Build driver name ↔ id map (for multiselect)
# ---------------------------------------------------------------------------
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
# Derive stats
# ---------------------------------------------------------------------------
race_row = season_races[season_races["race_id"] == race_id]
if race_row.empty:
    race_row = pd.DataFrame([selected_race])
r = race_row.iloc[0]

total_laps = int(positions_df["lap_number"].max()) if not positions_df.empty else 0
total_pit_stops = int(len(pit_df.index)) if not pit_df.empty else 0
neutralized_laps = (
    int(race_control_df[["is_sc", "is_vsc"]].fillna(False).any(axis=1).sum())
    if not race_control_df.empty
    else 0
)

# Fastest lap
fastest_lap_str = "\u2014"
fastest_lap_driver = ""
if not lap_times_df.empty:
    clean_laps = lap_times_df[
        lap_times_df["lap_time_ms"].notna()
        & (lap_times_df["lap_time_ms"] > 0)
        & (lap_times_df["lap_number"] > 1)
        & ~lap_times_df["is_pit_in_lap"].fillna(False)
        & ~lap_times_df["is_pit_out_lap"].fillna(False)
    ]
    if not clean_laps.empty:
        fastest_row = clean_laps.loc[clean_laps["lap_time_ms"].idxmin()]
        fastest_lap_str = format_lap_time_ms(fastest_row["lap_time_ms"])
        fname = fastest_row.get("full_name")
        fastest_lap_driver = (
            str(fname) if pd.notna(fname) else str(fastest_row.get("driver_code", ""))
        )

# Lead changes
lead_changes = 0
gap_df = bundle["gap"]
if not gap_df.empty and "leader_driver_id" in gap_df.columns:
    lead_changes = max(
        0,
        int((gap_df["leader_driver_id"] != gap_df["leader_driver_id"].shift()).sum()) - 1,
    )

# Biggest mover
biggest_mover_str = "\u2014"
mover_name = ""
gained_val = 0
if not results_df.empty:
    movers = results_df.dropna(subset=["grid_position", "finish_position"]).copy()
    if not movers.empty:
        movers["gained"] = movers["grid_position"].astype(int) - movers["finish_position"].astype(
            int
        )
        best = movers.loc[movers["gained"].idxmax()]
        gained_val = int(best["gained"])
        mover_name = (
            str(best["full_name"]) if pd.notna(best["full_name"]) else str(best["driver_code"])
        )
        if gained_val > 0:
            biggest_mover_str = f"+{gained_val}"
        elif gained_val == 0:
            biggest_mover_str = "0"
        else:
            biggest_mover_str = str(gained_val)

# Weather
track_temp_str = "\u2014"
conditions_str = "\u2014"
if not weather_df.empty:
    avg_track = weather_df["track_temp_c"].mean()
    if pd.notna(avg_track):
        lo = weather_df["track_temp_c"].min()
        hi = weather_df["track_temp_c"].max()
        track_temp_str = f"{lo:.0f}\u2013{hi:.0f}\u00b0C"
    rain_any = weather_df["rainfall"].fillna(False).any()
    rain_all = weather_df["rainfall"].fillna(False).all()
    if rain_all:
        conditions_str = "Wet"
    elif rain_any:
        conditions_str = "Mixed"
    else:
        conditions_str = "Dry"

podium_df = results_df[results_df["finish_position"].isin([1, 2, 3])].sort_values("finish_position")


def _podium_entry(row: pd.Series) -> dict:
    name = row.get("full_name")
    if pd.isna(name):
        name = row.get("driver_code", "\u2014")
    team = row.get("team_name", "")
    if pd.isna(team):
        team = ""
    color = row.get("team_color", "#E10600")
    if pd.isna(color):
        color = "#E10600"
    elif not str(color).startswith("#"):
        color = f"#{color}"
    return {"name": str(name), "team": str(team), "color": str(color)}


podium_entries = [_podium_entry(podium_df.iloc[i]) for i in range(len(podium_df))]


def _metric_html(
    label: str,
    value: str,
    sub: str = "",
    icon: str = "",
    variant: str = "",
) -> str:
    """Generate HTML for a metric card with optional Phosphor icon and color variant.

    Args:
        label: The metric label text
        value: The metric value to display
        sub: Optional subtitle/description
        icon: Phosphor icon class name (e.g., 'ph-bold ph-timer')
        variant: Color variant: 'timing', 'count', 'incident', 'weather', 'movement'
    """
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    icon_html = f'<div class="metric-icon"><i class="{icon}"></i></div>' if icon else ""
    variant_class = f" {variant}" if variant else ""
    return (
        f'<div class="metric-card{variant_class}">'
        f"{icon_html}"
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f"{sub_html}</div>"
    )


# ---------------------------------------------------------------------------
# A) Race Header Banner
# ---------------------------------------------------------------------------
race_dt = pd.to_datetime(r["race_datetime_utc"], utc=True)
date_str = race_dt.strftime("%d %B %Y")

st.markdown(
    f"""
    <div class="race-banner">
        <h1>Round {int(r['round'])} &middot; {r['event_name']}</h1>
        <p>{r['country']} &middot; {r['circuit']} &middot; {date_str}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# B) Podium & Stats Row
# ---------------------------------------------------------------------------
col_podium, col_stats = st.columns([3, 2], gap="large")

with col_podium:
    if len(podium_entries) >= 3:
        p1, p2, p3 = podium_entries[0], podium_entries[1], podium_entries[2]
        c2, c1, c3 = st.columns([1, 1.3, 1])
        with c1:
            st.markdown(
                f"""
                <div class="podium-card podium-p1" style="margin-top:0;">
                    <div class="color-bar"
                         style="background:{p1['color']};"></div>
                    <div class="position-badge">P1</div>
                    <div class="driver-name">{p1['name']}</div>
                    <div class="team-name">{p1['team']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="podium-card podium-p2" style="margin-top:1.5rem;">
                    <div class="color-bar"
                         style="background:{p2['color']};"></div>
                    <div class="position-badge">P2</div>
                    <div class="driver-name">{p2['name']}</div>
                    <div class="team-name">{p2['team']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="podium-card podium-p3" style="margin-top:1.5rem;">
                    <div class="color-bar"
                         style="background:{p3['color']};"></div>
                    <div class="position-badge">P3</div>
                    <div class="driver-name">{p3['name']}</div>
                    <div class="team-name">{p3['team']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with col_stats:
    sc_label = f"{neutralized_laps} lap{'s' if neutralized_laps != 1 else ''}"
    if neutralized_laps == 0:
        sc_label = "None"

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            _metric_html(
                "Fastest Lap",
                fastest_lap_str,
                fastest_lap_driver,
                icon="ph-bold ph-timer",
                variant="timing",
            ),
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            _metric_html(
                "Total Laps",
                str(total_laps),
                icon="ph-bold ph-flag-checkered",
                variant="count",
            ),
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            _metric_html(
                "Pit Stops",
                str(total_pit_stops),
                "all drivers",
                icon="ph-bold ph-wrench",
                variant="count",
            ),
            unsafe_allow_html=True,
        )
    with s4:
        st.markdown(
            _metric_html(
                "Safety Car",
                sc_label,
                icon="ph-bold ph-warning-circle",
                variant="incident",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)

    s5, s6, s7, s8 = st.columns(4)
    with s5:
        lc_label = str(lead_changes) if lead_changes > 0 else "None"
        st.markdown(
            _metric_html(
                "Lead Changes",
                lc_label,
                icon="ph-bold ph-arrows-left-right",
                variant="incident",
            ),
            unsafe_allow_html=True,
        )
    with s6:
        st.markdown(
            _metric_html(
                "Biggest Mover",
                biggest_mover_str,
                mover_name if gained_val > 0 else "",
                icon="ph-bold ph-trend-up",
                variant="movement",
            ),
            unsafe_allow_html=True,
        )
    with s7:
        st.markdown(
            _metric_html(
                "Track Temp",
                track_temp_str,
                icon="ph-bold ph-thermometer-simple",
                variant="weather",
            ),
            unsafe_allow_html=True,
        )
    with s8:
        st.markdown(
            _metric_html(
                "Conditions",
                conditions_str,
                icon="ph-bold ph-cloud-sun",
                variant="weather",
            ),
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Driver selection helper — returns highlight_top_n and highlight_driver_ids
# ---------------------------------------------------------------------------
_DRIVER_MODES = {
    "Top 5": 5,
    "Top 10": 10,
    "All drivers": 20,
    "Pick drivers\u2026": 0,
}


def _driver_selector(tab_key: str, default_mode: str = "Top 10") -> tuple[int, set[str] | None]:
    """Render a mode selector + optional multiselect.  Returns (top_n, ids)."""
    mode = st.selectbox(
        "Show",
        list(_DRIVER_MODES.keys()),
        index=list(_DRIVER_MODES.keys()).index(default_mode),
        key=f"{tab_key}_mode",
    )
    custom_ids: set[str] | None = None
    if mode == "Pick drivers\u2026":
        picks = st.multiselect(
            "Select drivers",
            all_driver_names,
            key=f"{tab_key}_custom",
        )
        if picks:
            custom_ids = {driver_name_to_id[n] for n in picks if n in driver_name_to_id}
    top_n = _DRIVER_MODES[mode] or 10
    return top_n, custom_ids


# ---------------------------------------------------------------------------
# C) Tabbed Analysis — 4 tabs
# ---------------------------------------------------------------------------
tab_story, tab_pace, tab_strategy, tab_results = st.tabs(
    ["Race Story", "Race Pace", "Strategy", "Full Results"]
)

# ---- Tab 1: Race Story ----
with tab_story:
    cap_col, ctrl_col = st.columns([4, 1])
    with cap_col:
        st.markdown(
            '<p class="chart-caption">'
            "<b>Leader vs Second Place Gap</b> &mdash; "
            "The time gap between the race leader and the driver in second. "
            "When the line rises, the leader is pulling away. "
            "When it drops, P2 is closing in "
            "&mdash; that means an exciting battle for the lead!</p>",
            unsafe_allow_html=True,
        )
    fig_gap = build_gap_timeline_chart(
        gap_df=bundle["gap"],
        race_control_df=bundle["race_control"],
        pit_markers_df=bundle["pit_markers"],
        show_sc_vsc=show_sc_vsc,
    )
    st.plotly_chart(fig_gap, use_container_width=True)

    st.markdown(
        '<p class="section-header">Position Chart</p>',
        unsafe_allow_html=True,
    )
    pos_cap_col, pos_ctrl_col = st.columns([3, 2])
    with pos_cap_col:
        st.markdown(
            '<p class="chart-caption">'
            "Where each driver ran throughout the race. "
            "P1 (the leader) is at the top. "
            "Watch for lines crossing each other "
            "&mdash; those are overtakes!</p>",
            unsafe_allow_html=True,
        )
    with pos_ctrl_col:
        pos_top_n, pos_ids = _driver_selector("pos", default_mode="Top 10")
    fig_pos = build_position_chart(
        positions_df=bundle["positions"],
        results_df=bundle["results"],
        highlight_top_n=pos_top_n,
        highlight_driver_ids=pos_ids,
    )
    st.plotly_chart(fig_pos, use_container_width=True)

# ---- Tab 2: Race Pace ----
with tab_pace:
    pace_cap_col, pace_ctrl_col = st.columns([3, 2])
    with pace_cap_col:
        st.markdown(
            '<p class="chart-caption">'
            "<b>Lap-by-Lap Pace</b> &mdash; "
            "Each line shows a driver's smoothed pace across the race. "
            "Lower means faster. "
            "Faded dots are individual lap times. "
            "Pit stops, safety car laps, and the opening lap are removed "
            "to show true racing speed.</p>",
            unsafe_allow_html=True,
        )
    with pace_ctrl_col:
        pace_top_n, pace_ids = _driver_selector("pace", default_mode="Top 5")
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
        "The box shows the typical range of lap times &mdash; "
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

# ---- Tab 3: Strategy ----
with tab_strategy:
    st.markdown(
        '<p class="chart-caption">'
        "<b>Tyre Strategy</b> &mdash; "
        "Each bar is a stint (the period between pit stops). "
        "Teams choose between tyre compounds: "
        '<span style="color:#FF3333;font-weight:700;">Soft</span> '
        "(fastest, wears out quickly), "
        '<span style="color:#FFC300;font-weight:700;">Medium</span> '
        "(balanced), and "
        '<span style="color:#F0F0F0;font-weight:700;">Hard</span> '
        "(slowest but lasts longest). "
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

# ---- Tab 4: Full Results ----
with tab_results:
    st.markdown(
        '<p class="chart-caption">'
        "<b>Grid vs Finish</b> &mdash; "
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
        display_df["Team"] = display_df["team_name"].fillna("\u2014")
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

        def _color_gained(val: int) -> str:
            if val > 0:
                return "color: #22C55E; font-weight: 700"
            elif val < 0:
                return "color: #EF4444; font-weight: 700"
            return "color: #9CA3AF"

        styled = show_df.style.map(_color_gained, subset=["Gained/Lost"])
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            height=min(len(show_df) * 38 + 40, 820),
        )

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

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="app-footer">Data sourced via FastF1 &middot; '
    "Stored in PostgreSQL &middot; Built with Streamlit</div>",
    unsafe_allow_html=True,
)
