# StormOps Data Lake v1 Schema

## Overview
Unified schema for all external data sources integrated into StormOps. Shows join keys across parcels, census tracts, storm events, claims, and imagery.

---

## Core Entity Tables

### 1. properties
**Primary Key**: `property_id`

```sql
CREATE TABLE properties (
    property_id UUID PRIMARY KEY,
    
    -- Identifiers
    parcel_id TEXT UNIQUE,              -- APN from county assessor
    regrid_uuid TEXT,                   -- Regrid universal ID
    
    -- Address
    address TEXT NOT NULL,
    normalized_address TEXT,
    street_number TEXT,
    street_name TEXT,
    street_type TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    
    -- Geospatial
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    geometry GEOMETRY(POINT, 4326),
    parcel_boundary GEOMETRY(POLYGON, 4326),
    
    -- Census linkage
    census_tract_geoid TEXT,            -- 11-digit GEOID
    census_block_group TEXT,            -- 12-digit GEOID
    
    -- Property characteristics
    property_type TEXT,                 -- Residential, Commercial
    year_built INTEGER,
    building_sqft INTEGER,
    land_sqft INTEGER,
    stories INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_parcel (parcel_id),
    INDEX idx_tract (census_tract_geoid),
    INDEX idx_geom USING GIST (geometry)
);
```

**Join Keys**:
- `parcel_id` → permits, appraisal data
- `census_tract_geoid` → census demographics
- `geometry` → spatial joins (storms, imagery)

---

### 2. roofs
**Primary Key**: `roof_id`  
**Foreign Key**: `property_id`

```sql
CREATE TABLE roofs (
    roof_id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(property_id),
    
    -- Physical characteristics
    roof_material TEXT,                 -- Asphalt, Metal, Tile, Flat
    roof_type TEXT,                     -- Gable, Hip, Flat, Gambrel
    roof_sqft INTEGER,
    roof_pitch DECIMAL(4, 2),           -- Degrees
    roof_age_years INTEGER,
    
    -- Condition
    condition_rating TEXT,              -- Excellent, Good, Fair, Poor
    condition_score DECIMAL(3, 2),      -- 0-1 normalized
    last_inspection_date DATE,
    
    -- Vulnerability
    hail_vulnerability_score DECIMAL(3, 2),  -- 0-1, material-dependent
    wind_vulnerability_score DECIMAL(3, 2),
    
    -- Geometry
    roof_footprint GEOMETRY(POLYGON, 4326),
    roof_centroid GEOMETRY(POINT, 4326),
    
    -- Source
    data_source TEXT,                   -- AIRS, RoofNet, Manual, Drone
    image_id UUID,                      -- Link to source imagery
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_property (property_id),
    INDEX idx_material (roof_material),
    INDEX idx_footprint USING GIST (roof_footprint)
);
```

**Join Keys**:
- `property_id` → properties
- `image_id` → aerial_imagery

---

### 3. storm_events
**Primary Key**: `event_id`

```sql
CREATE TABLE storm_events (
    event_id TEXT PRIMARY KEY,          -- NOAA event ID
    
    -- Event details
    event_type TEXT,                    -- Hail, Thunderstorm Wind, Tornado
    begin_datetime TIMESTAMP,
    end_datetime TIMESTAMP,
    
    -- Location
    state TEXT,
    county TEXT,
    cz_name TEXT,                       -- County zone name
    begin_lat DECIMAL(10, 8),
    begin_lon DECIMAL(11, 8),
    end_lat DECIMAL(10, 8),
    end_lon DECIMAL(11, 8),
    
    -- Magnitude
    magnitude DECIMAL(5, 2),            -- Hail size (inches) or wind speed (mph)
    magnitude_type TEXT,                -- Hail, Wind
    
    -- Impact
    injuries_direct INTEGER,
    injuries_indirect INTEGER,
    deaths_direct INTEGER,
    deaths_indirect INTEGER,
    damage_property BIGINT,             -- USD
    damage_crops BIGINT,
    
    -- Geometry
    event_path GEOMETRY(LINESTRING, 4326),
    event_buffer_5mi GEOMETRY(POLYGON, 4326),  -- 5-mile buffer for impact zone
    
    -- Source
    data_source TEXT DEFAULT 'NOAA',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_datetime (begin_datetime),
    INDEX idx_type (event_type),
    INDEX idx_county (state, county),
    INDEX idx_path USING GIST (event_path)
);
```

**Join Keys**:
- Spatial join: `event_buffer_5mi` ∩ `properties.geometry`
- Temporal join: `begin_datetime` for permit velocity analysis

---

### 4. hail_footprints
**Primary Key**: `footprint_id`  
**Foreign Key**: `event_id`

