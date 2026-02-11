-- StormOps v2: NVIDIA Earth-2 + Markov + Identity Resolution + Agentic Sidebar
-- Extension of existing schema with new control plane features

-- Enable PostGIS for spatial queries
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- 1. EARTH-2 INTEGRATION: Storm Impact Zones
-- ============================================================================

CREATE TABLE earth2_impact_zones (
    zone_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    
    -- Spatial data
    polygon GEOMETRY(POLYGON, 4326) NOT NULL,
    center_lat DECIMAL(10, 7),
    center_lon DECIMAL(10, 7),
    
    -- Earth-2 physics data
    hail_size_inches DECIMAL(4, 2),
    terminal_velocity_ms DECIMAL(6, 2),
    kinetic_energy_j DECIMAL(10, 2),
    wind_speed_mph DECIMAL(6, 2),
    
    -- Damage modeling
    damage_propensity_score DECIMAL(5, 4), -- 0-1 score
    resolution_km DECIMAL(4, 2) DEFAULT 1.0,
    
    -- Metadata
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(50) DEFAULT 'earth2_corrdiff',
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT fk_storm FOREIGN KEY (storm_id) REFERENCES storms(storm_id)
);

CREATE INDEX idx_earth2_zones_spatial ON earth2_impact_zones USING GIST(polygon);
CREATE INDEX idx_earth2_zones_storm ON earth2_impact_zones(storm_id);
CREATE INDEX idx_earth2_zones_score ON earth2_impact_zones(damage_propensity_score DESC);

-- ============================================================================
-- 2. MARKOV STATE ENGINE: ZIP-Level Opportunity Windows
-- ============================================================================

CREATE TYPE markov_state AS ENUM ('baseline', 'pre_impact', 'impact', 'recovery');

CREATE TABLE markov_zip_states (
    state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    
    zip_code VARCHAR(10) NOT NULL,
    current_state markov_state NOT NULL DEFAULT 'baseline',
    
    -- Transition probabilities
    prob_to_baseline DECIMAL(5, 4) DEFAULT 0,
    prob_to_pre_impact DECIMAL(5, 4) DEFAULT 0,
    prob_to_impact DECIMAL(5, 4) DEFAULT 0,
    prob_to_recovery DECIMAL(5, 4) DEFAULT 0,
    
    -- Business metrics
    estimated_tam_usd DECIMAL(12, 2),
    lead_velocity_24h INT DEFAULT 0,
    saturation_score DECIMAL(5, 4), -- Hill function output
    
    -- Timestamps
    state_entered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT fk_storm FOREIGN KEY (storm_id) REFERENCES storms(storm_id)
);

CREATE INDEX idx_markov_zip_storm ON markov_zip_states(storm_id, zip_code);
CREATE INDEX idx_markov_state ON markov_zip_states(current_state);

