# F1 Race Decoder

A Formula 1 race analysis dashboard that turns raw timing data into interactive visualizations. Built with a proper data engineering backend — data flows from the FastF1 API through a multi-layer PostgreSQL data warehouse and surfaces in a Streamlit dashboard with Plotly charts.

Covers every race from **2018 to 2025** — 8 seasons, 170+ grands prix.

<!-- ![Dashboard Screenshot](docs/screenshot.png) -->

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Source | [FastF1](https://github.com/theOehrly/Fast-F1) (unofficial F1 timing API) |
| Database | PostgreSQL 18 — 4-schema warehouse (staging → curated → marts) |
| Pipeline | Python 3.12, psycopg, idempotent upserts with SHA1-based stable IDs |
| Dashboard | Streamlit 1.54, Plotly 6.5 |
| Infrastructure | Docker Compose (3 services), Makefile automation |

## Dashboard

**5 analysis tabs covering every angle of a race:**

- **Race Story** — Position changes and gap-to-leader timeline across every lap
- **Race Pace** — Smoothed pace lines, lap time box plots, and sector performance heatmaps
- **Strategy** — Tyre stint visualization and compound degradation curves
- **Driver Deep Dive** — Head-to-head lap deltas, sector comparisons, and gap-to-leader overlays for any two drivers
- **Full Results** — Grid-vs-finish dumbbell chart and full race classification

**At a glance:** Podium cards with team colors, 8 stat KPIs (fastest lap, safety car laps, lead changes, biggest mover, track conditions), and SC/VSC shading on every chart. Dark theme throughout.

## Architecture

```
FastF1 API
    ↓
 Extract ─→ Staging (raw typed) ─→ Curated (facts + dims) ─→ Marts (precomputed)
                                                                     ↓
                                                                Streamlit App
```

The Streamlit app is **read-only** — it queries marts and curated tables via SQLAlchemy and never touches the external API. Ingestion runs on-demand in a separate container.

**Key design decisions:**
- All durations stored as `BIGINT` milliseconds — no floating-point precision issues
- Deterministic IDs via SHA1 hashing make ingestion fully idempotent
- Marts use DELETE + INSERT per race (not upsert) — clean regeneration, no stale data
- Separate Docker containers for ingestion and dashboard

## Project Structure

```
app/
├── main.py              # Slim orchestrator (~200 lines)
├── data_access.py       # SQLAlchemy queries against curated/marts
├── charts/              # Plotly chart builders (6 modules)
├── components/          # Banner, metric cards, driver selector
├── tabs/                # One render module per tab
└── theme/               # Dark theme CSS + Phosphor icons

pipeline/
├── extract.py           # FastF1 fetch with exponential backoff
├── transform.py         # Staging + curated dataframe builders
├── load.py              # Upserts and mart replacements
├── marts.py             # Precomputed aggregations
└── quality.py           # Post-ingestion data quality checks

sql/                     # DDL for all 4 schemas (15 tables)
scripts/                 # Ingestion CLI + fault-tolerant backfill
docker/                  # Dockerfiles for streamlit + ingest containers
```

## Quick Start

```bash
# Clone and configure
git clone https://github.com/<your-username>/f1-race-decoder.git
cd f1-race-decoder
cp .env.example .env              # defaults work out of the box

# Start services and initialize the database
make up                           # postgres + streamlit
make db-bootstrap                 # create schemas and tables

# Ingest your first race
make ingest-single                # loads 2024 Bahrain GP

# Open the dashboard
open http://localhost:8501
```

**Backfill more data:**

```bash
make backfill-season SEASON=2024                        # one season
make backfill-safe SEASON_START=2018 SEASON_END=2025    # all seasons with automatic retries
```

## Database Schema

Four PostgreSQL schemas forming a classic data warehouse:

- **metadata** — Ingestion run tracking and data quality check results
- **staging** — Raw typed data (laps, results, weather) loaded as-is from FastF1
- **curated** — Star schema with fact tables (`fact_lap`, `fact_session_results`, `fact_race_control`, `fact_weather_minute`) and dimensions (`dim_race`, `dim_driver`, `dim_team`)
- **marts** — Dashboard-optimized tables: `mart_gap_timeline`, `mart_position_chart`, `mart_stint_summary`

## Development

```bash
make lint                # ruff + black (check mode)
make format              # auto-format
make logs                # stream Docker logs
make reset-db            # hard reset — drops all data
```
