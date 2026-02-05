SHELL := /bin/bash

.PHONY: up down reset-db db-bootstrap seed-links ingest-single backfill-season backfill-range backfill-safe logs open-streamlit lint format docker-clean

up:
	docker compose --env-file .env up -d --build

down:
	docker compose --env-file .env down --remove-orphans

reset-db:
	docker compose --env-file .env down -v --remove-orphans

db-bootstrap:
	docker compose --env-file .env --profile tools run --rm ingest python -m pipeline.bootstrap

seed-links:
	docker compose --env-file .env --profile tools run --rm ingest \
		python scripts/seed_links.py

ingest-single:
	docker compose --env-file .env --profile tools run --rm ingest \
		python scripts/run_ingest.py single --season 2024 --round 1 --session-type R

backfill-season:
	docker compose --env-file .env --profile tools run --rm ingest \
		python scripts/run_ingest.py season --season $${SEASON:-2024} --session-type R

backfill-range:
	docker compose --env-file .env --profile tools run --rm ingest \
		python scripts/run_ingest.py range --season-start $${SEASON_START:-2018} --season-end $${SEASON_END:-2025} --session-type R

backfill-safe:
	docker compose --env-file .env --profile tools run --rm ingest \
		python scripts/backfill_until_complete.py --season-start $${SEASON_START:-2018} --season-end $${SEASON_END:-2025} --max-passes $${MAX_PASSES:-8}

open-streamlit:
	@echo "Streamlit: http://localhost:8501"

logs:
	docker compose --env-file .env logs -f --tail=200

lint:
	ruff check .
	black --check .

format:
	black .
	ruff check . --fix

docker-clean:
	docker image prune -f
	docker builder prune -f
