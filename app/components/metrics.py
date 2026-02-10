"""Metric cards, stat derivation, and summary strip rendering."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st
from charts import format_lap_time_ms


@dataclass(frozen=True)
class RaceStats:
    total_laps: int
    total_pit_stops: int
    neutralized_laps: int
    fastest_lap_str: str
    fastest_lap_driver: str
    lead_changes: int
    biggest_mover_str: str
    mover_name: str
    gained_val: int
    track_temp_str: str
    conditions_str: str
    podium_entries: list[dict]


def derive_race_stats(bundle: dict[str, pd.DataFrame]) -> RaceStats:
    """Compute all dashboard summary statistics from the race bundle."""
    results_df = bundle["results"]
    positions_df = bundle["positions"]
    race_control_df = bundle["race_control"]
    pit_df = bundle["pit_markers"]
    lap_times_df = bundle["lap_times"]
    weather_df = bundle.get("weather", pd.DataFrame())

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
            movers["gained"] = movers["grid_position"].astype(int) - movers[
                "finish_position"
            ].astype(int)
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

    # Podium
    podium_df = results_df[results_df["finish_position"].isin([1, 2, 3])].sort_values(
        "finish_position"
    )

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

    return RaceStats(
        total_laps=total_laps,
        total_pit_stops=total_pit_stops,
        neutralized_laps=neutralized_laps,
        fastest_lap_str=fastest_lap_str,
        fastest_lap_driver=fastest_lap_driver,
        lead_changes=lead_changes,
        biggest_mover_str=biggest_mover_str,
        mover_name=mover_name,
        gained_val=gained_val,
        track_temp_str=track_temp_str,
        conditions_str=conditions_str,
        podium_entries=podium_entries,
    )


def metric_html(
    label: str,
    value: str,
    sub: str = "",
    icon: str = "",
    variant: str = "",
    tooltip: str = "",
) -> str:
    """Generate HTML for a metric card with optional Phosphor icon and color variant."""
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    icon_html = f'<div class="metric-icon"><i class="{icon}"></i></div>' if icon else ""
    variant_class = f" {variant}" if variant else ""
    tooltip_html = f'<div class="metric-tooltip">{tooltip}</div>' if tooltip else ""
    tooltip_class = " has-tooltip" if tooltip else ""
    return (
        f'<div class="metric-card{variant_class}{tooltip_class}">'
        f"{icon_html}"
        f'<div class="metric-body">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f"{sub_html}"
        f"</div>"
        f"{tooltip_html}</div>"
    )


def render_summary(stats: RaceStats) -> None:
    """Render the combined podium + KPI summary strip."""
    s = stats

    sc_label = f"{s.neutralized_laps} lap{'s' if s.neutralized_laps != 1 else ''}"
    if s.neutralized_laps == 0:
        sc_label = "None"
    sc_variant = "incident-high" if s.neutralized_laps > s.total_laps * 0.1 else "incident"
    lc_label = str(s.lead_changes) if s.lead_changes > 0 else "None"

    # Build podium HTML
    podium_html = ""
    if len(s.podium_entries) >= 3:
        p1, p2, p3 = s.podium_entries[0], s.podium_entries[1], s.podium_entries[2]
        podium_html = (
            '<div class="summary-podium">\n' '<div class="summary-section-title">Podium</div>\n'
        )
        for pos, p in [("p1", p1), ("p2", p2), ("p3", p3)]:
            badge = pos.upper()
            podium_html += (
                f'<div class="compact-podium cp-{pos}">'
                f'<div class="cp-badge">{badge}</div>'
                f'<div class="cp-info">'
                f'<div class="cp-driver">{p["name"]}</div>'
                f'<div class="cp-team">'
                f'<span class="cp-color-dot" '
                f'style="background:{p["color"]}"></span>'
                f'{p["team"]}</div>'
                f"</div></div>\n"
            )
        podium_html += "</div>"

    # Build KPI HTML
    kpi_cards = [
        metric_html(
            "Fastest Lap",
            s.fastest_lap_str,
            s.fastest_lap_driver,
            icon="ph-bold ph-timer",
            variant="timing",
            tooltip="Best single lap time of the race",
        ),
        metric_html(
            "Total Laps",
            str(s.total_laps),
            icon="ph-bold ph-flag-checkered",
            variant="count",
            tooltip="Total laps completed in the race",
        ),
        metric_html(
            "Pit Stops",
            str(s.total_pit_stops),
            "all drivers",
            icon="ph-bold ph-wrench",
            variant="count",
            tooltip="Combined pit stops by all drivers",
        ),
        metric_html(
            "Safety Car",
            sc_label,
            icon="ph-bold ph-warning-circle",
            variant=sc_variant,
            tooltip="Laps under Safety Car or Virtual Safety Car",
        ),
        metric_html(
            "Lead Changes",
            lc_label,
            icon="ph-bold ph-arrows-left-right",
            variant="incident",
            tooltip="Times the race leader changed",
        ),
        metric_html(
            "Biggest Mover",
            s.biggest_mover_str,
            s.mover_name if s.gained_val > 0 else "",
            icon="ph-bold ph-trend-up",
            variant="movement",
            tooltip="Driver who gained the most positions",
        ),
        metric_html(
            "Track Temp",
            s.track_temp_str,
            icon="ph-bold ph-thermometer-simple",
            variant="weather",
            tooltip="Track temperature during the race",
        ),
        metric_html(
            "Conditions",
            s.conditions_str,
            icon="ph-bold ph-cloud-sun",
            variant="weather",
            tooltip="Weather conditions during the race",
        ),
    ]
    kpi_grid = "\n".join(kpi_cards)

    st.markdown(
        f"""<div class="dashboard-summary">
{podium_html}
<div class="summary-stats">
<div class="summary-section-title">Race Stats</div>
<div class="summary-kpis">
{kpi_grid}
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )
