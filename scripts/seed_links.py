"""Populate wikipedia_url and formula1_url for all ingested races.

Idempotent: safe to re-run. Uses ALTER TABLE ADD COLUMN IF NOT EXISTS
so it works on databases created before these columns were added to
init_warehouse.sql.

Usage:
    make seed-links          # via Docker (recommended)
    python scripts/seed_links.py   # locally (needs DB access + pipeline on PYTHONPATH)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pipeline.db import get_conn

# ---------------------------------------------------------------------------
# Wikipedia helpers
# ---------------------------------------------------------------------------
# FastF1 event_name → Wikipedia article title overrides.
# Most event names map cleanly via "{year}_{name_with_underscores}".
# Only entries that differ from that pattern need to be listed here.
_WIKI_OVERRIDES: dict[tuple[int, int], str] = {
    # 2020 COVID specials
    (2020, 2): "2020_Styrian_Grand_Prix",
    (2020, 5): "2020_70th_Anniversary_Grand_Prix",
    (2020, 9): "2020_Tuscan_Grand_Prix",
    (2020, 11): "2020_Eifel_Grand_Prix",
    (2020, 16): "2020_Sakhir_Grand_Prix",
    # 2021
    (2021, 8): "2021_Styrian_Grand_Prix",
}


def _build_wikipedia_url(season: int, round_number: int, event_name: str) -> str:
    """Build the Wikipedia article URL for a race."""
    override = _WIKI_OVERRIDES.get((season, round_number))
    if override:
        return f"https://en.wikipedia.org/wiki/{override}"
    slug = f"{season}_{event_name}".replace(" ", "_")
    return f"https://en.wikipedia.org/wiki/{slug}"


# ---------------------------------------------------------------------------
# Formula1.com slug mapping — (season, round) → slug
# ---------------------------------------------------------------------------
# URL pattern: https://www.formula1.com/en/racing/{season}/{slug}
# Verified against https://www.formula1.com/en/racing/{season} for each year.
_F1_COM_SLUGS: dict[tuple[int, int], str] = {
    # ── 2018 (21 races) ──────────────────────────────────────────────────
    (2018, 1): "australia",
    (2018, 2): "bahrain",
    (2018, 3): "china",
    (2018, 4): "azerbaijan",
    (2018, 5): "spain",
    (2018, 6): "monaco",
    (2018, 7): "canada",
    (2018, 8): "france",
    (2018, 9): "austria",
    (2018, 10): "great-britain",
    (2018, 11): "germany",
    (2018, 12): "hungary",
    (2018, 13): "belgium",
    (2018, 14): "italy",
    (2018, 15): "singapore",
    (2018, 16): "russia",
    (2018, 17): "japan",
    (2018, 18): "united-states",
    (2018, 19): "mexico",
    (2018, 20): "brazil",
    (2018, 21): "united-arab-emirates",
    # ── 2019 (21 races) ──────────────────────────────────────────────────
    (2019, 1): "australia",
    (2019, 2): "bahrain",
    (2019, 3): "china",
    (2019, 4): "azerbaijan",
    (2019, 5): "spain",
    (2019, 6): "monaco",
    (2019, 7): "canada",
    (2019, 8): "france",
    (2019, 9): "austria",
    (2019, 10): "great-britain",
    (2019, 11): "germany",
    (2019, 12): "hungary",
    (2019, 13): "belgium",
    (2019, 14): "italy",
    (2019, 15): "singapore",
    (2019, 16): "russia",
    (2019, 17): "japan",
    (2019, 18): "mexico",
    (2019, 19): "united-states",
    (2019, 20): "brazil",
    (2019, 21): "united-arab-emirates",
    # ── 2020 (17 races) ── COVID-reshuffled season ───────────────────────
    (2020, 1): "austria",
    (2020, 2): "styria",
    (2020, 3): "hungary",
    (2020, 4): "great-britain",
    (2020, 5): "70th-anniversary",
    (2020, 6): "spain",
    (2020, 7): "belgium",
    (2020, 8): "italy",
    (2020, 9): "tuscany",
    (2020, 10): "russia",
    (2020, 11): "germany",  # Eifel GP at Nurburgring
    (2020, 12): "portugal",
    (2020, 13): "emilia-romagna",  # hyphenated in 2020
    (2020, 14): "turkey",
    (2020, 15): "bahrain",
    (2020, 16): "sakhir",
    (2020, 17): "united-arab-emirates",
    # ── 2021 (22 races) ──────────────────────────────────────────────────
    (2021, 1): "bahrain",
    (2021, 2): "emiliaromagna",  # no hyphen from 2021 onward
    (2021, 3): "portugal",
    (2021, 4): "spain",
    (2021, 5): "monaco",
    (2021, 6): "azerbaijan",
    (2021, 7): "france",
    (2021, 8): "styria",
    (2021, 9): "austria",
    (2021, 10): "great-britain",
    (2021, 11): "hungary",
    (2021, 12): "belgium",
    (2021, 13): "netherlands",
    (2021, 14): "italy",
    (2021, 15): "russia",
    (2021, 16): "turkey",
    (2021, 17): "united-states",
    (2021, 18): "mexico",
    (2021, 19): "brazil",
    (2021, 20): "qatar",
    (2021, 21): "saudi-arabia",
    (2021, 22): "united-arab-emirates",
    # ── 2022 (22 races) ── Russia cancelled ──────────────────────────────
    (2022, 1): "bahrain",
    (2022, 2): "saudi-arabia",
    (2022, 3): "australia",
    (2022, 4): "emiliaromagna",
    (2022, 5): "miami",
    (2022, 6): "spain",
    (2022, 7): "monaco",
    (2022, 8): "azerbaijan",
    (2022, 9): "canada",
    (2022, 10): "great-britain",
    (2022, 11): "austria",
    (2022, 12): "france",
    (2022, 13): "hungary",
    (2022, 14): "belgium",
    (2022, 15): "netherlands",
    (2022, 16): "italy",
    (2022, 17): "singapore",
    (2022, 18): "japan",
    (2022, 19): "united-states",
    (2022, 20): "mexico",
    (2022, 21): "brazil",
    (2022, 22): "united-arab-emirates",
    # ── 2023 (22 races) ── Emilia Romagna cancelled (flooding) ───────────
    (2023, 1): "bahrain",
    (2023, 2): "saudi-arabia",
    (2023, 3): "australia",
    (2023, 4): "azerbaijan",
    (2023, 5): "miami",
    (2023, 6): "monaco",
    (2023, 7): "spain",
    (2023, 8): "canada",
    (2023, 9): "austria",
    (2023, 10): "great-britain",
    (2023, 11): "hungary",
    (2023, 12): "belgium",
    (2023, 13): "netherlands",
    (2023, 14): "italy",
    (2023, 15): "singapore",
    (2023, 16): "japan",
    (2023, 17): "qatar",
    (2023, 18): "united-states",
    (2023, 19): "mexico",
    (2023, 20): "brazil",
    (2023, 21): "las-vegas",
    (2023, 22): "united-arab-emirates",
    # ── 2024 (24 races) ──────────────────────────────────────────────────
    (2024, 1): "bahrain",
    (2024, 2): "saudi-arabia",
    (2024, 3): "australia",
    (2024, 4): "japan",
    (2024, 5): "china",
    (2024, 6): "miami",
    (2024, 7): "emiliaromagna",
    (2024, 8): "monaco",
    (2024, 9): "canada",
    (2024, 10): "spain",
    (2024, 11): "austria",
    (2024, 12): "great-britain",
    (2024, 13): "hungary",
    (2024, 14): "belgium",
    (2024, 15): "netherlands",
    (2024, 16): "italy",
    (2024, 17): "azerbaijan",
    (2024, 18): "singapore",
    (2024, 19): "united-states",
    (2024, 20): "mexico",
    (2024, 21): "brazil",
    (2024, 22): "las-vegas",
    (2024, 23): "qatar",
    (2024, 24): "united-arab-emirates",
    # ── 2025 (24 races) ──────────────────────────────────────────────────
    (2025, 1): "australia",
    (2025, 2): "china",
    (2025, 3): "japan",
    (2025, 4): "bahrain",
    (2025, 5): "saudi-arabia",
    (2025, 6): "miami",
    (2025, 7): "emiliaromagna",
    (2025, 8): "monaco",
    (2025, 9): "spain",
    (2025, 10): "canada",
    (2025, 11): "austria",
    (2025, 12): "great-britain",
    (2025, 13): "belgium",
    (2025, 14): "hungary",
    (2025, 15): "netherlands",
    (2025, 16): "italy",
    (2025, 17): "azerbaijan",
    (2025, 18): "singapore",
    (2025, 19): "united-states",
    (2025, 20): "mexico",
    (2025, 21): "brazil",
    (2025, 22): "las-vegas",
    (2025, 23): "qatar",
    (2025, 24): "united-arab-emirates",
}


def _build_f1_com_url(season: int, round_number: int) -> str | None:
    """Return the formula1.com race page URL, or None if not mapped."""
    slug = _F1_COM_SLUGS.get((season, round_number))
    if slug is None:
        return None
    return f"https://www.formula1.com/en/racing/{season}/{slug}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1) Ensure columns exist (idempotent for existing DBs)
            cur.execute(
                "ALTER TABLE metadata.races_catalog " "ADD COLUMN IF NOT EXISTS wikipedia_url TEXT"
            )
            cur.execute(
                "ALTER TABLE metadata.races_catalog " "ADD COLUMN IF NOT EXISTS formula1_url TEXT"
            )
            conn.commit()

            # 2) Fetch all race rows
            cur.execute(
                "SELECT race_id, season, round, event_name "
                "FROM metadata.races_catalog "
                "WHERE session_type = 'R' "
                "ORDER BY season, round"
            )
            rows = cur.fetchall()

            if not rows:
                print("No races found in metadata.races_catalog.")
                return

            # 3) Build and apply URLs
            updated = 0
            for race_id, season, round_number, event_name in rows:
                wiki_url = _build_wikipedia_url(season, round_number, event_name)
                f1_url = _build_f1_com_url(season, round_number)

                cur.execute(
                    "UPDATE metadata.races_catalog "
                    "SET wikipedia_url = %s, formula1_url = %s "
                    "WHERE race_id = %s",
                    (wiki_url, f1_url, race_id),
                )
                updated += 1

            conn.commit()
            print(f"Updated {updated} race(s) with external links.")


if __name__ == "__main__":
    main()
