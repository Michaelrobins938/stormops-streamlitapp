# StormOps Phased Data Acquisition Plan

## Overview
"Yes to all" phased approach for enriching StormOps v1.0.0 with external datasets. Each phase builds on the previous, maintaining a sane integration path from physics → people → money → behavior → causality.

---

## Phase 1 – Hail, Roofs, Exposure
**Goal**: Calibrate SII and MOE against real hail + claims, improve roof detection

### Datasets

#### 1. NOAA Storm Events Database
- **URL**: https://www.ncei.noaa.gov/stormevents/
- **Coverage**: US-wide, 1950-present
- **Format**: CSV bulk download or API
- **Key Fields**:
  - `event_id`: Unique storm event
  - `event_type`: Hail, Thunderstorm Wind, Tornado
  - `begin_date_time`, `end_date_time`
  - `begin_lat`, `begin_lon`, `end_lat`, `end_lon`
  - `magnitude`: Hail size (inches)
  - `damage_property`: Property damage estimate
  - `state`, `county`, `cz_name` (county zone)

**Use Case**: Ground truth for SII calibration, temporal storm patterns

**API Example**:
```bash
# Download by year and state
curl "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d2024_c20250101.csv.gz"
```

#### 2. CLIMADA Hail Damage Model
- **URL**: https://nhess.copernicus.org/articles/24/847/2024/
- **Source**: ETH Zurich CLIMADA platform
- **Content**: Hail hazard maps + damage functions + claims data
- **Format**: NetCDF, CSV
- **Key Components**:
  - Probabilistic hail footprints
  - Damage-to-loss functions by building type
  - Calibrated against insurance claims

**Use Case**: Validate MOE calculations, improve damage-to-cost models

#### 3. AIRS Roof Segmentation Dataset
- **URL**: https://daoqiqi.github.io/assets/img/achievements/airs.pdf
- **Content**: Aerial imagery with roof instance segmentation
- **Format**: Images + annotations (COCO format)
- **Coverage**: Research dataset, various US cities

**Use Case**: Train/improve roof footprint detection models

#### 4. RoofNet Material Classification
- **URL**: https://arxiv.org/html/2505.19358v1
- **Content**: Roof material classification dataset
- **Classes**: Asphalt shingle, metal, tile, flat, etc.
- **Format**: Images + labels

**Use Case**: Classify roof material from aerial imagery → refine hail vulnerability

#### 5. TxGIO StratMap Parcels
- **URL**: https://tnris.org/stratmap/land-parcels/
- **Coverage**: Texas statewide parcel boundaries
- **Format**: Shapefile, GeoJSON
- **Key Fields**:
  - `parcel_id` (APN)
  - Geometry (polygon)
  - Basic attributes (varies by county)

**Use Case**: Spatial join for property boundaries, roof footprint extraction

**Download**:
```bash
# Dallas County parcels
wget https://data.tnris.org/collection/[dataset_id]/parcels_dallas.zip
```

#### 6. Regrid Texas Sample
- **URL**: https://regrid.com/
- **Coverage**: US-wide parcel data
- **Format**: API or bulk download
- **Key Fields**:
  - `ll_uuid`: Regrid universal parcel ID
  - `parcelnumb`: Local APN
  - `address`, `city`, `state`, `zip`
  - `usecode`: Property use classification
  - Geometry

**Use Case**: Parcel-level joins, property characteristics

---

## Phase 2 – Local Activity & Competition
**Goal**: Infer roof age, competition intensity, post-storm permit spikes

### Datasets

#### 1. Dallas Building Permits
- **URL**: https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/pages/online-records.aspx
- **Portal**: Dallas Open Data (Socrata)
- **Key Fields**:
  - `permit_number`
  - `permit_type`: Filter for "Roofing", "Re-Roof"
  - `issue_date`, `final_date`
  - `address`, `parcel_id`
  - `contractor_name`, `contractor_license`
  - `valuation`, `square_footage`
  - `status`: Issued, Finaled, Expired

**Use Case**:
- Roof age proxy (last re-roof date)
- Competition density (unique contractors per tract)
- Post-storm velocity (permit spike after hail events)

**Query Pattern**:
```python
# Socrata API
import requests

url = "https://www.dallasopendata.com/resource/{dataset_id}.json"
params = {
    "$where": "permit_type LIKE '%Roof%' AND issue_date > '2020-01-01'",
    "$limit": 5000,
    "$order": "issue_date DESC"
}
response = requests.get(url, params=params)
permits = response.json()
```

#### 2. Permit Dashboards
- **URL**: https://dallascityhall.com/departments/sustainabledevelopment/Pages/permits-inspections.aspx
- **Content**: Tableau dashboards with permit trends
- **Use Case**: Visual validation of permit velocity patterns

---

## Phase 3 – SES, Behavior, Risk
**Goal**: Build neighborhood psychographic priors (pricing power, financing need, messaging)

### Datasets

