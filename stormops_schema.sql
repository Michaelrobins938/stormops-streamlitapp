-- StormOps v1 Database Schema
-- PostgreSQL + PostGIS

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;

-- Events: Storm events (DFW Storm 24, etc.)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    event_date TIMESTAMP NOT NULL,
    peak_hail_inches FLOAT,
    max_wind_mph FLOAT,
    estimated_value_usd FLOAT,
    earth2_swath_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active', -- active, closed, archived
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Parcels: Individual roofs/properties in DFW
CREATE TABLE parcels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id VARCHAR(255) UNIQUE NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    address VARCHAR(500),
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    roof_material VARCHAR(100), -- asphalt, metal, tile, etc.
    roof_age_years INT,
    estimated_value_usd FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_parcels_zip ON parcels(zip_code);
CREATE INDEX idx_parcels_geometry ON parcels USING GIST(geometry);

-- Impact Scores: SII (StormOps Impact Index) per parcel per event
CREATE TABLE impact_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    parcel_id UUID NOT NULL REFERENCES parcels(id),
    hail_intensity_mm FLOAT,
    sii_score FLOAT NOT NULL, -- 0-100
    damage_probability FLOAT, -- 0-1
    estimated_claim_value_usd FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parcel_id)
);

CREATE INDEX idx_impact_scores_event ON impact_scores(event_id);
CREATE INDEX idx_impact_scores_sii ON impact_scores(sii_score DESC);

-- Sectors: Geographic groupings (blocks, neighborhoods)
CREATE TABLE sectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sectors_zip ON sectors(zip_code);
CREATE INDEX idx_sectors_geometry ON sectors USING GIST(geometry);

-- Leads: Generated leads from event + SII scoring
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    parcel_id UUID NOT NULL REFERENCES parcels(id),
    crm_lead_id VARCHAR(255), -- ServiceTitan/JobNimbus lead ID
    sii_score FLOAT NOT NULL,
    lead_status VARCHAR(50) DEFAULT 'new', -- new, contacted, inspected, quoted, closed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parcel_id)
);

CREATE INDEX idx_leads_event ON leads(event_id);
CREATE INDEX idx_leads_status ON leads(lead_status);
CREATE INDEX idx_leads_sii ON leads(sii_score DESC);

-- Routes: Canvassing routes for field reps
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    route_name VARCHAR(255) NOT NULL,
    canvasser_id VARCHAR(255), -- Field rep identifier
    geometry GEOMETRY(LINESTRING, 4326),
    parcel_count INT,
    estimated_duration_minutes INT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, active, completed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_routes_event ON routes(event_id);
CREATE INDEX idx_routes_status ON routes(status);

-- Route parcels: Many-to-many between routes and parcels
CREATE TABLE route_parcels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_id UUID NOT NULL REFERENCES routes(id),
    parcel_id UUID NOT NULL REFERENCES parcels(id),
    sequence_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(route_id, parcel_id)
);

-- Proposals: Executable actions (lead gen, route build, SMS campaign)
CREATE TABLE proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    proposal_type VARCHAR(100) NOT NULL, -- lead_gen, route_build, sms_campaign, impact_report
    target_zip VARCHAR(10),
    target_sii_min FLOAT,
    target_sii_max FLOAT,
    expected_leads INT,
    expected_value_usd FLOAT,
    blast_radius INT, -- number of parcels affected
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected, executed
    created_at TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP,
    created_by VARCHAR(255),
    approved_by VARCHAR(255)
);

CREATE INDEX idx_proposals_event ON proposals(event_id);
CREATE INDEX idx_proposals_status ON proposals(status);

-- MOE State: Markov Opportunity Engine state per sector per event
CREATE TABLE moe_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    sector_id UUID NOT NULL REFERENCES sectors(id),
    state VARCHAR(50) NOT NULL, -- baseline, risk, impact, recovery
    state_probability FLOAT, -- 0-1
    expected_claim_count INT,
    expected_claim_value_usd FLOAT,
    recommended_canvassers INT,
    surge_multiplier FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, sector_id)
);

CREATE INDEX idx_moe_state_event ON moe_state(event_id);
CREATE INDEX idx_moe_state_sector ON moe_state(sector_id);

-- Impact Reports: Pre-built physics-backed reports
CREATE TABLE impact_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    parcel_id UUID NOT NULL REFERENCES parcels(id),
    hail_size_inches FLOAT,
    damage_probability FLOAT,
    estimated_claim_value_usd FLOAT,
    report_json JSONB, -- Full report data
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, parcel_id)
);

CREATE INDEX idx_impact_reports_event ON impact_reports(event_id);

-- CRM Sync Log: Track all CRM operations
CREATE TABLE crm_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id),
    operation_type VARCHAR(100), -- create_lead, update_job, push_route
    crm_entity_id VARCHAR(255),
    status VARCHAR(50), -- success, failed, pending
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_crm_sync_log_event ON crm_sync_log(event_id);
CREATE INDEX idx_crm_sync_log_status ON crm_sync_log(status);