```sql
CREATE TABLE hail_footprints (
    footprint_id UUID PRIMARY KEY,
    event_id TEXT REFERENCES storm_events(event_id),
    
    -- Hazard details
    max_hail_size_inches DECIMAL(4, 2),
    kinetic_energy_joules DECIMAL(10, 2),
    terminal_velocity_mps DECIMAL(6, 2),
    
    -- Probabilistic
    return_period_years INTEGER,        -- 10, 25, 50, 100
    exceedance_probability DECIMAL(5, 4),
    
    -- Geometry
    footprint GEOMETRY(POLYGON, 4326),
    intensity_raster RASTER,            -- Gridded hail size
    
    -- Source
    data_source TEXT,                   -- CLIMADA, NOAA, Radar
    model_version TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_event (event_id),
    INDEX idx_footprint USING GIST (footprint)
);
```

**Join Keys**:
- `event_id` → storm_events
- Spatial: `footprint` ∩ `properties.geometry`

---

### 5. census_tracts
**Primary Key**: `tract_geoid`

```sql
CREATE TABLE census_tracts (
    tract_geoid TEXT PRIMARY KEY,       -- 11-digit GEOID
    
    -- Geography
    state_fips TEXT,
    county_fips TEXT,
    tract_code TEXT,
    tract_name TEXT,
    geometry GEOMETRY(MULTIPOLYGON, 4326),
    
    -- Demographics (ACS 5-year)
    total_population INTEGER,
    median_age DECIMAL(4, 1),
    
    -- Income
    median_household_income INTEGER,
    per_capita_income INTEGER,
    poverty_rate DECIMAL(5, 2),
    
    -- Housing
    total_housing_units INTEGER,
    occupied_units INTEGER,
    vacant_units INTEGER,
    owner_occupied_units INTEGER,
    renter_occupied_units INTEGER,
    median_home_value INTEGER,
    median_gross_rent INTEGER,
    median_year_built INTEGER,
    
    -- Education
    bachelors_or_higher_pct DECIMAL(5, 2),
    
    -- Derived metrics
    homeownership_rate DECIMAL(5, 2),
    vacancy_rate DECIMAL(5, 2),
    
    -- Source
    acs_year INTEGER,                   -- 2023, 2024, etc.
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_state_county (state_fips, county_fips),
    INDEX idx_geom USING GIST (geometry)
);
```

**Join Keys**:
- `tract_geoid` → properties.census_tract_geoid
- Spatial: `geometry` ∩ `properties.geometry`

---

### 6. building_permits
**Primary Key**: `permit_id`

```sql
CREATE TABLE building_permits (
    permit_id TEXT PRIMARY KEY,
    
    -- Linkage
    property_id UUID REFERENCES properties(property_id),
    parcel_id TEXT,
    address TEXT,
    
    -- Permit details
    permit_number TEXT UNIQUE,
    permit_type TEXT,                   -- Roofing, Re-Roof, Repair
    work_type TEXT,
    status TEXT,                        -- Issued, Finaled, Expired
    
    -- Dates
    application_date DATE,
    issue_date DATE,
    final_date DATE,
    expiration_date DATE,
    
    -- Contractor
    contractor_name TEXT,
    contractor_license TEXT,
    contractor_phone TEXT,
    
    -- Valuation
    valuation INTEGER,                  -- USD
    square_footage INTEGER,
    
    -- Location
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    census_tract_geoid TEXT,
    
    -- Source
    data_source TEXT,                   -- Dallas OpenData, County
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_property (property_id),
    INDEX idx_parcel (parcel_id),
    INDEX idx_issue_date (issue_date),
    INDEX idx_contractor (contractor_license),
    INDEX idx_tract (census_tract_geoid)
);
```

**Join Keys**:
- `property_id` → properties
- `parcel_id` → properties.parcel_id
- `census_tract_geoid` → census_tracts

---

### 7. insurance_claims
**Primary Key**: `claim_id`

```sql
CREATE TABLE insurance_claims (
    claim_id TEXT PRIMARY KEY,
    
    -- Linkage
    property_id UUID REFERENCES properties(property_id),
    event_id TEXT REFERENCES storm_events(event_id),
    
    -- Claim details
    claim_number TEXT UNIQUE,
    claim_date DATE,
    loss_date DATE,
    
    -- Peril
    peril_type TEXT,                    -- Hail, Wind, Water, Fire
    cause_of_loss TEXT,
    
    -- Amounts
    claim_amount INTEGER,               -- USD
    paid_amount INTEGER,
    deductible INTEGER,
    
    -- Status
    claim_status TEXT,                  -- Open, Closed, Denied
    settlement_date DATE,
    
    -- Property damage
    roof_damage BOOLEAN,
    siding_damage BOOLEAN,
    window_damage BOOLEAN,
    interior_damage BOOLEAN,
    
    -- Source
    data_source TEXT,                   -- CLIMADA, Verisk, Carrier
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_property (property_id),
    INDEX idx_event (event_id),
    INDEX idx_loss_date (loss_date),
    INDEX idx_peril (peril_type)
);
```

