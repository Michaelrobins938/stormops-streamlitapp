-- Probabilistic Identity Resolution Engine

-- Golden Property Identity (unified view)
CREATE TABLE IF NOT EXISTS golden_property_identity (
    id SERIAL PRIMARY KEY,
    golden_id UUID UNIQUE DEFAULT gen_random_uuid(),
    parcel_id VARCHAR(255),
    address VARCHAR(500),
    lat FLOAT,
    lon FLOAT,
    confidence_score FLOAT,
    brier_score FLOAT,
    decision_maker_name VARCHAR(255),
    decision_maker_phone VARCHAR(20),
    decision_maker_email VARCHAR(255),
    household_size INT,
    owner_occupied BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_golden_property_identity_parcel ON golden_property_identity(parcel_id);
CREATE INDEX idx_golden_property_identity_confidence ON golden_property_identity(confidence_score DESC);

-- Property view signals (disparate sources)
CREATE TABLE IF NOT EXISTS property_signals (
    id SERIAL PRIMARY KEY,
    golden_id UUID,
    signal_type VARCHAR(100),
    signal_source VARCHAR(100),
    signal_value JSONB,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_property_signals_golden_id ON property_signals(golden_id);
CREATE INDEX idx_property_signals_type ON property_signals(signal_type);

-- Identity clustering results (K-Means)
CREATE TABLE IF NOT EXISTS identity_clusters (
    id SERIAL PRIMARY KEY,
    cluster_id INT,
    golden_id UUID,
    cluster_center JSONB,
    distance_to_center FLOAT,
    cluster_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_identity_clusters_cluster ON identity_clusters(cluster_id);
CREATE INDEX idx_identity_clusters_golden_id ON identity_clusters(golden_id);

-- Streaming Markov state transitions
CREATE TABLE IF NOT EXISTS streaming_markov_state (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    neighborhood_id VARCHAR(255),
    state VARCHAR(50),
    state_probability FLOAT,
    transition_timestamp TIMESTAMP,
    earth2_trigger BOOLEAN,
    removal_effect FLOAT,
    uncertainty_quantile_low FLOAT,
    uncertainty_quantile_high FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_streaming_markov_state_event ON streaming_markov_state(event_id);
CREATE INDEX idx_streaming_markov_state_neighborhood ON streaming_markov_state(neighborhood_id);
CREATE INDEX idx_streaming_markov_state_timestamp ON streaming_markov_state(transition_timestamp DESC);

-- Bayesian MMM parameters
CREATE TABLE IF NOT EXISTS bayesian_mmm_params (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    zip_code VARCHAR(10),
    channel VARCHAR(50),
    adstock_decay_rate FLOAT,
    adstock_shape FLOAT,
    saturation_hill_k FLOAT,
    saturation_hill_s FLOAT,
    baseline_conversion FLOAT,
    channel_elasticity FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, zip_code, channel)
);

CREATE INDEX idx_bayesian_mmm_params_event ON bayesian_mmm_params(event_id);

-- Market saturation tracking
CREATE TABLE IF NOT EXISTS market_saturation (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    neighborhood_id VARCHAR(255),
    canvassing_density FLOAT,
    competitor_density FLOAT,
    saturation_score FLOAT,
    saturation_status VARCHAR(50),
    uplift_delta FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, neighborhood_id)
);

CREATE INDEX idx_market_saturation_event ON market_saturation(event_id);
CREATE INDEX idx_market_saturation_status ON market_saturation(saturation_status);

-- Causal stress test results
CREATE TABLE IF NOT EXISTS causal_stress_tests (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    campaign_id VARCHAR(255),
    damage_propensity_score FLOAT,
    last_touch_bias_delta FLOAT,
    synthetic_ground_truth_error FLOAT,
    robustness_flag BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_causal_stress_tests_event ON causal_stress_tests(event_id);

-- Attribution alpha parameter (user-configurable)
CREATE TABLE IF NOT EXISTS attribution_alpha_config (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    alpha_value FLOAT DEFAULT 0.7,
    mode VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Differential privacy budget tracking
CREATE TABLE IF NOT EXISTS privacy_budget (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    epsilon FLOAT DEFAULT 0.1,
    delta FLOAT DEFAULT 1e-6,
    queries_used INT DEFAULT 0,
    budget_remaining FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
