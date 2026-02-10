"""Driver selection widget for chart filtering."""

from __future__ import annotations

import streamlit as st

_DRIVER_MODES = {
    "Top 5": 5,
    "Top 10": 10,
    "All drivers": 20,
    "Pick drivers\u2026": 0,
}


def driver_selector(
    tab_key: str,
    all_driver_names: list[str],
    driver_name_to_id: dict[str, str],
    default_mode: str = "Top 10",
) -> tuple[int, set[str] | None]:
    """Render a mode selector + optional multiselect. Returns (top_n, ids)."""
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