**Join Keys**:
- `property_id` → properties
- `event_id` → storm_events

---

### 8. aerial_imagery
**Primary Key**: `image_id`

```sql
CREATE TABLE aerial_imagery (
    image_id UUID PRIMARY KEY,
    
    -- Image details
    image_url TEXT,
    image_path TEXT,                    -- Local storage path
    image_format TEXT,                  -- JPEG, TIFF, PNG
    
    -- Capture details
    capture_date DATE,
    capture_time TIME,
    sensor_type TEXT,                   -- Satellite, Drone, Aerial
    resolution_cm DECIMAL(6, 2),        -- Ground sample distance
    
    -- Coverage
    coverage_area GEOMETRY(POLYGON, 4326),
    center_point GEOMETRY(POINT, 4326),
    
    -- Source
    data_source TEXT,                   -- AIRS, Nearmap, EagleView, Drone
    provider TEXT,
    
    -- Processing
    processed BOOLEAN DEFAULT FALSE,
    roof_segmentation_complete BOOLEAN DEFAULT FALSE,
    damage_detection_complete BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_capture_date (capture_date),
    INDEX idx_coverage USING GIST (coverage_area)
);
```

**Join Keys**:
- Spatial: `coverage_area` ∩ `properties.geometry`
- `image_id` → roofs.image_id

---

### 9. crime_incidents
**Primary Key**: `incident_id`

```sql
CREATE TABLE crime_incidents (
    incident_id TEXT PRIMARY KEY,
    
    -- Incident details
    incident_number TEXT UNIQUE,
    offense_type TEXT,
    offense_category TEXT,              -- Violent, Property, Other
    
    -- Date/time
    date_occurred DATE,
    time_occurred TIME,
    date_reported DATE,
    
    -- Location
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    geometry GEOMETRY(POINT, 4326),
    beat TEXT,
    division TEXT,
    census_tract_geoid TEXT,
    
    -- Source
    data_source TEXT,                   -- Fort Worth PD, Dallas PD
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_date (date_occurred),
    INDEX idx_offense (offense_type),
    INDEX idx_tract (census_tract_geoid),
    INDEX idx_geom USING GIST (geometry)
);
```

**Join Keys**:
- `census_tract_geoid` → census_tracts
- Spatial: `geometry` near `properties.geometry`

---

## Derived/Aggregated Tables

### 10. tract_metrics
**Primary Key**: `tract_geoid`

```sql
CREATE TABLE tract_metrics (
    tract_geoid TEXT PRIMARY KEY REFERENCES census_tracts(tract_geoid),
    
    -- Property counts
    total_properties INTEGER,
    residential_properties INTEGER,
    
    -- Permit activity (12-month rolling)
    permit_count_12mo INTEGER,
    roofing_permit_count_12mo INTEGER,
    unique_contractors_12mo INTEGER,
    avg_permit_valuation INTEGER,
    
    -- Competition
    contractor_density DECIMAL(6, 2),   -- Contractors per 1000 homes
    market_competitiveness TEXT,        -- Low, Medium, High
    
    -- Storm exposure
    hail_events_5yr INTEGER,
    max_hail_size_5yr DECIMAL(4, 2),
    last_hail_event_date DATE,
    
    -- Crime
    crime_incidents_12mo INTEGER,
    property_crime_rate DECIMAL(6, 2),  -- Per 1000 residents
    
    -- Derived SES
    ses_tier TEXT,                      -- Low, Medium, High
    pricing_power_index DECIMAL(5, 2),  -- 0-100
    
    -- Timestamps
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_ses (ses_tier),
    INDEX idx_competition (market_competitiveness)
);
```

**Join Keys**:
- `tract_geoid` → census_tracts, properties

---

### 11. property_exposure
**Primary Key**: `exposure_id`  
**Foreign Keys**: `property_id`, `event_id`

```sql
CREATE TABLE property_exposure (
    exposure_id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(property_id),
    event_id TEXT REFERENCES storm_events(event_id),
    
    -- Exposure metrics
    distance_to_event_km DECIMAL(8, 2),
    within_event_buffer BOOLEAN,
    
    -- Hazard intensity at property
    hail_size_at_property DECIMAL(4, 2),
    wind_speed_at_property DECIMAL(6, 2),
    
    -- Calculated impact
    sii_score DECIMAL(5, 2),            -- Storm Impact Index
    moe_usd INTEGER,                    -- Margin of Error
    damage_probability DECIMAL(5, 4),
    
    -- Timestamps
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_property (property_id),
    INDEX idx_event (event_id),
    INDEX idx_sii (sii_score)
);
```

