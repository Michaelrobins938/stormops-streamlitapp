# Data Quality & Feature Engineering Framework

## Overview

Rigorous data quality framework implementing the **6 dimensions of data quality** with automated validation, cleaning, and feature engineering for StormOps targeting and ML models.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   INTEGRATED PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Data Quality & Validation (data_quality.py)             │
│     ├─ Completeness checks (95% threshold)                  │
│     ├─ Validity checks (98% threshold)                      │
│     ├─ Uniqueness checks (99% threshold)                    │
│     ├─ Integrity checks (95% threshold)                     │
│     ├─ Outlier detection (IQR method)                       │
│     └─ Automated fixes & recalculation                      │
│                                                              │
│  2. Data Enrichment (enrich_normalize_data.py)              │
│     ├─ Property attributes (value, sqft, age, type)         │
│     ├─ Address normalization                                │
│     ├─ Risk scoring (0-100 scale)                           │
│     └─ Census tract linkage                                 │
│                                                              │
│  3. External Enrichment (external_data_copilot.py)          │
│     ├─ Census SES data (645 tracts)                         │
│     ├─ Psychographic segmentation (4 personas)              │
│     └─ NOAA weather triggers                                │
│                                                              │
│  4. Feature Engineering (feature_engineering.py)            │
│     ├─ Interaction features (age×risk, value×SES)           │
│     ├─ Scaled features (RobustScaler)                       │
│     ├─ Ratio features (sqft/value)                          │
│     └─ Model feature view (26 features)                     │
│                                                              │
│  5. Targeting Engine (targeting_engine.py)                  │
│     ├─ Play recommendations (11 plays)                      │
│     ├─ SII boost calculations                               │
│     ├─ Operator views (5 views)                             │
│     └─ Territory campaign plans                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Quality Framework

### Six Dimensions Implemented

#### 1. Completeness (95% threshold)
Required fields must be populated:
- Properties: `property_id`, `address`, `city`, `state`, `zip_code`, `census_tract_geoid`, `estimated_value`, `square_footage`
- Census: `tract_geoid`, `median_household_income`, `median_home_value`
- Psychographics: `property_id`, `primary_persona`

#### 2. Validity (98% threshold)
Values must be in reasonable ranges:
```python
CONSTRAINTS = {
    'properties': {
        'estimated_value': (50000, 5000000),
        'square_footage': (500, 10000),
        'year_built': (1900, 2026),
        'risk_score': (0, 100),
        'price_per_sqft': (20, 1000)
    },
    'census_tracts': {
        'median_household_income': (0, 500000),
        'median_home_value': (0, 5000000),
        'homeownership_rate': (0, 100),
        'affordability_index': (0, 200)
    }
}
```

**Automated Fixes:**
- Nullify negative income/home values
- Cap extreme property values at upper bounds
- Bound risk scores to 0-100
- Bound psychographic scores to 0-100

#### 3. Consistency
No conflicting values across joins - same `property_id` always maps to same address/tract.

#### 4. Accuracy
Spot-check against reference data:
- Census values validated against known Dallas County ranges
- Property values validated against market data

#### 5. Uniqueness (99% threshold)
No duplicates on key fields:
- Properties: `property_id`
- Census tracts: `tract_geoid`
- Psychographic profiles: `property_id`

#### 6. Integrity (95% threshold)
Foreign keys must resolve:
- `properties.census_tract_geoid` → `census_tracts.tract_geoid`
- `psychographic_profiles.property_id` → `properties.property_id`

### Outlier Detection

**IQR Method:**
```python
Q1 = quantile(0.25)
Q3 = quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
```

Applied to: `estimated_value`, `square_footage`, `risk_score`

**Handling:**
- Domain validation first (hard bounds)
- IQR detection for statistical outliers
- Log counts of adjustments
- Winsorize or cap based on domain knowledge

---

## Feature Engineering

### Interaction Features

**1. Age × Risk Interaction**
```sql
age_risk_interaction = property_age * risk_score / 100.0
```
Captures compounding effect of old properties in high-risk areas.

**2. Value × SES Interaction**
```sql
value_ses_interaction = (estimated_value / 100000) * (median_household_income / 10000)
```
Captures property value relative to neighborhood affluence.

**3. Sqft/Value Ratio**
```sql
sqft_value_ratio = square_footage / estimated_value
```
Efficiency metric - higher ratio = more space per dollar.

### Scaled Features

**RobustScaler** (less sensitive to outliers than StandardScaler):
- `estimated_value_scaled`
- `square_footage_scaled`
- `property_age_scaled`
- `price_per_sqft_scaled`
- `median_household_income_scaled`
- `median_home_value_scaled`

### Model Feature View

**26 features available** in `model_features` view:

| Category | Features | Count |
|----------|----------|-------|
| Raw | value, sqft, age, risk, price_per_sqft | 5 |
| Scaled | value_scaled, sqft_scaled, age_scaled | 3 |
| Interactions | age_risk, value_ses, sqft_ratio | 3 |
| Psychographic | persona, risk_tolerance, price_sensitivity | 3 |
| SES | income, home_value, homeownership, affordability | 4 |
| Targeting | play, sii_score, sla_hours | 3 |
| Identifiers | property_id, address, city, zip | 4 |

---

## Usage

### Run Full Pipeline

```bash
python3 run_pipeline.py
```

Executes all stages in order:
1. Data quality validation
2. Data enrichment
3. External enrichment
4. Feature engineering
5. Targeting engine

