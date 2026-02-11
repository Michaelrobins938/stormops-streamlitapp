-- Raw ingestion tables for public data sources

-- NOAA Storm Events
CREATE TABLE IF NOT EXISTS storm_events_raw (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(100),
    event_date TIMESTAMP,
    state VARCHAR(50),
    county VARCHAR(100),
    lat FLOAT,
    lon FLOAT,
    hail_size_mm FLOAT,
    damage_cost FLOAT,
    source VARCHAR(100),
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_storm_events_raw_date ON storm_events_raw(event_date);
CREATE INDEX idx_storm_events_raw_type ON storm_events_raw(event_type);
CREATE INDEX idx_storm_events_raw_state ON storm_events_raw(state);

-- Open-Meteo Forecasts
CREATE TABLE IF NOT EXISTS sector_forecasts_raw (
    id SERIAL PRIMARY KEY,
    sector_id VARCHAR(255),
    forecast_time TIMESTAMP,
    precip_mm FLOAT,
    wind_gust_ms FLOAT,
    cape FLOAT,
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(sector_id, forecast_time)
);

CREATE INDEX idx_sector_forecasts_raw_sector ON sector_forecasts_raw(sector_id);
CREATE INDEX idx_sector_forecasts_raw_time ON sector_forecasts_raw(forecast_time);

-- NWS Alerts
CREATE TABLE IF NOT EXISTS weather_alerts_raw (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(100),
    headline TEXT,
    description TEXT,
    effective TIMESTAMP,
    expires TIMESTAMP,
    severity VARCHAR(50),
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_weather_alerts_raw_type ON weather_alerts_raw(event_type);
CREATE INDEX idx_weather_alerts_raw_expires ON weather_alerts_raw(expires);

-- FEMA Hailstorms
CREATE TABLE IF NOT EXISTS hail_footprints_raw (
    id SERIAL PRIMARY KEY,
    hail_id VARCHAR(255) UNIQUE,
    event_date TIMESTAMP,
    severity VARCHAR(50),
    source VARCHAR(100),
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hail_footprints_raw_date ON hail_footprints_raw(event_date);

-- Normalized tables (from raw)

-- Normalized storm events
CREATE TABLE IF NOT EXISTS storm_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(100),
    event_date TIMESTAMP,
    state VARCHAR(50),
    county VARCHAR(100),
    lat FLOAT,
    lon FLOAT,
    hail_size_mm FLOAT,
    damage_cost FLOAT,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Normalized forecasts
CREATE TABLE IF NOT EXISTS sector_forecasts (
    id SERIAL PRIMARY KEY,
    sector_id VARCHAR(255),
    forecast_time TIMESTAMP,
    precip_mm FLOAT,
    wind_gust_ms FLOAT,
    cape FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(sector_id, forecast_time)
);

-- Normalized alerts
CREATE TABLE IF NOT EXISTS weather_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(100),
    headline TEXT,
    description TEXT,
    effective TIMESTAMP,
    expires TIMESTAMP,
    severity VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Normalized hail footprints
CREATE TABLE IF NOT EXISTS hail_footprints (
    id SERIAL PRIMARY KEY,
    hail_id VARCHAR(255) UNIQUE,
    event_date TIMESTAMP,
    severity VARCHAR(50),
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ingestion job tracking
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(255),
    source VARCHAR(100),
    status VARCHAR(50),
    records_processed INT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_ingestion_jobs_name ON ingestion_jobs(job_name);
CREATE INDEX idx_ingestion_jobs_status ON ingestion_jobs(status);
