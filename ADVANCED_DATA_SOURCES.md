# Advanced Data Sources - Quick Reference

## 🎯 Priority Order: Insurance Economics + Hazard Physics

### 1. Texas DOI Insurance Data (✅ DEPLOYED)
**Status:** Schema ready, synthetic data loaded  
**Source:** https://www.tdi.texas.gov/reports/report4.html  
**Table:** `tdi_zip_insurance`  
**Join:** `zip_code`

**Features Added:**
- `insurance_burden_ratio` - Premium / income (1.5% - 6.2%)
- `market_opportunity_score` - Loss ratio + competition (0-100)

**Query:**
```sql
SELECT * FROM enhanced_risk_scoring 
WHERE market_opportunity_score >= 80 
  AND insurance_burden_ratio < 0.04;
```

**Next:** Replace synthetic with real TDI data

---

### 2. FHFA Mortgage Data (🟡 READY)
**Status:** Schema ready, awaiting data  
**Source:** https://www.fhfa.gov/data/datasets  
**Table:** `fhfa_tract_data`  
**Join:** `census_tract_geoid`

**Features to Add:**
- `equity_risk_score` - LTV-based risk (0-100)
- `hpi_index` - House price index
- `hpi_yoy_change` - Price momentum

**Acquisition:**
1. Download Census Tract HPI: https://www.fhfa.gov/DataTools/Downloads/Pages/HPI.aspx
2. Parse CSV, load to `fhfa_tract_data`
3. Run feature engineering

**Impact:** Refine MOE priors by equity position

---

### 3. CLIMADA Hail Model (🟡 READY)
**Status:** Schema ready, awaiting model run  
**Source:** https://github.com/CLIMADA-project/climada_python  
**Table:** `climada_hail_hazard`  
**Join:** `tract_geoid` OR `zip_code`

**Features to Add:**
- `physics_risk_score` - Damage probability (0-100)
- `climada_hail_hazard` - Hazard intensity
- `return_period_10yr` - 10-year return period

**Acquisition:**
1. Clone CLIMADA: `git clone https://github.com/CLIMADA-project/climada_python`
2. Run hail model for Dallas County
3. Export hazard maps, load to `climada_hail_hazard`

**Impact:** Independent physics validation, strategic market selection

---

## 🔧 Model Integration

### SII Features (add 4)
```python
new_features = [
    'insurance_burden_ratio',    # Premium affordability
    'equity_risk_score',          # LTV-based risk
    'market_opportunity_score',   # Market dynamics
    'physics_risk_score'          # CLIMADA hazard
]
```

### MOE Priors (by equity)
```python
moe_adjustments = {
    'high_equity': 0.8,    # LTV < 0.6
    'moderate': 1.0,       # LTV 0.6-0.8
    'low_equity': 1.3      # LTV > 0.8
}
```

### Targeting Rules
```python
if insurance_burden_ratio > 0.04:
    messaging = "savings_efficiency"
elif market_opportunity_score > 80:
    play_aggressiveness = "high"
elif equity_risk_score > 70:
    moe_prior *= 1.3  # Less likely to invest
```

---

## 📊 Current Status

| Source | Status | Records | Features | Impact |
|--------|--------|---------|----------|--------|
| TDI | ✅ Loaded | 38 ZIPs | 2 | Immediate |
| FHFA | 🟡 Ready | 0 | 1 | High |
| CLIMADA | 🟡 Ready | 0 | 1 | High |

**Total New Features:** 4 (2 populated, 2 ready)

---

## 🚀 Next Steps

**This Week:**
1. Acquire real TDI data
2. Query high-opportunity properties
3. Integrate into targeting engine

**This Month:**
1. Acquire FHFA data
2. Add to SII model
3. Validate with SHAP

**This Quarter:**
1. Run CLIMADA model
2. Strategic market expansion
3. Physics-based risk refinement

---

## 📁 Files

- `advanced_data_ingestion.py` - Framework setup
- `load_tdi_data.py` - TDI loader (ready)
- `load_fhfa_data.py` - FHFA loader (TODO)
- `load_climada_data.py` - CLIMADA loader (TODO)

---

**Last Updated:** 2026-02-07  
**Status:** Framework deployed, ready for data acquisition
