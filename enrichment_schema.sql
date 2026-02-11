-- Enriched parcel and roof attributes

-- Roof attributes (from permits, appraisals, TxGIO)
CREATE TABLE IF NOT EXISTS roof_attributes (
    id SERIAL PRIMARY KEY,
    parcel_id VARCHAR(255) UNIQUE,
    roof_material VARCHAR(100),
    roof_age_years INT,
    roof_area_sqft INT,
    roof_complexity VARCHAR(50),
    last_permit_date DATE,
    permit_type VARCHAR(100),
    estimated_replacement_cost_usd FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_roof_attributes_material ON roof_attributes(roof_material);
CREATE INDEX idx_roof_attributes_age ON roof_attributes(roof_age_years);

-- Building use and value
CREATE TABLE IF NOT EXISTS property_attributes (
    id SERIAL PRIMARY KEY,
    parcel_id VARCHAR(255) UNIQUE,
    building_use VARCHAR(100),
    owner_occupied BOOLEAN,
    assessed_value_usd FLOAT,
    value_band VARCHAR(50),
    units INT,
    year_built INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_property_attributes_use ON property_attributes(building_use);
CREATE INDEX idx_property_attributes_value ON property_attributes(value_band);

-- Rep productivity and availability
CREATE TABLE IF NOT EXISTS rep_productivity (
    id SERIAL PRIMARY KEY,
    rep_id VARCHAR(255),
    event_id VARCHAR(255),
    inspections_completed INT,
    estimates_sent INT,
    jobs_sold INT,
    avg_revenue_per_inspection_usd FLOAT,
    close_rate FLOAT,
    no_show_rate FLOAT,
    avg_stop_duration_minutes INT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(rep_id, event_id)
);

CREATE INDEX idx_rep_productivity_rep ON rep_productivity(rep_id);

-- Rep availability calendar
CREATE TABLE IF NOT EXISTS rep_availability (
    id SERIAL PRIMARY KEY,
    rep_id VARCHAR(255),
    date DATE,
    available_hours INT,
    scheduled_hours INT,
    overtime_allowed BOOLEAN,
    home_base_lat FLOAT,
    home_base_lon FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(rep_id, date)
);

CREATE INDEX idx_rep_availability_date ON rep_availability(date);

-- Channel performance (SMS vs phone vs door-knock)
CREATE TABLE IF NOT EXISTS channel_performance (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    channel VARCHAR(50),
    severity_band VARCHAR(50),
    contacts_sent INT,
    responses INT,
    appointments_set INT,
    conversion_rate FLOAT,
    unsubscribe_rate FLOAT,
    complaint_rate FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, channel, severity_band)
);

CREATE INDEX idx_channel_performance_event ON channel_performance(event_id);

-- Response timing curves (decay over time)
CREATE TABLE IF NOT EXISTS response_timing (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    severity_band VARCHAR(50),
    hours_since_hail INT,
    conversion_rate FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, severity_band, hours_since_hail)
);

CREATE INDEX idx_response_timing_event ON response_timing(event_id);

-- External enrichment data (flood zones, wildfire, income, etc.)
CREATE TABLE IF NOT EXISTS external_enrichment (
    id SERIAL PRIMARY KEY,
    parcel_id VARCHAR(255) UNIQUE,
    flood_zone VARCHAR(50),
    wildfire_risk_score FLOAT,
    neighborhood_income_band VARCHAR(50),
    credit_proxy_score FLOAT,
    competitor_permit_count_12m INT,
    google_review_burst_30d INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_external_enrichment_flood ON external_enrichment(flood_zone);
CREATE INDEX idx_external_enrichment_wildfire ON external_enrichment(wildfire_risk_score);

-- Lifecycle tracking (lead → paid)
CREATE TABLE IF NOT EXISTS lifecycle_tracking (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    parcel_id VARCHAR(255),
    lead_id VARCHAR(255),
    stage VARCHAR(50),
    stage_timestamp TIMESTAMP,
    rep_id VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parcel_id, stage)
);

CREATE INDEX idx_lifecycle_tracking_event ON lifecycle_tracking(event_id);
CREATE INDEX idx_lifecycle_tracking_stage ON lifecycle_tracking(stage);

-- Economics per lifecycle stage
CREATE TABLE IF NOT EXISTS stage_economics (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    stage VARCHAR(50),
    count INT,
    avg_ticket_usd FLOAT,
    close_rate FLOAT,
    gross_margin_pct FLOAT,
    cancel_rate FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, stage)
);

CREATE INDEX idx_stage_economics_event ON stage_economics(event_id);
