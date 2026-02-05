CREATE SCHEMA IF NOT EXISTS metadata;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS metadata.ingestion_runs (
    run_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    session_type TEXT NOT NULL,
    code_version TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS metadata.races_catalog (
    race_id TEXT PRIMARY KEY,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    circuit TEXT,
    country TEXT,
    race_datetime_utc TIMESTAMPTZ,
    fastf1_event_key TEXT,
    session_type TEXT NOT NULL DEFAULT 'R',
    is_ingested BOOLEAN NOT NULL DEFAULT FALSE,
    last_ingested_at TIMESTAMPTZ,
    wikipedia_url TEXT,
    formula1_url TEXT,
    UNIQUE (season, round, session_type)
);

CREATE INDEX IF NOT EXISTS idx_races_catalog_season_round
    ON metadata.races_catalog (season, round);

CREATE TABLE IF NOT EXISTS metadata.data_quality_checks (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES metadata.ingestion_runs(run_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_quality_checks_run
    ON metadata.data_quality_checks (run_id);

CREATE TABLE IF NOT EXISTS staging.session_laps (
    run_id TEXT NOT NULL,
    race_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    session_type TEXT NOT NULL,
    driver_code TEXT NOT NULL,
    driver_number TEXT,
    lap_number INTEGER NOT NULL,
    position INTEGER,
    lap_time_ms BIGINT,
    stint INTEGER,
    compound TEXT,
    tyre_life_laps INTEGER,
    fresh_tyre BOOLEAN,
    is_accurate BOOLEAN,
    is_pit_in_lap BOOLEAN,
    is_pit_out_lap BOOLEAN,
    pit_in_time_ms BIGINT,
    pit_out_time_ms BIGINT,
    track_status_flags TEXT,
    sector1_ms BIGINT,
    sector2_ms BIGINT,
    sector3_ms BIGINT
);

CREATE INDEX IF NOT EXISTS idx_staging_laps_race
    ON staging.session_laps (race_id, lap_number);

CREATE TABLE IF NOT EXISTS staging.session_results (
    run_id TEXT NOT NULL,
    race_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    session_type TEXT NOT NULL,
    driver_code TEXT NOT NULL,
    driver_number TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    team_name TEXT,
    team_color TEXT,
    grid_position INTEGER,
    finish_position INTEGER,
    classified_position TEXT,
    status TEXT,
    points NUMERIC(8,2),
    race_time_ms BIGINT
);

CREATE INDEX IF NOT EXISTS idx_staging_results_race
    ON staging.session_results (race_id);

CREATE TABLE IF NOT EXISTS staging.session_weather (
    run_id TEXT NOT NULL,
    race_id TEXT NOT NULL,
    timestamp_utc TIMESTAMPTZ NOT NULL,
    air_temp_c NUMERIC(6,3),
    track_temp_c NUMERIC(6,3),
    humidity_pct NUMERIC(6,3),
    pressure_mbar NUMERIC(8,3),
    rainfall BOOLEAN,
    wind_dir_deg NUMERIC(6,2),
    wind_speed_ms NUMERIC(8,3)
);

CREATE INDEX IF NOT EXISTS idx_staging_weather_race_ts
    ON staging.session_weather (race_id, timestamp_utc);

CREATE TABLE IF NOT EXISTS curated.dim_race (
    race_id TEXT PRIMARY KEY,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    circuit TEXT,
    country TEXT,
    race_date_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS curated.dim_driver (
    driver_id TEXT PRIMARY KEY,
    driver_code TEXT NOT NULL UNIQUE,
    driver_number TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT
);

CREATE TABLE IF NOT EXISTS curated.dim_team (
    team_id TEXT PRIMARY KEY,
    team_name TEXT NOT NULL UNIQUE,
    team_color TEXT
);

CREATE TABLE IF NOT EXISTS curated.dim_driver_team_season (
    season INTEGER NOT NULL,
    driver_id TEXT NOT NULL REFERENCES curated.dim_driver(driver_id),
    team_id TEXT NOT NULL REFERENCES curated.dim_team(team_id),
    PRIMARY KEY (season, driver_id, team_id)
);

CREATE TABLE IF NOT EXISTS curated.fact_lap (
    race_id TEXT NOT NULL REFERENCES curated.dim_race(race_id) ON DELETE CASCADE,
    driver_id TEXT NOT NULL REFERENCES curated.dim_driver(driver_id),
    lap_number INTEGER NOT NULL,
    position INTEGER,
    lap_time_ms BIGINT,
    stint INTEGER,
    compound TEXT,
    tyre_life_laps INTEGER,
    fresh_tyre BOOLEAN,
    is_accurate BOOLEAN,
    is_pit_in_lap BOOLEAN,
    is_pit_out_lap BOOLEAN,
    pit_in_time_ms BIGINT,
    pit_out_time_ms BIGINT,
    track_status_flags TEXT,
    sector1_ms BIGINT,
    sector2_ms BIGINT,
    sector3_ms BIGINT,
    PRIMARY KEY (race_id, driver_id, lap_number)
);

CREATE INDEX IF NOT EXISTS idx_fact_lap_race_lap
    ON curated.fact_lap (race_id, lap_number);
CREATE INDEX IF NOT EXISTS idx_fact_lap_race_driver
    ON curated.fact_lap (race_id, driver_id);

CREATE TABLE IF NOT EXISTS curated.fact_session_results (
    race_id TEXT NOT NULL REFERENCES curated.dim_race(race_id) ON DELETE CASCADE,
    driver_id TEXT NOT NULL REFERENCES curated.dim_driver(driver_id),
    team_id TEXT REFERENCES curated.dim_team(team_id),
    grid_position INTEGER,
    finish_position INTEGER,
    classified_position TEXT,
    status TEXT,
    points NUMERIC(8,2),
    race_time_ms BIGINT,
    gap_to_winner_ms BIGINT,
    PRIMARY KEY (race_id, driver_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_results_race_driver
    ON curated.fact_session_results (race_id, driver_id);

CREATE TABLE IF NOT EXISTS curated.fact_race_control (
    race_id TEXT NOT NULL REFERENCES curated.dim_race(race_id) ON DELETE CASCADE,
    lap_number INTEGER NOT NULL,
    is_sc BOOLEAN NOT NULL,
    is_vsc BOOLEAN NOT NULL,
    is_red_flag BOOLEAN NOT NULL,
    is_yellow_flag BOOLEAN NOT NULL,
    PRIMARY KEY (race_id, lap_number)
);

CREATE INDEX IF NOT EXISTS idx_fact_race_control_race_lap
    ON curated.fact_race_control (race_id, lap_number);

CREATE TABLE IF NOT EXISTS curated.fact_weather_minute (
    race_id TEXT NOT NULL REFERENCES curated.dim_race(race_id) ON DELETE CASCADE,
    timestamp_utc TIMESTAMPTZ NOT NULL,
    air_temp_c NUMERIC(6,3),
    track_temp_c NUMERIC(6,3),
    humidity_pct NUMERIC(6,3),
    pressure_mbar NUMERIC(8,3),
    rainfall BOOLEAN,
    wind_dir_deg NUMERIC(6,2),
    wind_speed_ms NUMERIC(8,3),
    PRIMARY KEY (race_id, timestamp_utc)
);

CREATE INDEX IF NOT EXISTS idx_fact_weather_race_ts
    ON curated.fact_weather_minute (race_id, timestamp_utc);

CREATE TABLE IF NOT EXISTS marts.mart_gap_timeline (
    race_id TEXT NOT NULL REFERENCES curated.dim_race(race_id) ON DELETE CASCADE,
    lap_number INTEGER NOT NULL,
    leader_driver_id TEXT,
    p2_driver_id TEXT,
    gap_p2_to_leader_ms BIGINT,
    PRIMARY KEY (race_id, lap_number)
);

CREATE INDEX IF NOT EXISTS idx_mart_gap_race_lap
    ON marts.mart_gap_timeline (race_id, lap_number);

CREATE TABLE IF NOT EXISTS marts.mart_position_chart (
    race_id TEXT NOT NULL REFERENCES curated.dim_race(race_id) ON DELETE CASCADE,
    driver_id TEXT NOT NULL REFERENCES curated.dim_driver(driver_id),
    lap_number INTEGER NOT NULL,
    position INTEGER,
    team_id TEXT REFERENCES curated.dim_team(team_id),
    PRIMARY KEY (race_id, driver_id, lap_number)
);

CREATE INDEX IF NOT EXISTS idx_mart_position_race_lap
    ON marts.mart_position_chart (race_id, lap_number);

CREATE TABLE IF NOT EXISTS marts.mart_stint_summary (
    race_id TEXT NOT NULL REFERENCES curated.dim_race(race_id) ON DELETE CASCADE,
    driver_id TEXT NOT NULL REFERENCES curated.dim_driver(driver_id),
    stint INTEGER NOT NULL,
    start_lap INTEGER NOT NULL,
    end_lap INTEGER NOT NULL,
    compound TEXT,
    stint_laps INTEGER NOT NULL,
    median_lap_ms BIGINT,
    avg_lap_ms BIGINT,
    pit_lap INTEGER,
    PRIMARY KEY (race_id, driver_id, stint)
);

CREATE INDEX IF NOT EXISTS idx_mart_stint_race_driver
    ON marts.mart_stint_summary (race_id, driver_id);
