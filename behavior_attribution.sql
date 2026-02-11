-- Behavior event logging and attribution

-- Unified behavior events stream
CREATE TABLE IF NOT EXISTS behavior_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    parcel_id VARCHAR(255),
    lead_id VARCHAR(255),
    channel VARCHAR(50),
    event_type VARCHAR(100),
    timestamp TIMESTAMP,
    device_type VARCHAR(50),
    time_of_day VARCHAR(50),
    script_id VARCHAR(255),
    context JSONB,
    outcome VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_behavior_events_lead ON behavior_events(lead_id);
CREATE INDEX idx_behavior_events_channel ON behavior_events(channel);
CREATE INDEX idx_behavior_events_timestamp ON behavior_events(timestamp);

-- Journey outcomes (final value per lead)
CREATE TABLE IF NOT EXISTS journey_outcomes (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    lead_id VARCHAR(255),
    parcel_id VARCHAR(255),
    journey_start TIMESTAMP,
    journey_end TIMESTAMP,
    channels_touched TEXT[],
    final_outcome VARCHAR(50),
    job_revenue_usd FLOAT,
    claim_payout_usd FLOAT,
    total_value_usd FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, lead_id)
);

CREATE INDEX idx_journey_outcomes_event ON journey_outcomes(event_id);
CREATE INDEX idx_journey_outcomes_outcome ON journey_outcomes(final_outcome);

-- Markov chain state transitions
CREATE TABLE IF NOT EXISTS markov_transitions (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    from_state VARCHAR(50),
    to_state VARCHAR(50),
    channel VARCHAR(50),
    count INT,
    probability FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, from_state, to_state, channel)
);

CREATE INDEX idx_markov_transitions_event ON markov_transitions(event_id);

-- Shapley value attribution
CREATE TABLE IF NOT EXISTS shapley_attribution (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    lead_id VARCHAR(255),
    channel VARCHAR(50),
    shapley_value FLOAT,
    markov_share FLOAT,
    hybrid_score FLOAT,
    alpha FLOAT DEFAULT 0.7,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, lead_id, channel)
);

CREATE INDEX idx_shapley_attribution_event ON shapley_attribution(event_id);
CREATE INDEX idx_shapley_attribution_channel ON shapley_attribution(channel);

-- Channel coalition values (for Shapley computation)
CREATE TABLE IF NOT EXISTS coalition_values (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255),
    coalition TEXT,
    coalition_value FLOAT,
    conversion_rate FLOAT,
    avg_revenue FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, coalition)
);

CREATE INDEX idx_coalition_values_event ON coalition_values(event_id);

-- Psychographic segments and priors
CREATE TABLE IF NOT EXISTS psychographic_segments (
    id SERIAL PRIMARY KEY,
    segment_id VARCHAR(255),
    segment_name VARCHAR(255),
    description TEXT,
    channel_priors JSONB,
    script_preference VARCHAR(50),
    response_curve_shape VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Segment membership
CREATE TABLE IF NOT EXISTS segment_membership (
    id SERIAL PRIMARY KEY,
    parcel_id VARCHAR(255),
    segment_id VARCHAR(255),
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(parcel_id, segment_id)
);

CREATE INDEX idx_segment_membership_parcel ON segment_membership(parcel_id);