**Exit codes:**
- `0` = All stages passed
- `1` = Pipeline failed (check logs)

### Run Individual Stages

```bash
# Quality checks only
python3 data_quality.py

# Enrichment only
python3 enrich_normalize_data.py

# Feature engineering only
python3 feature_engineering.py

# Targeting only
python3 targeting_engine.py
```

### Query Model Features

```sql
-- All features for ML training
SELECT * FROM model_features;

-- High-priority targets with features
SELECT * FROM model_features 
WHERE sii_score >= 90
ORDER BY sii_score DESC;

-- Features by persona
SELECT 
    primary_persona,
    AVG(risk_score) as avg_risk,
    AVG(estimated_value) as avg_value,
    AVG(age_risk_interaction) as avg_age_risk
FROM model_features
GROUP BY primary_persona;
```

---

## Model Integration

### SII Feature Engineering

Add these features to SII models:
```python
sii_features = [
    'sii_score',              # Base SII + play boost
    'risk_score',             # Property-level risk
    'age_risk_interaction',   # Age × risk compound
    'value_ses_interaction',  # Value × SES compound
    'price_sensitivity',      # Persona-derived
    'risk_tolerance',         # Persona-derived
    'affordability_index',    # Tract-level SES
    'estimated_value_scaled', # Normalized value
    'property_age_scaled'     # Normalized age
]
```

### MOE Priors by Segment

```python
moe_priors = {
    ('Deal_Hunter', 'High'): 0.35,
    ('Deal_Hunter', 'Very High'): 0.40,
    ('Proof_Seeker', 'High'): 0.28,
    ('Proof_Seeker', 'Very High'): 0.32,
    ('Family_Protector', 'High'): 0.30,
    ('Family_Protector', 'Very High'): 0.33,
    ('Status_Conscious', 'High'): 0.25,
    ('Status_Conscious', 'Very High'): 0.28
}
```

### SHAP/Feature Importance

Validate feature contributions:
```python
import shap

# Load model and data
model = load_sii_model()
X = pd.read_csv('model_features.csv')

# Calculate SHAP values
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

# Plot feature importance
shap.summary_plot(shap_values, X)
```

Expected high-importance features:
- `sii_score` (by design)
- `risk_score`
- `age_risk_interaction`
- `price_sensitivity` (for Deal_Hunter)
- `risk_tolerance` (for Proof_Seeker)

---

## Quality Thresholds

```python
@dataclass
class QualityThresholds:
    completeness_min: float = 0.95  # 95% of required fields populated
    validity_min: float = 0.98      # 98% of values in valid ranges
    uniqueness_min: float = 0.99    # 99% unique on key fields
    integrity_min: float = 0.95     # 95% of FKs resolve
```

**Adjust thresholds** in `data_quality.py` based on data maturity:
- Early stage: Lower to 0.90-0.95
- Production: Keep at 0.95-0.99
- Critical systems: Raise to 0.99+

---

## Outputs

### Files
- `model_features.csv` - 100 rows × 26 features, ready for ML training

### Database Tables
- `properties` - Enriched with 15+ derived columns
- `census_tracts` - 645 tracts with SES metrics
- `psychographic_profiles` - 100 persona assignments
- `targeting_recommendations` - 100 play recommendations

### Database Views
- `model_features` - All features joined for ML
- `high_priority_targets` - SII ≥ 70 outreach queue
- `zip_campaign_summary` - Territory planning aggregations
- `financing_campaign_targets` - Deal_Hunter filtering
- `premium_upsell_targets` - High-value opportunities

---

## Monitoring & Maintenance

### Daily Checks
```bash
# Run quality checks
python3 data_quality.py

# Check for new data quality issues
psql -c "SELECT COUNT(*) FROM properties WHERE risk_score IS NULL;"
```

### Weekly Maintenance
```bash
# Re-run full pipeline
python3 run_pipeline.py

# Export fresh model features
psql -c "\copy (SELECT * FROM model_features) TO 'model_features.csv' CSV HEADER;"
```

### Monthly Review
- Review SHAP feature importance
- Adjust quality thresholds if needed
- Update domain constraints based on market changes
- Retrain SII/MOE models with new features

---

## Troubleshooting

### Pipeline Fails at Quality Stage
- Check `data_quality.py` output for specific failures
- Review invalid values: `SELECT * FROM properties WHERE estimated_value < 0;`
- Adjust constraints if domain knowledge supports it

### Negative Census Values
- Already handled by automated fixes
- If persists, check source data: `SELECT * FROM census_tracts WHERE median_household_income < 0;`

### Missing Features
- Check feature coverage: `SELECT COUNT(age_risk_interaction) FROM properties;`
- Re-run feature engineering: `python3 feature_engineering.py`

### Low Model Performance
- Check SHAP values for feature contributions
- Verify scaled features are being used
- Add more interaction terms if needed

---

## References

- [Six Dimensions of Data Quality](https://www.collibra.com/blog/the-6-dimensions-of-data-quality)
- [Outlier Handling Best Practices](https://statisticsbyjim.com/basics/remove-outliers/)
- [Feature Engineering for Risk Models](https://www.tencentcloud.com/techpedia/125555)
- [Data Quality in ML Pipelines](https://pmc.ncbi.nlm.nih.gov/articles/PMC12721946/)

---

**Status:** ✅ Production-ready  
**Last Updated:** 2026-02-07  
**Maintainer:** StormOps Data Team
