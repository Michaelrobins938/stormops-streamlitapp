# StormOps Data Enrichment & Targeting Summary

## 🎯 Mission Accomplished

Transformed raw property data into **actionable targeting intelligence** with persona-driven playbook recommendations.

---

## 📊 Data Pipeline

### 1. Base Data (100 properties)
- ✅ Addresses normalized (INITCAP, trimmed)
- ✅ Property attributes enriched (value, sqft, age, type)
- ✅ 100% census tract linkage

### 2. External Enrichment
- ✅ Census SES data (645 tracts)
  - Median household income
  - Median home value
  - Homeownership rates
  - Affordability indices
- ✅ Psychographic segmentation (100 profiles)
  - 32 Proof_Seekers (technical, documentation-driven)
  - 32 Deal_Hunters (price-sensitive, financing-focused)
  - 29 Family_Protectors (safety, warranty-focused)
  - 7 Status_Conscious (premium, aesthetic-focused)

### 3. Risk Scoring
- ✅ 100 properties scored (0-100 scale)
  - 4 Low risk (0-39)
  - 27 Medium risk (40-59)
  - 38 High risk (60-79)
  - 31 Very High risk (80+)
- Factors: property age, tract income, home values, homeownership

### 4. Targeting Engine
- ✅ 100 play recommendations generated
- ✅ 11 distinct plays mapped to persona × risk combinations
- ✅ SII boost calculations (base + play-specific)
- ✅ Follow-up SLA assignments (12-72 hours)

---

## 🎯 Targeting Outputs

### High-Priority Plays (SII ≥ 90)

| Play | Count | Avg SII | Avg Value | SLA (hrs) |
|------|-------|---------|-----------|-----------|
| Financing_Aggressive | 12 | 106 | $376k | 12 |
| Impact_Report_Premium | 9 | 99 | $337k | 24 |
| Premium_Showcase | 5 | 100 | $272k | 24 |
| Safety_Warranty | 5 | 95 | $233k | 24 |

### Territory Campaigns (Top ZIPs)

| ZIP | Properties | Avg SII | Dominant Persona | Suggested Play |
|-----|------------|---------|------------------|----------------|
| 75227 | 3 | 97 | Deal_Hunter | Financing_Aggressive |
| 75224 | 5 | 92 | Family_Protector | Premium_Showcase |
| 75238 | 3 | 89 | Deal_Hunter | Financing_Aggressive |
| 75231 | 5 | 88 | Proof_Seeker | Impact_Report_Premium |

---

## 📋 Operator Views Created

### 1. `high_priority_targets`
**Purpose:** Daily outreach queue  
**Filter:** SII ≥ 70, sorted by priority + SLA  
**Use case:** Rep assignment, immediate follow-ups

### 2. `urgent_follow_ups`
**Purpose:** Time-sensitive leads  
**Filter:** SLA ≤ 24 hours  
**Use case:** Same-day/next-day scheduling

### 3. `financing_campaign_targets`
**Purpose:** Promo/financing campaigns  
**Filter:** Deal_Hunter persona, high price sensitivity  
**Use case:** Batch financing offers, seasonal promos

### 4. `premium_upsell_targets`
**Purpose:** High-margin material sales  
**Filter:** Proof_Seeker + Status_Conscious, value > $300k  
**Use case:** Designer materials, premium upgrades

### 5. `zip_campaign_summary`
**Purpose:** Territory planning  
**Aggregation:** Property count, persona mix, avg metrics by ZIP  
**Use case:** Territory assignment, batch campaigns

---

## 🔧 Model Integration Points

### SII Feature Engineering
Add these features to SII models:
```python
features = [
    'sii_with_boost',      # Base SII + play-specific boost
    'risk_score',          # Property-level risk (0-100)
    'price_sensitivity',   # Persona-derived (0-100)
    'risk_tolerance',      # Persona-derived (0-100)
    'affordability_index', # Tract-level SES metric
    'property_age',        # Years since built
    'estimated_value'      # Property value
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
    ('Status_Conscious', 'High'): 0.25
}
```

### Playbook Config Overrides
Use persona to set:
- Default material recommendations
- Messaging emphasis (financing vs technical vs safety)
- Follow-up cadence
- Content type (promo vs documentation)

---

## 📈 Data Quality Metrics

| Entity | Total | Completeness |
|--------|-------|--------------|
| Properties | 100 | 100% enriched |
| Census Tracts | 645 | 99% enriched |
| Psychographic Profiles | 100 | 100% assigned |
| Targeting Recommendations | 100 | 100% generated |

**Key Stats:**
- 100% address normalization
- 100% census linkage
- 100% risk scoring
- 100% persona assignment
- 100% play recommendations

---

## 🚀 Immediate Actions

### Today
1. Query `high_priority_targets` WHERE `priority_score >= 100`
2. Assign 7 Financing_Aggressive leads to reps (12hr SLA)
3. Assign 9 Impact_Report_Premium leads to technical team (24hr SLA)

### This Week
1. Launch ZIP 75227 financing blitz (3 properties, avg SII 97)
2. Launch ZIP 75231 technical documentation campaign (5 properties)
3. A/B test play messaging variants

### This Month
1. Retrain SII model with enriched features
2. Update MOE priors by persona segment
3. Feed play outcomes back to targeting engine
4. Expand to additional ZIPs/markets

---

## 📁 Key Files

- `enrich_normalize_data.py` - Data enrichment pipeline
- `external_data_copilot.py` - Census + psychographic enrichment
- `targeting_engine.py` - Play recommendation engine
- `PLAYBOOK_CONFIG.md` - Playbook definitions and configs

## 🗄️ Key Tables

- `properties` - Base property data (enriched)
- `census_tracts` - SES demographic data
- `psychographic_profiles` - Persona assignments
- `targeting_recommendations` - Play recommendations + SII scores

## 📊 Key Views

- `property_enrichment` - Complete property + census data
- `high_priority_targets` - Top outreach queue
- `zip_campaign_summary` - Territory planning
- `financing_campaign_targets` - Financing campaign filter
- `premium_upsell_targets` - Premium material filter

---

**Status:** ✅ Production-ready  
**Last Updated:** 2026-02-07  
**Next Review:** After first campaign results