**Join Keys**:
- `property_id` → properties
- `event_id` → storm_events

---

### 12. behavior_events
**Primary Key**: `event_id`

```sql
CREATE TABLE behavior_events (
    event_id UUID PRIMARY KEY,
    customer_id UUID,
    property_id UUID REFERENCES properties(property_id),
    
    -- Event details
    event_type TEXT,                    -- impression, click, open, response, appointment, inspection, quote, contract, job_complete
    channel TEXT,                       -- email, sms, phone_outbound, phone_inbound, door_knock, direct_mail, paid_ad, organic_search, referral
    event_timestamp TIMESTAMP,
    
    -- Context at time of event
    days_since_storm INTEGER,
    sii_score_at_event DECIMAL(5, 2),
    ses_tier TEXT,
    psychographic_segment TEXT,         -- Analytical, Emotional, Urgency
    
    -- Message/content
    message_template_id TEXT,
    message_variant TEXT,
    
    -- Outcome
    converted_this_step BOOLEAN,
    final_conversion BOOLEAN,
    job_value_usd INTEGER,
    
    -- Attribution (calculated post-hoc)
    shapley_value DECIMAL(5, 4),        -- 0-1, sums to 1 across journey
    markov_removal_effect DECIMAL(5, 4),
    
    -- Metadata
    session_id TEXT,
    device_type TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_customer (customer_id),
    INDEX idx_property (property_id),
    INDEX idx_timestamp (event_timestamp),
    INDEX idx_channel (channel),
    INDEX idx_event_type (event_type)
);
```

**Join Keys**:
- `property_id` → properties
- `customer_id` → customer_journeys
- Used for Markov+Shapley attribution modeling

---

### 13. customer_journeys
**Primary Key**: `journey_id`

```sql
CREATE TABLE customer_journeys (
    journey_id UUID PRIMARY KEY,
    customer_id UUID,
    property_id UUID REFERENCES properties(property_id),
    
    -- Journey characteristics
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    total_touchpoints INTEGER,
    unique_channels INTEGER,
    
    -- Ordered sequences (JSON arrays)
    touchpoint_sequence JSONB,          -- ["email", "sms", "phone", "door"]
    event_sequence JSONB,               -- ["impression", "click", "response", "contract"]
    
    -- Context
    triggered_by_event_id TEXT REFERENCES storm_events(event_id),
    initial_sii_score DECIMAL(5, 2),
    ses_tier TEXT,
    psychographic_segment TEXT,
    
    -- Outcome
    converted BOOLEAN,
    conversion_date TIMESTAMP,
    time_to_conversion_hours INTEGER,
    job_value_usd INTEGER,
    
    -- Attribution results
    top_channel_by_shapley TEXT,
    top_channel_shapley_value DECIMAL(5, 4),
    attribution_model_version TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_customer (customer_id),
    INDEX idx_property (property_id),
    INDEX idx_converted (converted),
    INDEX idx_start_date (start_date)
);
```

**Join Keys**:
- `property_id` → properties
- `triggered_by_event_id` → storm_events
- `journey_id` → behavior_events (via customer_id)

---

### 14. permit_response_metrics
**Primary Key**: `metric_id`

```sql
CREATE TABLE permit_response_metrics (
    metric_id UUID PRIMARY KEY,
    
    -- Geography
    zip_code TEXT,
    census_tract_geoid TEXT REFERENCES census_tracts(tract_geoid),
    
    -- Historical response patterns
    avg_spike_ratio_30d DECIMAL(6, 2),  -- Typical 30-day post-storm spike
    avg_spike_ratio_90d DECIMAL(6, 2),  -- 90-day cumulative
    median_days_to_peak INTEGER,        -- Days until permit peak
    
    -- Market characteristics
    response_velocity_tier TEXT,        -- Fast, Medium, Slow
    typical_window_days INTEGER,        -- When most permits occur
    
    -- Last event
    last_event_date DATE,
    last_event_id TEXT REFERENCES storm_events(event_id),
    last_event_permits_30d INTEGER,
    
    -- Timestamps
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_zip (zip_code),
    INDEX idx_tract (census_tract_geoid),
    INDEX idx_velocity (response_velocity_tier)
);
```

**Join Keys**:
- `census_tract_geoid` → census_tracts
- `last_event_id` → storm_events

---

### 15. roof_inspections
**Primary Key**: `inspection_id`

