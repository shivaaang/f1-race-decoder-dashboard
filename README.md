# F1 Race Decoder

Production-style F1 dashboard platform focused on one thing: a great user-facing race analysis experience.

## Stack

- Docker Compose
- Postgres 18
- Streamlit 1.54.0 + Plotly 6.5.2
- FastF1 3.7.0 (ingestion only, never in Streamlit)
- Python 3.12

## Architecture

```text
FastF1 extract (manual CLI trigger)
  -> staging (typed normalized)
  -> curated (facts/dims with stable keys)
  -> marts (dashboard-ready precomputes)
  -> Streamlit (read-only queries)
```

Design rules implemented:
- Streamlit never calls FastF1
- Idempotent reloads using deterministic keys + upserts
- Durations stored as integer milliseconds
- UTC timestamps stored as `TIMESTAMPTZ`

## Why no Airflow

Airflow was removed to reduce operational complexity. This project now uses simple manual ingestion commands because race data is mostly historical and does not need constant scheduling.

## Project Structure

```text
.
├── app/
├── docker/
│   ├── Dockerfile.ingest
│   ├── Dockerfile.streamlit
│   └── postgres-init/
├── pipeline/
├── scripts/
├── sql/
├── tests/
├── docker-compose.yml
└── Makefile
```

## Quick Start

1. Copy env defaults.

```bash
cp .env.example .env
```

2. Start services.

```bash
make up
```

3. Initialize warehouse schemas/tables.

```bash
make db-bootstrap
```

4. Ingest one race (example: 2024 round 1).

```bash
make ingest-single
```

5. Open dashboard.

- Streamlit: [http://localhost:8501](http://localhost:8501)

## Ingestion Commands

Single race:

```bash
make ingest-single
```

Whole season (default `SEASON=2024`):

```bash
make backfill-season
# override:
SEASON=2021 make backfill-season
```

Range backfill (default `2018..2025`):

```bash
make backfill-range
# override:
SEASON_START=2018 SEASON_END=2025 make backfill-range
```

Safe full backfill with retries (recommended for first load):

```bash
make backfill-safe
# override:
SEASON_START=2018 SEASON_END=2025 MAX_PASSES=10 make backfill-safe
```

## Common Commands

```bash
make up
make down
make reset-db
make db-bootstrap
make ingest-single
make backfill-season
make backfill-range
make backfill-safe
make logs
make lint
make test
make docker-clean
```

## Streamlit View (Week 1)

Page: **Race Decoder**

Controls:
- Season dropdown
- Round dropdown
- Load race button
- Focus driver
- Top-N highlight slider
- Show-all toggle
- SC/VSC shading toggle

Charts:
- Leader vs P2 gap timeline
- Position changes by lap
- Tyre strategy stint bars

All charts read from Postgres curated/marts tables only.

## Idempotency Notes

- `metadata.races_catalog` upserts by `race_id`
- Dims use deterministic stable IDs
- Curated facts upsert by PK
- Marts rebuild by `race_id` (`DELETE + INSERT`)
- Re-running the same race converges to same state

## Data Quality Checks

Each ingestion run stores checks in `metadata.data_quality_checks`.

## Development

```bash
pip install -r requirements-dev.txt
make lint
make test
```

## Screenshots (placeholders)

- `docs/screenshots/streamlit-race-decoder.png`
