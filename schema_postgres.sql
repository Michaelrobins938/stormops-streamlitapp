-- StormOps Multi-Tenant Schema with Row-Level Security
-- Postgres 14+

-- ============================================================================
-- TENANTING & AUTH
-- ============================================================================

CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'churned')),
    tier TEXT NOT NULL DEFAULT 'standard' CHECK (tier IN ('trial', 'standard', 'enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'crew_chief', 'field_user', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant ON users(tenant_id);

-- Session context for RLS
CREATE TABLE rls_context (
    session_id TEXT PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    set_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- CORE STORM DATA
-- ============================================================================

CREATE TABLE storms (
    storm_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    event_id TEXT NOT NULL,
    name TEXT NOT NULL,
    county TEXT,
    state TEXT,
    magnitude FLOAT,
    begin_datetime TIMESTAMPTZ,
    end_datetime TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('planning', 'active', 'completed', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, event_id)
);

CREATE INDEX idx_storms_tenant ON storms(tenant_id);
CREATE INDEX idx_storms_status ON storms(tenant_id, status);

ALTER TABLE storms ENABLE ROW LEVEL SECURITY;

CREATE POLICY storms_tenant_isolation ON storms
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- ============================================================================
-- PROPERTIES & JOURNEYS
-- ============================================================================

CREATE TABLE properties (
    property_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    external_id TEXT NOT NULL,
    address TEXT,
    zip_code TEXT,
    latitude FLOAT,
    longitude FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, external_id)
);

CREATE INDEX idx_properties_tenant ON properties(tenant_id);
CREATE INDEX idx_properties_zip ON properties(tenant_id, zip_code);

ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

CREATE POLICY properties_tenant_isolation ON properties
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE TABLE customer_journeys (
    journey_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    property_id UUID NOT NULL REFERENCES properties(property_id),
    channel TEXT NOT NULL,
    play_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    converted BOOLEAN NOT NULL DEFAULT FALSE,
    conversion_value FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_journeys_tenant ON customer_journeys(tenant_id);
CREATE INDEX idx_journeys_storm ON customer_journeys(tenant_id, storm_id);
CREATE INDEX idx_journeys_property ON customer_journeys(property_id);

ALTER TABLE customer_journeys ENABLE ROW LEVEL SECURITY;

CREATE POLICY journeys_tenant_isolation ON customer_journeys
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- ============================================================================
-- UPLIFT & EXPERIMENTS
-- ============================================================================

CREATE TABLE lead_uplift (
    uplift_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    property_id UUID NOT NULL REFERENCES properties(property_id),
    expected_uplift FLOAT NOT NULL,
    next_best_action TEXT,
    model_version TEXT NOT NULL,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, storm_id, property_id)
);

CREATE INDEX idx_uplift_tenant ON lead_uplift(tenant_id);
CREATE INDEX idx_uplift_storm ON lead_uplift(tenant_id, storm_id);

ALTER TABLE lead_uplift ENABLE ROW LEVEL SECURITY;

CREATE POLICY uplift_tenant_isolation ON lead_uplift
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE TABLE experiments (
    experiment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    name TEXT NOT NULL,
    hypothesis TEXT,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('draft', 'running', 'completed', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, storm_id, name)
);

CREATE INDEX idx_experiments_tenant ON experiments(tenant_id);

ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;

CREATE POLICY experiments_tenant_isolation ON experiments
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE TABLE experiment_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    experiment_id UUID NOT NULL REFERENCES experiments(experiment_id),
    property_id UUID NOT NULL REFERENCES properties(property_id),
    variant TEXT NOT NULL CHECK (variant IN ('treatment', 'control')),
    universal_control BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, experiment_id, property_id)
);

CREATE INDEX idx_assignments_tenant ON experiment_assignments(tenant_id);
CREATE INDEX idx_assignments_experiment ON experiment_assignments(experiment_id);

ALTER TABLE experiment_assignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY assignments_tenant_isolation ON experiment_assignments
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- ============================================================================
-- POLICY DECISIONS & OUTCOMES
-- ============================================================================

CREATE TABLE policy_decisions_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    property_id UUID NOT NULL REFERENCES properties(property_id),
    decision TEXT NOT NULL CHECK (decision IN ('treat', 'hold')),
    reason TEXT NOT NULL,
    expected_uplift FLOAT,
    uplift_band TEXT,
    policy_mode TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_policy_log_tenant ON policy_decisions_log(tenant_id);
CREATE INDEX idx_policy_log_storm ON policy_decisions_log(tenant_id, storm_id);

ALTER TABLE policy_decisions_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY policy_log_tenant_isolation ON policy_decisions_log
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE TABLE policy_outcomes (
    outcome_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    property_id UUID NOT NULL REFERENCES properties(property_id),
    decision TEXT NOT NULL,
    expected_uplift FLOAT,
    actual_converted BOOLEAN NOT NULL,
    conversion_value FLOAT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, storm_id, property_id)
);

CREATE INDEX idx_outcomes_tenant ON policy_outcomes(tenant_id);
CREATE INDEX idx_outcomes_storm ON policy_outcomes(tenant_id, storm_id);

ALTER TABLE policy_outcomes ENABLE ROW LEVEL SECURITY;

CREATE POLICY outcomes_tenant_isolation ON policy_outcomes
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- ============================================================================
-- ATTRIBUTION
-- ============================================================================

CREATE TABLE channel_attribution (
    attribution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    zip_code TEXT,
    channel TEXT NOT NULL,
    credit FLOAT NOT NULL,
    total_journeys INT NOT NULL,
    conversions INT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_channel_attr_tenant ON channel_attribution(tenant_id);
CREATE INDEX idx_channel_attr_storm ON channel_attribution(tenant_id, storm_id);

ALTER TABLE channel_attribution ENABLE ROW LEVEL SECURITY;

CREATE POLICY channel_attr_tenant_isolation ON channel_attribution
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- ============================================================================
-- METERING & OBSERVABILITY
-- ============================================================================

CREATE TABLE tenant_usage (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    dimensions JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_tenant ON tenant_usage(tenant_id);
CREATE INDEX idx_usage_time ON tenant_usage(timestamp);

ALTER TABLE tenant_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY usage_tenant_isolation ON tenant_usage
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE TABLE data_quality_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    table_name TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    threshold_breached BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dq_tenant ON data_quality_metrics(tenant_id);
CREATE INDEX idx_dq_time ON data_quality_metrics(timestamp);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Set tenant context for session
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id UUID)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_tenant', p_tenant_id::TEXT, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Get current tenant
CREATE OR REPLACE FUNCTION current_tenant()
RETURNS UUID AS $$
BEGIN
    RETURN current_setting('app.current_tenant', TRUE)::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Create system tenant for testing
INSERT INTO tenants (tenant_id, org_name, tier)
VALUES ('00000000-0000-0000-0000-000000000000', 'System', 'enterprise');

-- Create test tenant
INSERT INTO tenants (org_name, tier)
VALUES ('DFW Elite Roofing', 'standard')
RETURNING tenant_id;
