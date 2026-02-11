-- StormOps Attribution Tables

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

CREATE TABLE IF NOT EXISTS play_attribution (
    zip_code TEXT,
    event_id TEXT,
    play_id TEXT,
    credit FLOAT,
    total_touches INT,
    conversions INT,
    timestamp TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zip_code, event_id, play_id)
);

CREATE INDEX IF NOT EXISTS idx_channel_event ON channel_attribution(event_id);
CREATE INDEX IF NOT EXISTS idx_play_event ON play_attribution(event_id);