-- Transition history log
CREATE TABLE markov_transitions (
    transition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_id UUID NOT NULL REFERENCES markov_zip_states(state_id),
    
    from_state markov_state NOT NULL,
    to_state markov_state NOT NULL,
    
    transition_probability DECIMAL(5, 4),
    trigger_event VARCHAR(100), -- e.g., 'earth2_hail_detected'
    
    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transitions_state ON markov_transitions(state_id);

-- ============================================================================
-- 3. IDENTITY RESOLUTION: Golden Property Identity
-- ============================================================================

CREATE TABLE property_identities (
    identity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    
    -- Golden record
    property_id UUID NOT NULL, -- Links to properties table
    
    -- Probabilistic matching
    confidence_score DECIMAL(5, 4), -- Brier score
    resolution_method VARCHAR(50), -- 'exact', 'fuzzy', 'behavioral'
    
    -- Household graph
    household_id UUID,
    decision_maker_name VARCHAR(255),
    decision_maker_email VARCHAR(255),
    decision_maker_phone VARCHAR(20),
    
    -- Behavioral fingerprint
    web_sessions INT DEFAULT 0,
    form_submissions INT DEFAULT 0,
    call_attempts INT DEFAULT 0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
);

CREATE INDEX idx_identity_property ON property_identities(property_id);
CREATE INDEX idx_identity_household ON property_identities(household_id);
CREATE INDEX idx_identity_confidence ON property_identities(confidence_score DESC);

-- Identity linkage (many-to-one)
CREATE TABLE identity_signals (
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES property_identities(identity_id),
    
    signal_type VARCHAR(50), -- 'email', 'phone', 'address', 'cookie'
    signal_value TEXT,
    signal_hash VARCHAR(64), -- SHA-256
    
    match_weight DECIMAL(5, 4),
    
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signals_identity ON identity_signals(identity_id);
CREATE INDEX idx_signals_hash ON identity_signals(signal_hash);

-- ============================================================================
-- 4. AGENTIC SIDEBAR: Action Queue
-- ============================================================================

CREATE TYPE action_status AS ENUM ('proposed', 'approved', 'executing', 'completed', 'failed', 'rejected');
CREATE TYPE action_type AS ENUM ('load_swath', 'generate_routes', 'launch_sms', 'dispatch_rep', 'sync_crm', 'calculate_tam');

CREATE TABLE sidebar_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    
    action_type action_type NOT NULL,
    action_status action_status NOT NULL DEFAULT 'proposed',
    
    -- AI reasoning
    ai_confidence DECIMAL(5, 4),
    ai_reasoning TEXT,
    
    -- Action payload
    action_params JSONB, -- e.g., {"zip_code": "75024", "max_properties": 50}
    
    -- Execution tracking
    proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Results
    result_summary JSONB,
    error_message TEXT,
    
    -- User interaction
    approved_by VARCHAR(255),
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT fk_storm FOREIGN KEY (storm_id) REFERENCES storms(storm_id)
);

CREATE INDEX idx_sidebar_storm ON sidebar_actions(storm_id);
CREATE INDEX idx_sidebar_status ON sidebar_actions(action_status);
CREATE INDEX idx_sidebar_proposed ON sidebar_actions(proposed_at DESC);

-- ============================================================================
-- 5. OPERATIONAL SCORE: Real-time Readiness Metric
-- ============================================================================

CREATE TABLE operational_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    
    -- Score components (0-100)
    total_score INT NOT NULL,
    
    validated_leads_score INT,
    route_efficiency_score INT,
    sla_compliance_score INT,
    
    -- Gap analysis
    gap_to_100 INT,
    next_best_action action_type,
    estimated_points_gain INT,
    
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT fk_storm FOREIGN KEY (storm_id) REFERENCES storms(storm_id)
);

CREATE INDEX idx_opscore_storm ON operational_scores(storm_id);
CREATE INDEX idx_opscore_time ON operational_scores(calculated_at DESC);

-- ============================================================================
-- 6. SYSTEM VITALITY: Connection Health
-- ============================================================================

CREATE TYPE connection_status AS ENUM ('healthy', 'degraded', 'failed');

CREATE TABLE system_vitality (
    vitality_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    
    service_name VARCHAR(100) NOT NULL, -- 'earth2', 'servicetitan', 'jobnimbus'
    status connection_status NOT NULL DEFAULT 'healthy',
    
    latency_ms INT,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    failure_count_24h INT DEFAULT 0,
    
    health_check_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
);

CREATE INDEX idx_vitality_tenant ON system_vitality(tenant_id);
CREATE INDEX idx_vitality_service ON system_vitality(service_name);

-- ============================================================================
-- VIEWS: Simplified queries for UI
-- ============================================================================

-- Property damage enrichment
CREATE OR REPLACE VIEW v_property_damage_intel AS
SELECT 
    p.property_id,
    p.tenant_id,
    p.address,
    p.zip_code,
    ez.hail_size_inches,
    ez.terminal_velocity_ms,
    ez.damage_propensity_score,
    mz.current_state AS zip_state,
    mz.estimated_tam_usd AS zip_tam,
    pi.confidence_score AS identity_confidence,
    pi.decision_maker_name
