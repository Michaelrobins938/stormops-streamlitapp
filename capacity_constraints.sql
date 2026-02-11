-- Capacity and constraints tables

-- Field rep availability and territory
CREATE TABLE IF NOT EXISTS field_reps (
    id SERIAL PRIMARY KEY,
    rep_id VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    territory VARCHAR(255),
    max_daily_stops INT DEFAULT 50,
    avg_stop_duration_minutes INT DEFAULT 30,
    available_hours_per_day INT DEFAULT 8,
    status VARCHAR(50) DEFAULT 'available',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_field_reps_territory ON field_reps(territory);
CREATE INDEX idx_field_reps_status ON field_reps(status);

-- Rep daily capacity tracking
CREATE TABLE IF NOT EXISTS rep_daily_capacity (
    id SERIAL PRIMARY KEY,
    rep_id VARCHAR(255),
    event_date DATE,
    max_stops INT,
    assigned_stops INT DEFAULT 0,
    completed_stops INT DEFAULT 0,
    available_capacity INT,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(rep_id, event_date)
);

CREATE INDEX idx_rep_daily_capacity_date ON rep_daily_capacity(event_date);

-- Territory definitions
CREATE TABLE IF NOT EXISTS territories (
    id SERIAL PRIMARY KEY,
    territory_id VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    geometry GEOMETRY(POLYGON, 4326),
    zip_codes TEXT[],
    max_daily_leads INT DEFAULT 500,
    saturation_threshold FLOAT DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_territories_geometry ON territories USING GIST(geometry);

-- Neighborhood saturation tracking
CREATE TABLE IF NOT EXISTS neighborhood_saturation (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    neighborhood_id VARCHAR(255),
    total_parcels INT,
    contacted_parcels INT,
    saturation_ratio FLOAT,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, neighborhood_id)
);

-- Lead conversion tracking (for feedback loop)
CREATE TABLE IF NOT EXISTS lead_outcomes (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    parcel_id VARCHAR(255),
    lead_id VARCHAR(255),
    sii_score_predicted FLOAT,
    lead_status VARCHAR(50),
    contacted_at TIMESTAMP,
    inspected_at TIMESTAMP,
    quoted_at TIMESTAMP,
    job_created_at TIMESTAMP,
    job_amount_usd FLOAT,
    claim_filed_at TIMESTAMP,
    claim_amount_usd FLOAT,
    claim_accepted BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parcel_id)
);

CREATE INDEX idx_lead_outcomes_event ON lead_outcomes(event_id);
CREATE INDEX idx_lead_outcomes_status ON lead_outcomes(lead_status);

-- Economics and profitability
CREATE TABLE IF NOT EXISTS parcel_economics (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    parcel_id VARCHAR(255),
    sii_score FLOAT,
    estimated_claim_value_usd FLOAT,
    estimated_margin_pct FLOAT DEFAULT 0.15,
    estimated_profit_usd FLOAT,
    cac_budget_usd FLOAT,
    roi_ratio FLOAT,
    priority_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parcel_id)
);

CREATE INDEX idx_parcel_economics_priority ON parcel_economics(priority_score DESC);

-- Governance and compliance rules
CREATE TABLE IF NOT EXISTS governance_rules (
    id SERIAL PRIMARY KEY,
    rule_type VARCHAR(100),
    rule_name VARCHAR(255),
    description TEXT,
    constraint_type VARCHAR(50),
    constraint_value VARCHAR(255),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- TCPA compliance tracking
CREATE TABLE IF NOT EXISTS tcpa_compliance (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20),
    event_id VARCHAR(255),
    sms_sent_at TIMESTAMP,
    sms_count_24h INT,
    sms_count_7d INT,
    opted_out BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tcpa_compliance_phone ON tcpa_compliance(phone_number);
