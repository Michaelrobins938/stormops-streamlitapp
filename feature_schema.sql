-- Feature engineering tables

-- Sector-level features (MOE inputs)
CREATE TABLE IF NOT EXISTS sector_features (
    id SERIAL PRIMARY KEY,
    sector_id VARCHAR(255),
    event_id VARCHAR(255),
    hail_intensity_avg_mm FLOAT,
    hail_intensity_max_mm FLOAT,
    wind_gust_max_ms FLOAT,
    cape_avg FLOAT,
    alert_count INT,
    alert_severity VARCHAR(50),
    parcel_count INT,
    moe_state VARCHAR(50),
    computed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(sector_id, event_id)
);

CREATE INDEX idx_sector_features_event ON sector_features(event_id);
CREATE INDEX idx_sector_features_state ON sector_features(moe_state);

-- Parcel-level impacts (SII scores)
CREATE TABLE IF NOT EXISTS parcel_impacts (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    parcel_id VARCHAR(255),
    hail_intensity_mm FLOAT,
    sii_score FLOAT,
    damage_probability FLOAT,
    computed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parcel_id)
);

CREATE INDEX idx_parcel_impacts_event ON parcel_impacts(event_id);
CREATE INDEX idx_parcel_impacts_sii ON parcel_impacts(sii_score DESC);

-- Trigger execution log
CREATE TABLE IF NOT EXISTS trigger_log (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    sector_id VARCHAR(255),
    trigger_type VARCHAR(100),
    proposal_id VARCHAR(255),
    triggered_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trigger_log_event ON trigger_log(event_id);
CREATE INDEX idx_trigger_log_type ON trigger_log(trigger_type);