```sql
CREATE TABLE roof_inspections (
    inspection_id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(property_id),
    image_id UUID REFERENCES aerial_imagery(image_id),
    
    -- Capture details
    inspection_date DATE,
    inspection_type TEXT,               -- Aerial, Drone, Ground
    inspector TEXT,                     -- Human name or "CV_Model_v1.2"
    
    -- Condition assessment
    condition_score DECIMAL(3, 2),      -- 0-1 (1 = excellent)
    damage_detected BOOLEAN,
    damage_severity TEXT,               -- Minor, Moderate, Severe
    damage_types JSONB,                 -- ["hail_dents", "missing_shingles"]
    
    -- CV confidence
    cv_confidence DECIMAL(3, 2),        -- 0-1
    human_verified BOOLEAN,
    
    -- Measurements
    roof_sqft INTEGER,
    damaged_sqft INTEGER,
    damage_percentage DECIMAL(5, 2),
    
    -- Flags
    urgent_repair_needed BOOLEAN,
    insurance_claim_recommended BOOLEAN,
    
    -- Metadata
    model_version TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_property (property_id),
    INDEX idx_image (image_id),
    INDEX idx_date (inspection_date),
    INDEX idx_damage (damage_detected)
);
```

**Join Keys**:
- `property_id` → properties
- `image_id` → aerial_imagery

---

### 16. consent_records
**Primary Key**: `consent_id`

```sql
CREATE TABLE consent_records (
    consent_id UUID PRIMARY KEY,
    customer_id UUID,
    property_id UUID REFERENCES properties(property_id),
    
    -- Consent details
    consent_type TEXT,                  -- SMS, Phone, Email
    consent_granted BOOLEAN,
    consent_date TIMESTAMP,
    consent_source TEXT,                -- Web_Form, Verbal, Written
    consent_language TEXT,              -- Exact wording shown/read
    
    -- Revocation
    revoked BOOLEAN DEFAULT FALSE,
    revocation_date TIMESTAMP,
    revocation_reason TEXT,
    
    -- Compliance
    tcpa_compliant BOOLEAN,
    recorded_call_id TEXT,              -- If verbal consent
    ip_address INET,                    -- If web form
    
    -- Expiration
    expires_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_customer (customer_id),
    INDEX idx_property (property_id),
    INDEX idx_type (consent_type),
    INDEX idx_granted (consent_granted, revoked)
);
```

**Join Keys**:
- `property_id` → properties
- `customer_id` → customer_journeys

---

### 17. contact_policies
**Primary Key**: `policy_id`

```sql
CREATE TABLE contact_policies (
    policy_id UUID PRIMARY KEY,
    customer_id UUID,
    property_id UUID REFERENCES properties(property_id),
    
    -- Frequency caps
    max_contacts_per_day INTEGER DEFAULT 1,
    max_contacts_per_week INTEGER DEFAULT 3,
    max_contacts_per_month INTEGER DEFAULT 8,
    
    -- Channel-specific caps
    max_sms_per_week INTEGER DEFAULT 2,
    max_calls_per_week INTEGER DEFAULT 2,
    max_emails_per_week INTEGER DEFAULT 3,
    
    -- Quiet hours
    no_contact_before_hour INTEGER DEFAULT 9,
    no_contact_after_hour INTEGER DEFAULT 20,
    timezone TEXT DEFAULT 'America/Chicago',
    
    -- Days off
    no_contact_days JSONB,              -- ["Sunday"]
    
    -- Current counts (rolling windows)
    contacts_today INTEGER DEFAULT 0,
    contacts_this_week INTEGER DEFAULT 0,
    contacts_this_month INTEGER DEFAULT 0,
    last_contact_date TIMESTAMP,
    
    -- Override flags
    high_intent_override BOOLEAN DEFAULT FALSE,
    emergency_override BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_customer (customer_id),
    INDEX idx_property (property_id),
    INDEX idx_last_contact (last_contact_date)
);
```

**Join Keys**:
- `property_id` → properties

---

### 18. exclusion_zones
**Primary Key**: `zone_id`

```sql
CREATE TABLE exclusion_zones (
    zone_id UUID PRIMARY KEY,
    
    -- Geography
    zone_type TEXT,                     -- ZIP, Tract, Polygon
    zone_identifier TEXT,               -- ZIP code, tract GEOID, or name
    geometry GEOMETRY(POLYGON, 4326),
    
    -- Exclusion details
    exclusion_reason TEXT,              -- Legal, High_Complaint, Low_Performance
    excluded_channels JSONB,            -- ["door_knock", "phone"] or ["all"]
    
    -- Temporal
    exclusion_start TIMESTAMP,
    exclusion_end TIMESTAMP,            -- NULL = permanent
    
    -- Metadata
    complaint_count INTEGER,
    conversion_rate DECIMAL(5, 4),
    notes TEXT,
    
    -- Audit
    created_by TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_zone_type (zone_type),
    INDEX idx_identifier (zone_identifier),
    INDEX idx_geom USING GIST (geometry),
    INDEX idx_active (exclusion_start, exclusion_end)
);
```

