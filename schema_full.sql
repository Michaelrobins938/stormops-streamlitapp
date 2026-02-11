-- Postgres Schema for StormOps Attribution + Plays

-- Journey storage
CREATE TABLE IF NOT EXISTS customer_journeys (
    property_id TEXT,
    zip_code TEXT,
    event_id TEXT,
    channel TEXT,
    play_id TEXT,
    timestamp TIMESTAMP,
    converted BOOLEAN,
    conversion_value FLOAT,
    PRIMARY KEY (property_id, timestamp)
);

-- Channel attribution
CREATE TABLE IF NOT EXISTS channel_attribution (
    zip_code TEXT,
    event_id TEXT,
    channel TEXT,
    credit FLOAT,
    total_journeys INT,
    conversions INT,
    timestamp TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zip_code, event_id, channel)
);

-- Play attribution
CREATE TABLE IF NOT EXISTS play_attribution (
    zip_code TEXT,
    event_id TEXT,
    play_id TEXT,
    credit FLOAT,
    total_touches INT,
    conversions INT,
    avg_sii FLOAT,
    timestamp TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zip_code, event_id, play_id)
);

-- Play-channel cross-attribution
CREATE TABLE IF NOT EXISTS play_channel_attribution (
    event_id TEXT,
    play_id TEXT,
    channel TEXT,
    credit FLOAT,
    touches INT,
    conversions INT,
    timestamp TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (event_id, play_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_journeys_event ON customer_journeys(event_id, zip_code);
CREATE INDEX IF NOT EXISTS idx_channel_event ON channel_attribution(event_id);
CREATE INDEX IF NOT EXISTS idx_play_event ON play_attribution(event_id);
CREATE INDEX IF NOT EXISTS idx_play_channel ON play_channel_attribution(event_id, play_id);