#### 1. Census ACS 5-Year Data
- **URL**: https://data.census.gov
- **API**: https://api.census.gov/data/2023/acs/acs5
- **Key Variables** (see previous enrichment guide):
  - `B19013_001E`: Median household income
  - `B25077_001E`: Median home value
  - `B15003_022E`: Bachelor's degree or higher
  - `B25003_002E`: Owner-occupied units
  - `B25034_001E`: Year structure built

**Use Case**: SES segmentation, affordability modeling, education-based behavior priors

#### 2. Fort Worth Crime Data Center
- **URL**: https://police.fortworthtexas.gov/Crime-Public-Info/Crime-Data-Center
- **Format**: CSV, Socrata API
- **Key Fields**:
  - `incident_number`
  - `offense_type`
  - `date_occurred`
  - `address`, `latitude`, `longitude`
  - `beat`, `division`

**Use Case**: Neighborhood risk scoring, property maintenance proxy, messaging tone adjustment

**Dallas Equivalent**: Check Dallas Police Open Data portal for comparable datasets

---

## Phase 4 – Imaging & CV Enhancement
**Goal**: Refine visual SII components, generate richer Impact Reports

### Datasets

#### 1. Roboflow Hail/Roof Damage Datasets
- **URL**: https://universe.roboflow.com/search?q=class%3Ahail+damage
- **Content**: Annotated images of hail damage, roof damage
- **Format**: YOLO, COCO, Pascal VOC
- **Classes**: Hail dents, missing shingles, cracked tiles, etc.

**Use Case**: Train damage detection models for drone/aerial imagery analysis

**Example Datasets**:
- "Hail Damage Detection"
- "Roof Damage Assessment"
- "Storm Damage Segmentation"

#### 2. Building Damage Segmentation (RoofN3D)
- **URL**: https://github.com/LysanetsAndriy/Building-damage-segmentation
- **Content**: Research code + datasets for damage segmentation
- **Format**: PyTorch models, annotated images

**Use Case**: Semantic segmentation of damage severity levels

---

## Phase 5 – Behavioral / Attribution Sandbox
**Goal**: Prototype hybrid Markov+Shapley attribution before production

### Datasets

#### 1. E-Commerce Customer Behavior Dataset
- **URL**: https://www.kaggle.com/datasets/programmer3/e-commerce-customer-behavior-dataset
- **Content**: Customer journey data with touchpoints
- **Key Fields**:
  - `customer_id`
  - `session_id`
  - `touchpoint_sequence`: Email, Ad, Website, etc.
  - `conversion`: Binary outcome
  - `time_to_conversion`

**Use Case**: Test attribution models (first-touch, last-touch, Shapley, Markov chain)

#### 2. Marketing Attribution Datasets (Kaggle)
- Search: "marketing attribution", "customer journey", "multi-touch attribution"
- **Use Case**: Validate psychographic weighting in attribution engine

**Prototype Flow**:
```
Touchpoint Sequence → Markov Transition Matrix → Shapley Value → Weighted Attribution
                                                        ↓
                                                Psychographic Modifier
```

---

## Integration Priority

### Immediate (Week 1-2)
1. NOAA Storm Events → calibrate SII
2. TxGIO Parcels → spatial joins
3. Census ACS → SES segmentation

### Short-term (Month 1)
4. Dallas Permits → competition + roof age
5. CLIMADA → validate MOE

### Medium-term (Month 2-3)
6. AIRS/RoofNet → roof detection models
7. Crime data → risk scoring

### Long-term (Month 3+)
8. Roboflow damage datasets → CV pipeline
9. Behavioral datasets → attribution sandbox

---

## Next: Data Lake Schema

See `stormops_data_lake_schema.md` for the unified table blueprint showing how all sources join via:
- `parcel_id`
- `tract_id` (census GEOID)
- `event_id` (storm events)
- `claim_id` (insurance claims)
- `image_id` (aerial/drone imagery)

---

## References

Content was rephrased for compliance with licensing restrictions.

[1] NOAA Storm Events Database - https://www.ncei.noaa.gov/stormevents/
[2] CLIMADA Hail Damage Model - https://nhess.copernicus.org/articles/24/847/2024/
[3] AIRS Roof Segmentation - https://daoqiqi.github.io/assets/img/achievements/airs.pdf
[4] RoofNet Dataset - https://arxiv.org/html/2505.19358v1
[5] TxGIO StratMap Parcels - https://tnris.org/stratmap/land-parcels/
[6] Dallas Building Permits - https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/pages/online-records.aspx
[7] Fort Worth Crime Data - https://police.fortworthtexas.gov/Crime-Public-Info/Crime-Data-Center
[8] Roboflow Damage Datasets - https://universe.roboflow.com/search?q=class%3Ahail+damage
[9] Building Damage Segmentation - https://github.com/LysanetsAndriy/Building-damage-segmentation
[10] Kaggle E-Commerce Behavior - https://www.kaggle.com/datasets/programmer3/e-commerce-customer-behavior-dataset