**Join Keys**:
- Spatial: `geometry` ∩ `properties.geometry`
- `zone_identifier` → properties.zip_code or census_tract_geoid

---

## Join Relationship Summary

```
properties (property_id, parcel_id, census_tract_geoid)
    ├─ roofs (property_id)
    │   ├─ aerial_imagery (image_id)
    │   └─ roof_inspections (property_id, image_id)
    │
    ├─ building_permits (property_id, parcel_id)
    │
    ├─ insurance_claims (property_id, event_id)
    │
    ├─ property_exposure (property_id, event_id)
    │   └─ storm_events (event_id)
    │       ├─ hail_footprints (event_id)
    │       └─ permit_response_metrics (last_event_id)
    │
    ├─ behavior_events (property_id)
    │   └─ customer_journeys (journey_id, property_id, triggered_by_event_id)
    │
    ├─ consent_records (property_id)
    ├─ contact_policies (property_id)
    │
    └─ census_tracts (tract_geoid)
        ├─ tract_metrics (tract_geoid)
        ├─ permit_response_metrics (census_tract_geoid)
        ├─ building_permits (census_tract_geoid)
        ├─ crime_incidents (census_tract_geoid)
        └─ exclusion_zones (zone_identifier, geometry)
```

---

## Governance-Aware Property View

```sql
CREATE VIEW properties_with_governance AS
SELECT 
    p.*,
    
    -- Consent status
    MAX(CASE WHEN cr.consent_type = 'SMS' AND cr.consent_granted AND NOT cr.revoked THEN TRUE ELSE FALSE END) AS has_sms_consent,
    MAX(CASE WHEN cr.consent_type = 'Phone' AND cr.consent_granted AND NOT cr.revoked THEN TRUE ELSE FALSE END) AS has_phone_consent,
    MAX(CASE WHEN cr.consent_type = 'Email' AND cr.consent_granted AND NOT cr.revoked THEN TRUE ELSE FALSE END) AS has_email_consent,
    MIN(cr.expires_at) AS consent_expires_at,
    
    -- Contact limits
    COALESCE(cp.contacts_this_week, 0) AS contacts_this_week,
    cp.last_contact_date,
    CASE 
        WHEN cp.contacts_this_week >= cp.max_contacts_per_week THEN cp.last_contact_date + INTERVAL '7 days'
        WHEN cp.contacts_today >= cp.max_contacts_per_day THEN CURRENT_DATE + INTERVAL '1 day'
        ELSE NOW()
    END AS next_eligible_contact,
    
    -- Exclusions
    CASE WHEN ez.zone_id IS NOT NULL THEN TRUE ELSE FALSE END AS in_exclusion_zone,
    ez.exclusion_reason,
    ez.excluded_channels,
    
    -- Imaging
    CASE WHEN ri.inspection_id IS NOT NULL AND ri.inspection_date > NOW() - INTERVAL '6 months' THEN TRUE ELSE FALSE END AS has_recent_imaging,
    ri.inspection_date AS last_image_date,
    ri.condition_score AS condition_score_from_cv,
    ri.image_id,
    ri.inspection_id,
    CASE 
        WHEN ri.human_verified THEN 'Human_Verified'
        WHEN ri.cv_confidence > 0.8 THEN 'CV_Only'
        ELSE 'None'
    END AS visual_verification_status

FROM properties p
LEFT JOIN consent_records cr ON p.property_id = cr.property_id
LEFT JOIN contact_policies cp ON p.property_id = cp.property_id
LEFT JOIN exclusion_zones ez ON ST_Within(p.geometry, ez.geometry) 
    AND (ez.exclusion_end IS NULL OR ez.exclusion_end > NOW())
LEFT JOIN LATERAL (
    SELECT * FROM roof_inspections 
    WHERE property_id = p.property_id 
    ORDER BY inspection_date DESC 
    LIMIT 1
) ri ON TRUE
GROUP BY p.property_id, cp.policy_id, ez.zone_id, ri.inspection_id;
```

---

## Example Queries

### 1. Properties Exposed to Recent Hail Event

