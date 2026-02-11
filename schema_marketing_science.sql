-- StormOps v2.1: Marketing Science Extensions
-- Hybrid Attribution, Bayesian MMM, Probabilistic Identity

-- ============================================================================
-- 1. HYBRID ATTRIBUTION: Markov-Shapley Framework
-- ============================================================================

CREATE TABLE attribution_touchpoints (
    touchpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    property_id UUID NOT NULL,
    
    -- Touchpoint data
    channel VARCHAR(50) NOT NULL, -- 'earth2_alert', 'door_knock', 'sms', 'web_form', 'call'
    touchpoint_timestamp TIMESTAMPTZ NOT NULL,
    touchpoint_order INT, -- Position in journey
    
    -- Attribution weights
    markov_credit DECIMAL(8, 6), -- Removal effect contribution
    shapley_credit DECIMAL(8, 6), -- Axiomatic fair credit
    hybrid_credit DECIMAL(8, 6), -- α-weighted combination
    
    -- Context
    rep_id VARCHAR(100),
    campaign_id UUID,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attribution_property ON attribution_touchpoints(property_id);
CREATE INDEX idx_attribution_channel ON attribution_touchpoints(channel);
CREATE INDEX idx_attribution_storm ON attribution_touchpoints(storm_id);

-- Journey table (sequences of touchpoints)
CREATE TABLE customer_journeys_v2 (
    journey_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    property_id UUID NOT NULL,
    identity_id UUID REFERENCES property_identities(identity_id),
    
    -- Journey path
    touchpoint_sequence TEXT[], -- ['earth2_alert', 'door_knock', 'web_form', 'call']
    journey_length INT,
    
    -- Outcome
    converted BOOLEAN DEFAULT FALSE,
    conversion_timestamp TIMESTAMPTZ,
    contract_value_usd DECIMAL(10, 2),
    
    -- Causal metrics
    uplift_score DECIMAL(5, 4), -- T-Learner estimated uplift
    removal_effect DECIMAL(5, 4), -- Markov removal effect
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_journeys_v2_property ON customer_journeys_v2(property_id);
CREATE INDEX idx_journeys_v2_identity ON customer_journeys_v2(identity_id);
CREATE INDEX idx_journeys_v2_converted ON customer_journeys_v2(converted);

-- ============================================================================
-- 2. BAYESIAN MMM: Media Mix Modeling
-- ============================================================================

CREATE TABLE mmm_channels (
    channel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    
    channel_name VARCHAR(50) NOT NULL, -- 'door_knock', 'sms', 'google_ads', 'facebook'
    channel_type VARCHAR(20), -- 'offline', 'digital'
    
    -- Adstock parameters (Weibull decay)
    adstock_alpha DECIMAL(5, 4) DEFAULT 0.5, -- Shape parameter
    adstock_theta DECIMAL(5, 4) DEFAULT 0.3, -- Decay rate
    
    -- Saturation parameters (Hill function)
    saturation_k DECIMAL(10, 2), -- Half-saturation point
    saturation_s DECIMAL(5, 4) DEFAULT 1.0, -- Slope
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mmm_channels_tenant ON mmm_channels(tenant_id);

-- Spend and response data
CREATE TABLE mmm_observations (
    observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    channel_id UUID NOT NULL REFERENCES mmm_channels(channel_id),
    
    observation_date DATE NOT NULL,
    zip_code VARCHAR(10),
    
    -- Inputs
    spend_usd DECIMAL(10, 2),
    impressions INT,
    touches INT, -- Door knocks, calls, etc.
    
    -- Outputs
    leads_generated INT,
    conversions INT,
    revenue_usd DECIMAL(12, 2),
    
    -- Transformed features
    adstock_transformed DECIMAL(10, 4), -- After Weibull decay
    saturation_transformed DECIMAL(10, 4), -- After Hill function
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mmm_obs_storm ON mmm_observations(storm_id);
CREATE INDEX idx_mmm_obs_date ON mmm_observations(observation_date);
CREATE INDEX idx_mmm_obs_zip ON mmm_observations(zip_code);

-- ============================================================================
-- 3. CAUSAL INFERENCE: Uplift Modeling
-- ============================================================================

CREATE TABLE uplift_models (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    
    model_type VARCHAR(50) DEFAULT 't_learner', -- 't_learner', 's_learner', 'x_learner'
    
    -- Model metadata
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_samples INT,
    validation_auc DECIMAL(5, 4),
    
    -- Model artifacts (serialized)
    model_params JSONB,
    feature_importance JSONB
);

CREATE INDEX idx_uplift_models_storm ON uplift_models(storm_id);

-- Property-level uplift scores
CREATE TABLE uplift_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES uplift_models(model_id),
    property_id UUID NOT NULL,
    
    -- Uplift estimates
    cate DECIMAL(5, 4), -- Conditional Average Treatment Effect
    confidence_lower DECIMAL(5, 4),
    confidence_upper DECIMAL(5, 4),
    
    -- Segmentation
    uplift_band VARCHAR(20), -- 'persuadable', 'sure_thing', 'lost_cause', 'sleeping_dog'
    
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_uplift_scores_property ON uplift_scores(property_id);
CREATE INDEX idx_uplift_scores_band ON uplift_scores(uplift_band);

-- ============================================================================
-- 4. UNCERTAINTY QUANTIFICATION
-- ============================================================================

CREATE TABLE confidence_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    storm_id UUID NOT NULL REFERENCES storms(storm_id),
    
    metric_type VARCHAR(50), -- 'brier_score', 'calibration_error', 'sharpness'
    
    -- Scores
    overall_score DECIMAL(6, 5),
    by_segment JSONB, -- {"persuadable": 0.08, "sure_thing": 0.05}
    
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_confidence_storm ON confidence_metrics(storm_id);

-- ============================================================================
-- 5. ALPHA-SWEEP: Hybrid Attribution Control
-- ============================================================================

CREATE TABLE attribution_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    
    config_name VARCHAR(100),
    
    -- α parameter (0 = pure Markov, 1 = pure Shapley)
    alpha_markov DECIMAL(3, 2) DEFAULT 0.5,
    alpha_shapley DECIMAL(3, 2) DEFAULT 0.5,
    
    -- Active config
    is_active BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attribution_configs_tenant ON attribution_configs(tenant_id);
CREATE INDEX idx_attribution_configs_active ON attribution_configs(is_active);

-- ============================================================================
-- VIEWS: Marketing Science Dashboards
-- ============================================================================

-- Hybrid attribution summary
CREATE OR REPLACE VIEW v_hybrid_attribution AS
SELECT 
    at.storm_id,
    at.channel,
    COUNT(DISTINCT at.property_id) as properties_touched,
    SUM(at.markov_credit) as total_markov_credit,
    SUM(at.shapley_credit) as total_shapley_credit,
    SUM(at.hybrid_credit) as total_hybrid_credit,
    AVG(cj.contract_value_usd) as avg_contract_value
FROM attribution_touchpoints at
LEFT JOIN customer_journeys_v2 cj ON at.property_id = cj.property_id
WHERE cj.converted = TRUE
GROUP BY at.storm_id, at.channel;

-- Uplift segmentation
CREATE OR REPLACE VIEW v_uplift_segments AS
SELECT 
    us.uplift_band,
    COUNT(*) as property_count,
    AVG(us.cate) as avg_uplift,
    AVG(us.confidence_upper - us.confidence_lower) as avg_uncertainty,
    SUM(CASE WHEN cj.converted THEN 1 ELSE 0 END) as conversions
FROM uplift_scores us
LEFT JOIN customer_journeys_v2 cj ON us.property_id = cj.property_id
GROUP BY us.uplift_band;

-- MMM saturation analysis
CREATE OR REPLACE VIEW v_mmm_saturation AS
SELECT 
    mo.zip_code,
    mc.channel_name,
    SUM(mo.spend_usd) as total_spend,
    SUM(mo.touches) as total_touches,
    SUM(mo.conversions) as total_conversions,
    AVG(mo.saturation_transformed) as avg_saturation_score,
    CASE 
        WHEN AVG(mo.saturation_transformed) > 0.8 THEN 'saturated'
        WHEN AVG(mo.saturation_transformed) > 0.5 THEN 'optimal'
        ELSE 'undersaturated'
    END as saturation_status
FROM mmm_observations mo
JOIN mmm_channels mc ON mo.channel_id = mc.channel_id
GROUP BY mo.zip_code, mc.channel_name;

-- ============================================================================
-- FUNCTIONS: Marketing Science Logic
-- ============================================================================

-- Calculate Weibull adstock transformation
CREATE OR REPLACE FUNCTION calculate_adstock(
    p_spend DECIMAL[],
    p_alpha DECIMAL,
    p_theta DECIMAL
) RETURNS DECIMAL[] AS $$
DECLARE
    v_result DECIMAL[];
    v_lag INT;
    v_weight DECIMAL;
    i INT;
BEGIN
    v_result := ARRAY[]::DECIMAL[];
    
    FOR i IN 1..array_length(p_spend, 1) LOOP
        v_result[i] := p_spend[i];
        
        -- Apply Weibull decay to previous periods
        FOR v_lag IN 1..(i-1) LOOP
            v_weight := p_alpha * POWER(v_lag, p_alpha - 1) * EXP(-POWER(v_lag / p_theta, p_alpha));
            v_result[i] := v_result[i] + (p_spend[i - v_lag] * v_weight);
        END LOOP;
    END LOOP;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate Hill saturation
CREATE OR REPLACE FUNCTION calculate_hill_saturation(
    p_x DECIMAL,
    p_k DECIMAL,
    p_s DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    RETURN POWER(p_x, p_s) / (POWER(p_k, p_s) + POWER(p_x, p_s));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate Brier score
CREATE OR REPLACE FUNCTION calculate_brier_score(
    p_predictions DECIMAL[],
    p_actuals BOOLEAN[]
) RETURNS DECIMAL AS $$
DECLARE
    v_sum DECIMAL := 0;
    i INT;
BEGIN
    FOR i IN 1..array_length(p_predictions, 1) LOOP
        v_sum := v_sum + POWER(p_predictions[i] - CASE WHEN p_actuals[i] THEN 1 ELSE 0 END, 2);
    END LOOP;
    
    RETURN v_sum / array_length(p_predictions, 1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate hybrid attribution credit
CREATE OR REPLACE FUNCTION calculate_hybrid_credit(
    p_markov_credit DECIMAL,
    p_shapley_credit DECIMAL,
    p_alpha DECIMAL DEFAULT 0.5
) RETURNS DECIMAL AS $$
BEGIN
    RETURN (p_alpha * p_markov_credit) + ((1 - p_alpha) * p_shapley_credit);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Markov removal effect
CREATE OR REPLACE FUNCTION calculate_removal_effect(
    p_storm_id UUID,
    p_channel VARCHAR
) RETURNS DECIMAL AS $$
DECLARE
    v_with_channel DECIMAL;
    v_without_channel DECIMAL;
BEGIN
    -- Conversion rate WITH channel
    SELECT AVG(CASE WHEN converted THEN 1.0 ELSE 0.0 END)
    INTO v_with_channel
    FROM customer_journeys_v2
    WHERE storm_id = p_storm_id
      AND p_channel = ANY(touchpoint_sequence);
    
    -- Conversion rate WITHOUT channel
    SELECT AVG(CASE WHEN converted THEN 1.0 ELSE 0.0 END)
    INTO v_without_channel
    FROM customer_journeys_v2
    WHERE storm_id = p_storm_id
      AND NOT (p_channel = ANY(touchpoint_sequence));
    
    -- Removal effect = (with - without) / with
    IF v_with_channel > 0 THEN
        RETURN (v_with_channel - COALESCE(v_without_channel, 0)) / v_with_channel;
    ELSE
        RETURN 0;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO stormops;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO stormops;