FROM properties p
LEFT JOIN earth2_impact_zones ez ON ST_Contains(ez.polygon, ST_SetSRID(ST_MakePoint(p.longitude, p.latitude), 4326))
LEFT JOIN markov_zip_states mz ON p.zip_code = mz.zip_code AND p.tenant_id = mz.tenant_id
LEFT JOIN property_identities pi ON p.property_id = pi.property_id;

-- Sidebar action queue (for UI)
CREATE OR REPLACE VIEW v_sidebar_queue AS
SELECT 
    sa.action_id,
    sa.storm_id,
    sa.action_type,
    sa.action_status,
    sa.ai_confidence,
    sa.ai_reasoning,
    sa.action_params,
    sa.proposed_at,
    s.name AS storm_name
FROM sidebar_actions sa
JOIN storms s ON sa.storm_id = s.storm_id
WHERE sa.action_status IN ('proposed', 'approved', 'executing')
ORDER BY sa.ai_confidence DESC, sa.proposed_at ASC;

-- ============================================================================
-- FUNCTIONS: Core business logic
-- ============================================================================

-- Calculate damage propensity score
CREATE OR REPLACE FUNCTION calculate_damage_propensity(
    p_terminal_velocity DECIMAL,
    p_material_coefficient DECIMAL,
    p_roof_age INT
) RETURNS DECIMAL AS $$
BEGIN
    RETURN LEAST(1.0, (p_terminal_velocity * p_material_coefficient + p_roof_age * 0.01));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Update Markov state with transition
CREATE OR REPLACE FUNCTION transition_markov_state(
    p_state_id UUID,
    p_new_state markov_state,
    p_trigger_event VARCHAR
) RETURNS VOID AS $$
DECLARE
    v_old_state markov_state;
BEGIN
    -- Get current state
    SELECT current_state INTO v_old_state
    FROM markov_zip_states
    WHERE state_id = p_state_id;
    
    -- Log transition
    INSERT INTO markov_transitions (state_id, from_state, to_state, trigger_event)
    VALUES (p_state_id, v_old_state, p_new_state, p_trigger_event);
    
    -- Update state
    UPDATE markov_zip_states
    SET current_state = p_new_state,
        state_entered_at = NOW(),
        last_updated_at = NOW()
    WHERE state_id = p_state_id;
END;
$$ LANGUAGE plpgsql;

-- Calculate operational score
CREATE OR REPLACE FUNCTION calculate_operational_score(
    p_tenant_id UUID,
    p_storm_id UUID
) RETURNS INT AS $$
DECLARE
    v_leads_score INT;
    v_route_score INT;
    v_sla_score INT;
    v_total INT;
BEGIN
    -- Validated leads (40%)
    SELECT COALESCE(COUNT(*) * 40 / NULLIF((SELECT COUNT(*) FROM properties WHERE tenant_id = p_tenant_id), 0), 0)
    INTO v_leads_score
    FROM policy_decisions_log
    WHERE storm_id = p_storm_id AND decision = 'treat';
    
    -- Route efficiency (30%)
    SELECT COALESCE(COUNT(*) * 30 / NULLIF((SELECT COUNT(*) FROM policy_decisions_log WHERE storm_id = p_storm_id AND decision = 'treat'), 0), 0)
    INTO v_route_score
    FROM routes
    WHERE storm_id = p_storm_id AND status = 'assigned';
    
    -- SLA compliance (30%)
    v_sla_score := 30; -- Placeholder
    
    v_total := LEAST(100, v_leads_score + v_route_score + v_sla_score);
    
    -- Insert score
    INSERT INTO operational_scores (tenant_id, storm_id, total_score, validated_leads_score, route_efficiency_score, sla_compliance_score, gap_to_100)
    VALUES (p_tenant_id, p_storm_id, v_total, v_leads_score, v_route_score, v_sla_score, 100 - v_total);
    
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO stormops;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO stormops;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO stormops;
