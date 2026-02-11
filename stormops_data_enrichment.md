# StormOps v1.0.0 Data Enrichment Guide

## Overview
This guide provides API endpoints, sample data structures, and join keys to enrich StormOps with:
- Census demographic/socioeconomic data (income, housing, demographics)
- Building permit data (velocity, competition, activity)
- Property parcel data (roof condition, property characteristics)

---

## 1. US Census Bureau API

### Base Information
- **Base URL**: `https://api.census.gov/data`
- **API Key**: Required (free) - [Request here](https://api.census.gov/data/key_signup.html)
- **Documentation**: https://www.census.gov/data/developers/guidance/api-user-guide.html

### American Community Survey (ACS) 5-Year Data

**Endpoint Pattern**:
```
https://api.census.gov/data/{year}/acs/acs5?get={variables}&for={geography}&in={parent_geography}&key={API_KEY}
```

**Key Variables for StormOps**:

| Variable | Description | Use Case |
|----------|-------------|----------|
| `B19013_001E` | Median household income | SES segmentation, affordability |
| `B25077_001E` | Median home value | Property value proxy, market tier |
| `B25064_001E` | Median gross rent | Renter vs owner dynamics |
| `B01003_001E` | Total population | Market size, density |
| `B25001_001E` | Total housing units | Housing stock |
| `B25002_002E` | Occupied housing units | Occupancy rate |
| `B25002_003E` | Vacant housing units | Vacancy rate |
| `B25024_002E` | Single-family detached homes | Target property type |
| `B25034_001E` | Year structure built (median) | Roof age proxy |
| `B15003_022E` | Bachelor's degree or higher | Education level (behavior proxy) |
| `B25003_002E` | Owner-occupied units | Homeownership rate |
| `B25003_003E` | Renter-occupied units | Rental market size |

**Example API Call** (Dallas County tracts):
```bash
curl "https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B25077_001E,B25001_001E,B25034_001E&for=tract:*&in=state:48+county:113&key=YOUR_KEY"
```

**Sample Response**:
```json
[
  ["NAME", "B19013_001E", "B25077_001E", "B25001_001E", "B25034_001E", "state", "county", "tract"],
  ["Census Tract 101.01, Dallas County, Texas", "65000", "285000", "1523", "1985", "48", "113", "010101"],
  ["Census Tract 101.02, Dallas County, Texas", "45000", "195000", "2341", "1972", "48", "113", "010102"]
]
```

**Geography Identifiers (GEOID)**:
- **State**: 2-digit FIPS (Texas = `48`)
- **County**: 3-digit FIPS (Dallas = `113`)
- **Tract**: 6-digit code
- **Full GEOID**: `{state}{county}{tract}` (e.g., `48113010101`)

**Join Key for StormOps**:
- Geocode property addresses to lat/lon
- Use Census Geocoder API to get GEOID
- Join on `tract_geoid`

---

## 2. Census Geocoding API

### Convert Address → Census Tract

**Endpoint**:
```
https://geocoding.geo.census.gov/geocoder/geographies/address
```

**Parameters**:
- `street`: Street address
- `city`: City name
- `state`: State abbreviation
- `zip`: ZIP code
- `benchmark`: `Public_AR_Current`
- `vintage`: `Current_Current`
- `format`: `json`

**Example Request**:
```bash
curl "https://geocoding.geo.census.gov/geocoder/geographies/address?street=1600+Main+St&city=Dallas&state=TX&zip=75201&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
```

**Sample Response**:
```json
{
  "result": {
    "addressMatches": [{
      "coordinates": {"x": -96.7970, "y": 32.7767},
      "geographies": {
        "Census Tracts": [{
          "GEOID": "48113010101",
          "TRACT": "010101",
          "COUNTY": "113",
          "STATE": "48"
        }]
      }
    }]
  }
}
```

**Join Strategy**:
1. Geocode property address → get `GEOID`
2. Query ACS API with `GEOID` → get demographics
3. Store in StormOps as `property.census_tract_id`

---

## 3. Building Permit Data

### Dallas Open Data Portal

**Portal URL**: https://www.dallasopendata.com/
**Platform**: Socrata Open Data API (SODA)

**Note**: Dallas uses DallasNow system. Check for available datasets at the portal.

### Generic Permit Data Structure

**Typical Fields**:
```json
{
  "permit_number": "BP2024-12345",
  "permit_type": "Roofing",
  "issue_date": "2024-01-15",
  "status": "Issued",
  "work_type": "Re-Roof",
  "property_address": "123 Main St",
  "parcel_id": "00123456789",
  "contractor_name": "ABC Roofing",
  "contractor_license": "TX-12345",
  "valuation": 15000,
  "square_footage": 2500,
  "latitude": 32.7767,
  "longitude": -96.7970
}
```

### Socrata API Pattern

**Endpoint**:
```
https://{domain}/resource/{dataset_id}.json
```

**Query Parameters**:
- `$where`: SQL-like filtering
- `$limit`: Number of records
- `$offset`: Pagination
- `$order`: Sort order
- `$select`: Specific fields

**Example** (hypothetical Dallas permits):
```bash
curl "https://www.dallasopendata.com/resource/abcd-1234.json?\$where=permit_type='Roofing' AND issue_date>'2023-01-01'&\$limit=1000"
```

### Alternative: County-Level Permit Data

**Dallas County** may provide permit data. Check:
- Dallas County Appraisal District (DCAD)
- Texas Department of Licensing and Regulation (TDLR)

### Join Keys for Permits

**Primary Join Options**:
1. **Address Matching**: Normalize and match street addresses
2. **Parcel ID (APN)**: Most reliable if available
3. **Lat/Lon**: Spatial join within tolerance (e.g., 50m)

**Permit Velocity Calculation**:
```python
# Permits per tract per year
permit_velocity = permits.groupby(['census_tract', 'year']).size()

# Competition metric: unique contractors per tract
competition = permits.groupby('census_tract')['contractor_license'].nunique()
```

---

## 4. Property Parcel Data

### Dallas Central Appraisal District (DCAD)

**Website**: https://www.dallascad.org/
**Data Access**: May require bulk data purchase or API access

**Key Fields**:
```json
{
  "account_number": "00123456789",
  "property_address": "123 Main St, Dallas, TX 75201",
  "owner_name": "John Doe",
  "property_type": "Residential",
  "year_built": 1985,
  "building_sqft": 2500,
  "land_sqft": 7500,
  "market_value": 350000,
  "improvement_value": 280000,
  "land_value": 70000,
  "roof_type": "Composition Shingle",
  "roof_condition": "Average",
  "last_sale_date": "2018-06-15",
  "last_sale_price": 285000,
  "latitude": 32.7767,
  "longitude": -96.7970
}
```

### Commercial Parcel APIs

**Attom Data Solutions**: https://api.developer.attomdata.com/
- Property characteristics, sales history, valuations
- Paid API with comprehensive coverage

**Regrid (formerly Loveland)**: https://regrid.com/
- Parcel boundaries and basic attributes
- Freemium model

**Example Attom API Call**:
```bash
curl -X GET "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/address?address1=123+Main+St&address2=Dallas,+TX+75201" \
  -H "apikey: YOUR_API_KEY"
```

### Join Keys for Parcels

**Primary**: `parcel_id` / `account_number` (APN)
**Secondary**: Normalized address string
**Tertiary**: Lat/lon spatial join

---

## 5. Roof Condition Data

### Sources

**1. Aerial Imagery + ML**:
- Google Earth Engine
- Nearmap (commercial)
- EagleView (commercial roofing reports)

**2. Insurance Claims Data**:
- NAIC (National Association of Insurance Commissioners)
- State insurance department filings
- Proprietary datasets (e.g., Verisk)

**3. Proxy Indicators**:
- `year_built` from parcel data → estimate roof age
- Permit history → recent re-roof activity
- Storm event dates → likely damage areas

**Sample Roof Condition Schema**:
```json
{
  "property_id": "prop_12345",
  "roof_age_years": 18,
  "roof_condition": "Fair",
  "roof_material": "Asphalt Shingle",
  "estimated_replacement_year": 2027,
  "hail_damage_probability": 0.35,
  "last_inspection_date": "2023-08-15"
}
```

---

## 6. Join Key Strategy

### Master Property Table

```sql
CREATE TABLE properties (
  property_id UUID PRIMARY KEY,
  address TEXT,
  normalized_address TEXT,
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  parcel_id TEXT,
  census_tract_geoid TEXT,
  zip_code TEXT,
  created_at TIMESTAMP
);
```

### Enrichment Flow

```
1. Property Address (StormOps input)
   ↓
2. Geocode → lat/lon + census_tract_geoid
   ↓
3. Census API → demographics (join on census_tract_geoid)
   ↓
4. Parcel API → property details (join on address or parcel_id)
   ↓
5. Permit API → permit history (join on address or parcel_id)
   ↓
6. Aggregate → tract-level metrics (permit velocity, competition)
```

### Address Normalization

**Python Example**:
```python
import usaddress

def normalize_address(address_string):
    parsed = usaddress.tag(address_string)
    return {
        'street_number': parsed[0].get('AddressNumber', ''),
        'street_name': parsed[0].get('StreetName', ''),
        'street_type': parsed[0].get('StreetNamePostType', ''),
        'city': parsed[0].get('PlaceName', ''),
        'state': parsed[0].get('StateName', ''),
        'zip': parsed[0].get('ZipCode', '')
    }
```

---

## 7. Sample Integration Code

### Census Data Enrichment

```python
import requests

def get_census_data(geoid, year=2023):
    """Fetch ACS 5-year data for a census tract."""
    base_url = f"https://api.census.gov/data/{year}/acs/acs5"
    
    variables = [
        "B19013_001E",  # Median household income
        "B25077_001E",  # Median home value
        "B25001_001E",  # Total housing units
        "B25034_001E",  # Year structure built
    ]
    
    params = {
        "get": f"NAME,{','.join(variables)}",
        "for": f"tract:{geoid[-6:]}",
        "in": f"state:{geoid[:2]}+county:{geoid[2:5]}",
        "key": "YOUR_API_KEY"
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    return {
        "median_income": int(data[1][1]) if data[1][1] else None,
        "median_home_value": int(data[1][2]) if data[1][2] else None,
        "total_housing_units": int(data[1][3]) if data[1][3] else None,
        "median_year_built": int(data[1][4]) if data[1][4] else None,
    }
```

### Geocoding to Census Tract

```python
def geocode_to_tract(address, city, state, zip_code):
    """Convert address to census tract GEOID."""
    url = "https://geocoding.geo.census.gov/geocoder/geographies/address"
    
    params = {
        "street": address,
        "city": city,
        "state": state,
        "zip": zip_code,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data["result"]["addressMatches"]:
        match = data["result"]["addressMatches"][0]
        tract_info = match["geographies"]["Census Tracts"][0]
        return tract_info["GEOID"]
    
    return None
```

### Permit Velocity Calculation

```python
import pandas as pd
from datetime import datetime, timedelta

def calculate_permit_velocity(permits_df, lookback_months=12):
    """Calculate roofing permit velocity by census tract."""
    cutoff_date = datetime.now() - timedelta(days=lookback_months*30)
    
    recent_permits = permits_df[
        (permits_df['issue_date'] >= cutoff_date) &
        (permits_df['permit_type'].str.contains('Roof', case=False))
    ]
    
    velocity = recent_permits.groupby('census_tract').agg({
        'permit_number': 'count',
        'contractor_license': 'nunique',
        'valuation': 'mean'
    }).rename(columns={
        'permit_number': 'permit_count',
        'contractor_license': 'unique_contractors',
        'valuation': 'avg_permit_value'
    })
    
    return velocity
```

---

## 8. Data Schema for StormOps

### Enriched Property Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class EnrichedProperty:
    # Core identifiers
    property_id: str
    address: str
    latitude: float
    longitude: float
    
    # Census data
    census_tract_geoid: str
    median_income: Optional[int]
    median_home_value: Optional[int]
    homeownership_rate: Optional[float]
    
    # Parcel data
    parcel_id: Optional[str]
    year_built: Optional[int]
    building_sqft: Optional[int]
    roof_type: Optional[str]
    roof_condition: Optional[str]
    
    # Permit data
    last_permit_date: Optional[str]
    permit_count_12mo: int
    tract_permit_velocity: float  # permits per 1000 homes
    tract_contractor_count: int
    
    # Behavioral segmentation
    ses_tier: str  # "Low", "Medium", "High"
    market_competitiveness: str  # "Low", "Medium", "High"
    roof_urgency_score: float  # 0-1
```

---

## 9. API Rate Limits & Best Practices

### Census API
- **Rate Limit**: None officially, but be respectful
- **Best Practice**: Batch requests by geography
- **Caching**: Cache tract-level data (updates annually)

### Socrata (Dallas Open Data)
- **Rate Limit**: 1,000 requests/rolling hour (unauthenticated)
- **With App Token**: 10,000 requests/rolling hour
- **Best Practice**: Use `$limit` and `$offset` for pagination

### Commercial APIs (Attom, Regrid)
- **Rate Limit**: Varies by plan (typically 1-10 req/sec)
- **Cost**: Per-request pricing
- **Best Practice**: Batch lookups, cache aggressively

---

## 10. Claims & Permit Response Layer

### Hail Event → Permit Spike Analysis

**Goal**: Learn how fast areas repair after storms to predict opportunity windows

**Dallas Building Permits Dataset**:
- **URL**: https://www.dallasopendata.com/Services/Building-Permits/e7gq-4sah
- **Socrata ID**: `e7gq-4sah`

**Metric Calculation**:
```python
def calculate_permit_response_velocity(permits_df, events_df):
    """Calculate permit spike after hail events by ZIP/tract."""
    results = []
    
    for _, event in events_df.iterrows():
        event_date = event['begin_datetime']
        affected_zips = get_affected_zips(event)  # Spatial join
        
        for zip_code in affected_zips:
            # Baseline: 90 days before event
            baseline = permits_df[
                (permits_df['zip_code'] == zip_code) &
                (permits_df['issue_date'] >= event_date - timedelta(days=90)) &
                (permits_df['issue_date'] < event_date) &
                (permits_df['permit_type'].str.contains('Roof', case=False))
            ].shape[0] / 3  # Monthly average
            
            # Response windows
            for window_days in [7, 14, 30, 60, 90]:
                response = permits_df[
                    (permits_df['zip_code'] == zip_code) &
                    (permits_df['issue_date'] >= event_date) &
                    (permits_df['issue_date'] < event_date + timedelta(days=window_days)) &
                    (permits_df['permit_type'].str.contains('Roof', case=False))
                ].shape[0]
                
                results.append({
                    'event_id': event['event_id'],
                    'zip_code': zip_code,
                    'window_days': window_days,
                    'baseline_monthly': baseline,
                    'response_permits': response,
                    'spike_ratio': response / (baseline * (window_days/30)) if baseline > 0 else 0,
                    'velocity_tier': 'Fast' if response / (baseline * (window_days/30)) > 3 else 'Medium' if response / (baseline * (window_days/30)) > 1.5 else 'Slow'
                })
    
    return pd.DataFrame(results)
```

**Schema Addition**:
```python
@dataclass
class PermitResponseMetrics:
    zip_code: str
    census_tract_geoid: str
    
    # Historical response patterns
    avg_spike_ratio_30d: float      # Typical 30-day post-storm spike
    avg_spike_ratio_90d: float      # 90-day cumulative
    median_days_to_peak: int        # Days until permit peak
    
    # Market characteristics
    response_velocity_tier: str     # Fast, Medium, Slow
    typical_window_days: int        # When most permits occur
    
    # Last event
    last_event_date: Optional[str]
    last_event_permits_30d: int
```

### Claims Data Integration

**Anonymized Claims Schema**:
```python
@dataclass
class ClaimProxy:
    claim_id: str
    property_id: str
    event_id: str
    
    # Anonymized amounts (bucketed)
    claim_amount_bucket: str        # <5K, 5-10K, 10-20K, 20K+
    paid_amount_bucket: str
    
    # Timing
    loss_date: str
    claim_date: str
    settlement_date: Optional[str]
    days_to_settlement: Optional[int]
    
    # Damage indicators
    roof_damage: bool
    total_loss: bool
    
    # Geography (for aggregation only)
    census_tract_geoid: str
    zip_code: str
```

**Join Strategy**:
```sql
-- Tract-level claim rates (privacy-preserving)
SELECT 
    ct.tract_geoid,
    COUNT(DISTINCT c.claim_id) AS claim_count,
    COUNT(DISTINCT c.property_id) AS properties_with_claims,
    AVG(c.days_to_settlement) AS avg_settlement_days,
    SUM(CASE WHEN c.roof_damage THEN 1 ELSE 0 END) AS roof_claims
FROM census_tracts ct
LEFT JOIN claim_proxy c ON ct.tract_geoid = c.census_tract_geoid
WHERE c.loss_date > NOW() - INTERVAL '2 years'
GROUP BY ct.tract_geoid;
```

---

## 11. Behavioral & Attribution Trace Schema

### Behavior Events Table

**Aligns with Markov + Shapley attribution model**

```python
from enum import Enum
from typing import List, Optional

class ChannelType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PHONE_OUTBOUND = "phone_outbound"
    PHONE_INBOUND = "phone_inbound"
    DOOR_KNOCK = "door_knock"
    DIRECT_MAIL = "direct_mail"
    PAID_AD = "paid_ad"
    ORGANIC_SEARCH = "organic_search"
    REFERRAL = "referral"

class EventType(Enum):
    IMPRESSION = "impression"
    CLICK = "click"
    OPEN = "open"
    RESPONSE = "response"
    APPOINTMENT = "appointment"
    INSPECTION = "inspection"
    QUOTE = "quote"
    CONTRACT = "contract"
    JOB_COMPLETE = "job_complete"

@dataclass
class BehaviorEvent:
    event_id: str
    customer_id: str
    property_id: str
    
    # Event details
    event_type: EventType
    channel: ChannelType
    timestamp: datetime
    
    # Context at time of event
    days_since_storm: Optional[int]
    sii_score_at_event: Optional[float]
    ses_tier: Optional[str]
    psychographic_segment: Optional[str]  # Analytical, Emotional, Urgency
    
    # Message/content
    message_template_id: Optional[str]
    message_variant: Optional[str]
    
    # Outcome
    converted_this_step: bool
    final_conversion: bool              # Did customer eventually convert?
    job_value_usd: Optional[int]        # If converted
    
    # Attribution (calculated post-hoc)
    shapley_value: Optional[float]      # 0-1, sums to 1 across journey
    markov_removal_effect: Optional[float]
    
    # Metadata
    session_id: Optional[str]
    device_type: Optional[str]
    created_at: datetime
```

**Customer Journey Aggregation**:
```python
@dataclass
class CustomerJourney:
    journey_id: str
    customer_id: str
    property_id: str
    
    # Journey characteristics
    start_date: datetime
    end_date: Optional[datetime]
    total_touchpoints: int
    unique_channels: int
    
    # Ordered sequence
    touchpoint_sequence: List[str]      # ["email", "sms", "phone", "door"]
    event_sequence: List[str]           # ["impression", "click", "response", "contract"]
    
    # Context
    triggered_by_event_id: Optional[str]  # Storm event that started journey
    initial_sii_score: Optional[float]
    ses_tier: str
    psychographic_segment: str
    
    # Outcome
    converted: bool
    conversion_date: Optional[datetime]
    time_to_conversion_hours: Optional[int]
    job_value_usd: Optional[int]
    
    # Attribution results
    top_channel_by_shapley: Optional[str]
    top_channel_shapley_value: Optional[float]
    attribution_model_version: str
```

**Master Property Table Extension**:
```python
@dataclass
class EnrichedPropertyV2:
    # Core identifiers (existing)
    property_id: str
    parcel_id: Optional[str]
    census_tract_geoid: str
    
    # Physics layer
    event_id: Optional[str]             # Most recent storm event
    sii_score: Optional[float]
    moe_usd: Optional[int]
    last_hail_date: Optional[str]
    
    # Parcel/roof layer
    roof_age_years: Optional[int]
    roof_condition: Optional[str]
    roof_material: Optional[str]
    
    # People layer (SES)
    median_income: Optional[int]
    median_home_value: Optional[int]
    ses_tier: str                       # Low, Medium, High
    
    # Money layer (market)
    tract_permit_velocity: float
    tract_contractor_count: int
    market_competitiveness: str
    
    # Behavior layer
    psychographic_segment: Optional[str]  # Analytical, Emotional, Urgency
    prior_engagement_count: int           # Historical touchpoints
    last_contact_date: Optional[str]
    customer_lifetime_value: Optional[int]
    
    # Journey state
    active_journey_id: Optional[str]
    journey_stage: Optional[str]          # Awareness, Consideration, Decision
    
    # Imaging
    has_recent_imaging: bool
    last_image_date: Optional[str]
    condition_score_from_cv: Optional[float]
    image_id: Optional[str]
```

**Attribution Calculation Reference**:
- **Framework**: https://amplitude.com/blog/attribution-model-frameworks
- **Models**: First-touch, Last-touch, Linear, Time-decay, Shapley, Markov Chain

---

## 12. Imaging & Roof Condition Hooks

### Imaging Sources

#### 1. Roboflow Roof Damage Dataset
- **URL**: https://universe.roboflow.com/reworked/roof-damage-ebuyf
- **Classes**: Damaged, Undamaged, Missing shingles, Hail dents
- **Format**: YOLO, COCO
- **Use**: Fine-tune damage detection models

#### 2. Commercial Aerial Providers
- **EagleView**: High-res roof reports with measurements
- **Nearmap**: Frequent aerial updates (monthly in some markets)
- **Google Earth Engine**: Historical imagery

#### 3. Drone Inspection Integration
- **DJI SDK**: Automated roof inspection flights
- **Skydio**: Autonomous damage assessment

### Imaging Schema Extension

```python
@dataclass
class RoofInspection:
    inspection_id: str
    property_id: str
    image_id: str
    
    # Capture details
    inspection_date: date
    inspection_type: str                # Aerial, Drone, Ground
    inspector: Optional[str]            # Human or "CV_Model_v1.2"
    
    # Condition assessment
    condition_score: float              # 0-1 (1 = excellent)
    damage_detected: bool
    damage_severity: Optional[str]      # Minor, Moderate, Severe
    damage_types: List[str]             # ["hail_dents", "missing_shingles"]
    
    # CV confidence
    cv_confidence: Optional[float]      # 0-1
    human_verified: bool
    
    # Measurements
    roof_sqft: Optional[int]
    damaged_sqft: Optional[int]
    damage_percentage: Optional[float]
    
    # Flags
    urgent_repair_needed: bool
    insurance_claim_recommended: bool
    
    # Metadata
    model_version: Optional[str]
    created_at: datetime
```

**Property Table Imaging Fields**:
```python
# Add to EnrichedPropertyV2
has_recent_imaging: bool                    # Within 6 months
last_image_date: Optional[str]
condition_score_from_cv: Optional[float]    # Latest CV assessment
image_id: Optional[str]                     # Link to aerial_imagery table
inspection_id: Optional[str]                # Link to roof_inspection table

# Imaging quality flags
imaging_resolution_cm: Optional[float]      # Ground sample distance
imaging_confidence: Optional[float]         # CV model confidence
visual_verification_status: str             # "None", "CV_Only", "Human_Verified"
```

**Differential Treatment Logic**:
```python
def calculate_opportunity_score(property: EnrichedPropertyV2) -> float:
    """Adjust scoring based on imaging availability."""
    base_score = property.sii_score
    
    # Boost confidence if visually verified
    if property.visual_verification_status == "Human_Verified":
        confidence_multiplier = 1.2
    elif property.visual_verification_status == "CV_Only":
        confidence_multiplier = 1.1
    else:
        confidence_multiplier = 1.0  # Physics-only estimate
    
    # Adjust for known condition
    if property.condition_score_from_cv:
        if property.condition_score_from_cv < 0.5:  # Poor condition
            condition_boost = 1.3
        elif property.condition_score_from_cv < 0.7:  # Fair
            condition_boost = 1.1
        else:  # Good condition
            condition_boost = 0.9
    else:
        condition_boost = 1.0
    
    return base_score * confidence_multiplier * condition_boost
```

---

## 13. Governance & Safety Fields

### TCPA Compliance & Contact Management

**Consent Tracking**:
```python
@dataclass
class ConsentRecord:
    consent_id: str
    customer_id: str
    property_id: str
    
    # Consent details
    consent_type: str                   # SMS, Phone, Email
    consent_granted: bool
    consent_date: datetime
    consent_source: str                 # "Web_Form", "Verbal", "Written"
    consent_language: str               # Exact wording shown/read
    
    # Revocation
    revoked: bool
    revocation_date: Optional[datetime]
    revocation_reason: Optional[str]
    
    # Compliance
    tcpa_compliant: bool
    recorded_call_id: Optional[str]     # If verbal consent
    ip_address: Optional[str]           # If web form
    
    # Expiration
    expires_at: Optional[datetime]
    
    created_at: datetime
    updated_at: datetime
```

**Contact Frequency Limits**:
```python
@dataclass
class ContactPolicy:
    policy_id: str
    customer_id: str
    property_id: str
    
    # Frequency caps
    max_contacts_per_day: int           # Default: 1
    max_contacts_per_week: int          # Default: 3
    max_contacts_per_month: int         # Default: 8
    
    # Channel-specific caps
    max_sms_per_week: int
    max_calls_per_week: int
    max_emails_per_week: int
    
    # Quiet hours
    no_contact_before_hour: int         # 9 AM
    no_contact_after_hour: int          # 8 PM
    timezone: str
    
    # Days off
    no_contact_days: List[str]          # ["Sunday"]
    
    # Current counts (rolling windows)
    contacts_today: int
    contacts_this_week: int
    contacts_this_month: int
    last_contact_date: Optional[datetime]
    
    # Override flags
    high_intent_override: bool          # Customer requested contact
    emergency_override: bool            # Urgent storm damage
    
    updated_at: datetime
```

**Exclusion Zones**:
```python
@dataclass
class ExclusionZone:
    zone_id: str
    
    # Geography
    zone_type: str                      # "ZIP", "Tract", "Polygon"
    zone_identifier: str                # ZIP code, tract GEOID, or WKT
    geometry: Optional[str]             # WKT polygon
    
    # Exclusion details
    exclusion_reason: str               # "Legal", "High_Complaint", "Low_Performance"
    excluded_channels: List[str]        # ["door_knock", "phone"] or ["all"]
    
    # Temporal
    exclusion_start: datetime
    exclusion_end: Optional[datetime]   # None = permanent
    
    # Metadata
    complaint_count: Optional[int]
    conversion_rate: Optional[float]
    notes: Optional[str]
    
    created_by: str
    created_at: datetime
```

**Master Property Governance Fields**:
```python
# Add to EnrichedPropertyV2
@dataclass
class PropertyGovernance:
    # Consent status
    has_sms_consent: bool
    has_phone_consent: bool
    has_email_consent: bool
    consent_expires_at: Optional[datetime]
    
    # Contact limits
    contacts_this_week: int
    last_contact_date: Optional[datetime]
    next_eligible_contact: datetime     # Calculated from policy
    
    # Exclusions
    in_exclusion_zone: bool
    exclusion_reason: Optional[str]
    excluded_channels: List[str]
    
    # Complaint history
    complaint_count: int
    last_complaint_date: Optional[datetime]
    do_not_contact: bool                # Hard stop
    
    # Legal flags
    litigation_flag: bool
    bankruptcy_flag: bool
```

**Pre-Contact Validation**:
```python
def can_contact(property: EnrichedPropertyV2, channel: ChannelType) -> tuple[bool, str]:
    """Validate contact eligibility before triggering."""
    gov = property.governance
    
    # Hard stops
    if gov.do_not_contact:
        return False, "Do Not Contact flag set"
    
    if gov.litigation_flag:
        return False, "Property in litigation"
    
    if gov.in_exclusion_zone and (channel.value in gov.excluded_channels or "all" in gov.excluded_channels):
        return False, f"Property in exclusion zone: {gov.exclusion_reason}"
    
    # Consent checks
    if channel == ChannelType.SMS and not gov.has_sms_consent:
        return False, "No SMS consent"
    
    if channel == ChannelType.PHONE_OUTBOUND and not gov.has_phone_consent:
        return False, "No phone consent"
    
    # Frequency limits
    if datetime.now() < gov.next_eligible_contact:
        return False, f"Frequency limit: next eligible {gov.next_eligible_contact}"
    
    # Quiet hours (if phone/door)
    if channel in [ChannelType.PHONE_OUTBOUND, ChannelType.DOOR_KNOCK]:
        current_hour = datetime.now().hour
        if current_hour < 9 or current_hour > 20:
            return False, "Outside contact hours (9 AM - 8 PM)"
    
    return True, "OK"
```

**Governance Dashboard Metrics**:
```sql
-- Compliance health check
SELECT 
    COUNT(*) AS total_properties,
    SUM(CASE WHEN has_sms_consent THEN 1 ELSE 0 END) AS sms_consent_count,
    SUM(CASE WHEN has_phone_consent THEN 1 ELSE 0 END) AS phone_consent_count,
    SUM(CASE WHEN do_not_contact THEN 1 ELSE 0 END) AS dnc_count,
    SUM(CASE WHEN in_exclusion_zone THEN 1 ELSE 0 END) AS excluded_count,
    SUM(CASE WHEN complaint_count > 0 THEN 1 ELSE 0 END) AS properties_with_complaints,
    AVG(contacts_this_week) AS avg_weekly_contacts
FROM properties;
```

**Reference**:
- **TCPA Compliance**: https://blog.seduca.ai/id/89407/
- **Best Practices**: Opt-in consent, clear revocation paths, frequency caps, quiet hours

---

## 14. Next Steps

### Immediate Actions
1. **Get API Keys**:
   - Census API: https://api.census.gov/data/key_signup.html
   - Dallas Open Data: Check if app token needed
   
2. **Explore Dallas Data**:
   - Visit https://www.dallasopendata.com/
   - Search for "building permits" or "roofing permits"
   - Identify dataset ID and schema
   
3. **Test Geocoding**:
   - Run sample addresses through Census Geocoder
   - Verify GEOID accuracy
   
4. **Prototype Join Logic**:
   - Implement address normalization
   - Test fuzzy matching for permits ↔ properties

### Advanced Enrichment
- **Weather Data**: NOAA Storm Events Database
- **Hail Maps**: NOAA NEXRAD radar archives
- **Competitor Intelligence**: Scrape contractor reviews (Yelp, Google)
- **Market Trends**: Zillow API, Redfin data

### Governance Setup
1. **Implement consent tracking** before any outbound contact
2. **Define exclusion zones** based on complaint history
3. **Set frequency caps** per channel
4. **Build pre-contact validation** into trigger logic

---

## References

Content was rephrased for compliance with licensing restrictions.

[1] US Census Bureau API Documentation - https://www.census.gov/data/developers/data-sets.html
[2] American Community Survey 5-Year Data - https://www.census.gov/data/developers/data-sets/acs-5year.html
[3] Census Geocoding Services - https://www.census.gov/data/developers/data-sets/Geocoding-services.html
[4] Socrata Open Data API - https://dev.socrata.com/
[5] Dallas Open Data Portal - https://dallascityhall.com/Pages/data-transparency.aspx
[6] Geocodio Census Data Guide - https://www.geocod.io/guides/demographics-census/
[7] Attom Data API - https://api.developer.attomdata.com/docs