```sql
SELECT 
    p.property_id,
    p.address,
    r.roof_material,
    r.roof_age_years,
    se.event_id,
    se.magnitude AS hail_size_inches,
    pe.sii_score,
    pe.moe_usd,
    ct.median_household_income,
    tm.contractor_density
FROM properties p
JOIN roofs r ON p.property_id = r.property_id
JOIN property_exposure pe ON p.property_id = pe.property_id
JOIN storm_events se ON pe.event_id = se.event_id
JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
JOIN tract_metrics tm ON ct.tract_geoid = tm.tract_geoid
WHERE se.begin_datetime > NOW() - INTERVAL '30 days'
  AND se.event_type = 'Hail'
  AND pe.sii_score > 70
ORDER BY pe.sii_score DESC;
```

### 2. Tract-Level Competition Analysis

```sql
SELECT 
    ct.tract_geoid,
    ct.tract_name,
    ct.median_household_income,
    tm.roofing_permit_count_12mo,
    tm.unique_contractors_12mo,
    tm.contractor_density,
    tm.market_competitiveness,
    COUNT(p.property_id) AS total_properties
FROM census_tracts ct
JOIN tract_metrics tm ON ct.tract_geoid = tm.tract_geoid
LEFT JOIN properties p ON ct.tract_geoid = p.census_tract_geoid
WHERE ct.state_fips = '48' AND ct.county_fips = '113'  -- Dallas County
GROUP BY ct.tract_geoid, ct.tract_name, ct.median_household_income,
         tm.roofing_permit_count_12mo, tm.unique_contractors_12mo,
         tm.contractor_density, tm.market_competitiveness
ORDER BY tm.contractor_density DESC;
```

### 3. Roof Age vs. Permit Activity

```sql
SELECT 
    r.roof_age_years,
    COUNT(*) AS property_count,
    COUNT(bp.permit_id) AS permit_count,
    AVG(bp.valuation) AS avg_permit_value
FROM roofs r
LEFT JOIN properties p ON r.property_id = p.property_id
LEFT JOIN building_permits bp ON p.property_id = bp.property_id
    AND bp.issue_date > NOW() - INTERVAL '2 years'
    AND bp.permit_type ILIKE '%roof%'
WHERE r.roof_age_years IS NOT NULL
GROUP BY r.roof_age_years
ORDER BY r.roof_age_years;
```

### 4. Attribution Analysis

```sql
WITH customer_journey AS (
    SELECT 
        customer_id,
        property_id,
        ARRAY_AGG(channel ORDER BY event_timestamp) AS journey,
        MAX(final_conversion::int) AS converted,
        SUM(shapley_value) AS total_attribution
    FROM behavior_events
    WHERE event_timestamp > NOW() - INTERVAL '90 days'
    GROUP BY customer_id, property_id
)
SELECT 
    channel,
    COUNT(*) AS touchpoint_count,
    SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) AS conversions,
    AVG(total_attribution) AS avg_attribution_weight
FROM customer_journey
CROSS JOIN UNNEST(journey) AS channel
GROUP BY channel
ORDER BY avg_attribution_weight DESC;
```

---

### 5. Permit Response Velocity After Storm

```sql
SELECT 
    se.event_id,
    se.begin_datetime AS storm_date,
    se.magnitude AS hail_size_inches,
    prm.census_tract_geoid,
    prm.avg_spike_ratio_30d,
    prm.response_velocity_tier,
    COUNT(bp.permit_id) AS actual_permits_30d,
    prm.last_event_permits_30d AS expected_permits_30d,
    COUNT(bp.permit_id)::float / NULLIF(prm.last_event_permits_30d, 0) AS actual_vs_expected_ratio
FROM storm_events se
JOIN permit_response_metrics prm ON se.event_id = prm.last_event_id
LEFT JOIN building_permits bp ON prm.census_tract_geoid = bp.census_tract_geoid
    AND bp.issue_date BETWEEN se.begin_datetime AND se.begin_datetime + INTERVAL '30 days'
    AND bp.permit_type ILIKE '%roof%'
WHERE se.begin_datetime > NOW() - INTERVAL '1 year'
  AND se.event_type = 'Hail'
GROUP BY se.event_id, se.begin_datetime, se.magnitude, prm.census_tract_geoid, 
         prm.avg_spike_ratio_30d, prm.response_velocity_tier, prm.last_event_permits_30d
ORDER BY se.begin_datetime DESC;
```

---

### 6. Governance Pre-Contact Check

```sql
-- Properties eligible for SMS contact right now
SELECT 
    p.property_id,
    p.address,
    pe.sii_score,
    pgov.has_sms_consent,
    pgov.contacts_this_week,
    pgov.next_eligible_contact,
    pgov.in_exclusion_zone
FROM properties_with_governance pgov
JOIN properties p ON pgov.property_id = p.property_id
JOIN property_exposure pe ON p.property_id = pe.property_id
WHERE pgov.has_sms_consent = TRUE
  AND pgov.in_exclusion_zone = FALSE
  AND pgov.next_eligible_contact <= NOW()
  AND EXTRACT(HOUR FROM NOW()) BETWEEN 9 AND 20  -- Quiet hours
  AND pe.sii_score > 70
ORDER BY pe.sii_score DESC
LIMIT 100;
```

