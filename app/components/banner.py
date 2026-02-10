"""Race header banner with integrated external links."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_banner(selected_race: pd.Series, r: pd.Series) -> None:
    """Render the race header banner with optional Wikipedia/F1.com links."""
    race_dt = pd.to_datetime(r["race_datetime_utc"], utc=True)
    date_str = race_dt.strftime("%d %B %Y")

    wiki_url = (
        selected_race.get("wikipedia_url") if pd.notna(selected_race.get("wikipedia_url")) else None
    )
    f1_url = (
        selected_race.get("formula1_url") if pd.notna(selected_race.get("formula1_url")) else None
    )

    event_short = r["event_name"].replace(" Grand Prix", " GP")

    banner_links = ""
    if wiki_url or f1_url:
        link_items = ""
        if wiki_url:
            link_items += (
                f'<a class="banner-link" href="{wiki_url}" '
                'target="_blank" rel="noopener">'
                '<i class="ph-bold ph-article"></i>'
                f"<span>{event_short} on Wiki</span></a>"
            )
        if f1_url:
            link_items += (
                f'<a class="banner-link" href="{f1_url}" '
                'target="_blank" rel="noopener">'
                '<i class="ph-bold ph-flag-checkered"></i>'
                f"<span>{event_short} on F1.com</span></a>"
            )
        banner_links = f'<div class="banner-links">{link_items}</div>'

    st.markdown(
        f"""
        <div class="race-banner">
            <div>
                <h1>Round {int(r['round'])} &middot; {r['event_name']}</h1>
                <p>{r['country']} &middot; {r['circuit']} &middot; {date_str}</p>
            </div>
            {banner_links}
        </div>
        """,
        unsafe_allow_html=True,
    )