---

### 7. Imaging-Enhanced Opportunity Scoring

```sql
SELECT 
    p.property_id,
    p.address,
    r.roof_age_years,
    r.roof_material,
    pe.sii_score AS physics_score,
    ri.condition_score AS cv_condition_score,
    ri.damage_detected,
    ri.cv_confidence,
    pgov.visual_verification_status,
    
    -- Adjusted opportunity score
    CASE 
        WHEN pgov.visual_verification_status = 'Human_Verified' THEN pe.sii_score * 1.2
        WHEN pgov.visual_verification_status = 'CV_Only' THEN pe.sii_score * 1.1
        ELSE pe.sii_score
    END * 
    CASE 
        WHEN ri.condition_score < 0.5 THEN 1.3
        WHEN ri.condition_score < 0.7 THEN 1.1
        ELSE 0.9
    END AS adjusted_opportunity_score,
    
    ct.median_household_income,
    tm.contractor_density
    
FROM properties p
JOIN roofs r ON p.property_id = r.property_id
JOIN property_exposure pe ON p.property_id = pe.property_id
JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
JOIN tract_metrics tm ON ct.tract_geoid = tm.tract_geoid
JOIN properties_with_governance pgov ON p.property_id = pgov.property_id
LEFT JOIN roof_inspections ri ON p.property_id = ri.property_id
WHERE pe.sii_score > 60
ORDER BY adjusted_opportunity_score DESC
LIMIT 500;
```

---

## Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Data Sources                    │
├─────────────────────────────────────────────────────────────┤
│ NOAA │ Census │ Permits │ Parcels │ Imagery │ Crime │ Claims│
└────┬─────┬──────┬────────┬─────────┬─────────┬───────┬──────┘
     │     │      │        │         │         │       │
     ▼     ▼      ▼        ▼         ▼         ▼       ▼
┌─────────────────────────────────────────────────────────────┐
│                      ETL / Ingestion Layer                   │
│  (API clients, geocoding, normalization, validation)         │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    StormOps Data Lake (PostgreSQL + PostGIS) │
│  properties │ roofs │ storm_events │ permits │ census │ ...  │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Derived Metrics Layer                      │
│  tract_metrics │ property_exposure │ attribution │ ...       │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      StormOps Application                    │
│  SII Engine │ MOE Calculator │ Opportunity Scorer │ CRM      │
└─────────────────────────────────────────────────────────────┘
```

---

## Storage Estimates

**Assumptions**: Dallas County (~1M parcels), 5 years of historical data

| Table | Rows | Size per Row | Total Size |
|-------|------|--------------|------------|
| properties | 1M | 1 KB | 1 GB |
| roofs | 1M | 2 KB | 2 GB |
| storm_events | 500 | 2 KB | 1 MB |
| hail_footprints | 500 | 50 KB | 25 MB |
| census_tracts | 500 | 5 KB | 2.5 MB |
| building_permits | 100K | 1 KB | 100 MB |
| insurance_claims | 50K | 1 KB | 50 MB |
| aerial_imagery | 10K | 500 bytes | 5 MB |
| crime_incidents | 500K | 500 bytes | 250 MB |
| tract_metrics | 500 | 2 KB | 1 MB |
| property_exposure | 500K | 500 bytes | 250 MB |
| customer_touchpoints | 1M | 500 bytes | 500 MB |

**Total**: ~4.2 GB (excluding raster imagery files)

**Additional Tables**:
- behavior_events: 1M rows × 500 bytes = 500 MB
- customer_journeys: 200K rows × 1 KB = 200 MB
- permit_response_metrics: 1K rows × 2 KB = 2 MB
- roof_inspections: 100K rows × 1 KB = 100 MB
- consent_records: 500K rows × 500 bytes = 250 MB
- contact_policies: 500K rows × 500 bytes = 250 MB
- exclusion_zones: 100 rows × 10 KB = 1 MB

**Revised Total**: ~5.5 GB (core tables only)

---

## Next Steps

1. **Set up PostgreSQL + PostGIS** database
2. **Implement ETL pipelines** for Phase 1 data sources
3. **Build geocoding service** (Census API wrapper)
4. **Create spatial indexes** for performance
5. **Develop derived metrics** calculation jobs
6. **Integrate with StormOps** application layer

---

This schema provides the foundation for your physics → people → money → behavior → causality engine with full context enrichment from public and commercial data sources.
