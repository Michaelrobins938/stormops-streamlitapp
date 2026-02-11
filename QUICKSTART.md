# StormOps v2.0.0 Quick Start Guide

## 🚀 5-Minute Setup

### Prerequisites
- PostgreSQL 14+ with PostGIS
- Python 3.9+
- 4GB RAM minimum

### Installation

```bash
cd /home/forsythe/kirocli/kirocli

# Run deployment script
./deploy_complete.sh

# Start application
streamlit run app_v2.py
```

Open browser to `http://localhost:8501`

---

## 📊 First Storm Workflow

### Step 1: Create Tenant (One-time)
```sql
INSERT INTO tenants (tenant_id, org_name, status)
VALUES (gen_random_uuid(), 'Acme Roofing DFW', 'active');
```

### Step 2: Create Storm
```sql
INSERT INTO storms (storm_id, tenant_id, event_id, name, status)
VALUES (
    gen_random_uuid(),
    '<your_tenant_id>',
    'DFW-2026-02',
    'Dallas Hailstorm Feb 2026',
    'active'
);
```

### Step 3: Load Earth-2 Data
1. Navigate to **Tactical Map** tab
2. Enter coordinates: `32.7767, -96.7970` (Dallas)
3. Set radius: `50 km`
4. Click **"Load Earth-2 Swath"**

Result: 5-10 impact zones created with 1km resolution

### Step 4: Initialize Markov States
1. Navigate to **Markov States** tab
2. Click **"Initialize Markov States"**
3. Click **"Trigger Earth-2 Transitions"**

Result: ZIPs transition from baseline → pre-impact → impact

### Step 5: Let AI Propose Actions
1. Scroll to **AI Action Queue** (right sidebar)
2. Click **"AI: Analyze & Propose Actions"**
3. Review proposals (e.g., "Generate routes for ZIP 75024")
4. Click **"Approve"** → **"Execute"**

Result: Routes generated, TAM calculated, crews can be assigned

---

## 🎯 Key Features Demo

### Hybrid Attribution (α-Sweep)

Navigate to **Hybrid Attribution** tab:

1. **Adjust α slider:**
   - α = 0.0 → Pure Markov (causal)
   - α = 0.5 → Hybrid
   - α = 1.0 → Pure Shapley (fair)

2. **Run α-Sweep:**
   - Click "Run α-Sweep"
   - See how channel credit changes with fairness vs. causality

3. **Check Saturation:**
   - Select channel: `door_knock`
   - Select ZIP: `75024`
   - Click "Check Saturation"
   - Get recommendation: Saturated/Optimal/Undersaturated

### Identity Resolution

Navigate to **Identity Graph** tab:

- View all resolved property identities
- See confidence scores (target: >0.8)
- Check household linkages

### Operational Score

Left sidebar shows real-time score (0-100):

- **Components:**
  - Validated Leads: 40%
  - Route Efficiency: 30%
  - SLA Compliance: 30%

- **Gap Analysis:**
  - Shows points needed to reach 100
  - Suggests next best action

---

## 🧪 Testing

### Run Integration Test
```bash
python3 test_integration.py
```

Expected output:
```
✅ Created 8 Earth-2 impact zones
✅ Initialized 5 ZIP states
✅ Transitions: {'baseline_to_pre': 2, 'pre_to_impact': 1}
✅ AI proposed 3 actions
```

### Synthetic Ground Truth Test
```python
from bayesian_mmm import SyntheticGroundTruth, BayesianMMM

sgt = SyntheticGroundTruth(db_url)
df, true_params = sgt.generate_synthetic_data(n_obs=50)

mmm = BayesianMMM(db_url)
# trace = mmm.fit(df, channels=['test_channel'])
# validation = sgt.validate_model(mmm, true_params)
# print(f"ACE: {validation['ace']:.2%}")  # Target: <5%
```

---

## 📈 Production Checklist

### Before Launch

- [ ] Change database password from default
- [ ] Set up NVIDIA Earth-2 API key
- [ ] Configure ServiceTitan/JobNimbus webhooks
- [ ] Set up Twilio for SMS campaigns
- [ ] Define Hill function parameters per channel
- [ ] Calibrate Markov transition matrix with historical data
- [ ] Run synthetic ground truth validation (ACE < 5%)
- [ ] Set up monitoring for R-Hat convergence
- [ ] Configure backup and disaster recovery

### Weekly Operations

- [ ] Run α-sweep analysis
- [ ] Check Brier scores (target: <0.12)
- [ ] Review saturation status by ZIP
- [ ] Validate Markov state transitions
- [ ] Run synthetic ground truth test
- [ ] Review Operational Score trends
- [ ] Audit identity resolution accuracy

---

## 🔧 Troubleshooting

### "No tenants found"
```sql
-- Check tenants
SELECT * FROM tenants;

-- Create if missing
INSERT INTO tenants (tenant_id, org_name, status)
VALUES (gen_random_uuid(), 'Test Tenant', 'active');
```

### "PostGIS not found"
```bash
psql -U stormops -d stormops -c "CREATE EXTENSION postgis;"
```

### "Module not found"
```bash
# Ensure you're in the correct directory
cd /home/forsythe/kirocli/kirocli

# Reinstall dependencies
pip install -r requirements.txt
```

### "Earth-2 data not loading"
- Check system vitality in left sidebar
- Verify Earth-2 service shows "healthy"
- If degraded, check API key and network

### "Markov states not transitioning"
```sql
-- Check current states
SELECT zip_code, current_state, state_entered_at
FROM markov_zip_states
WHERE storm_id = '<your_storm_id>';

-- Manually trigger transition
SELECT transition_markov_state(
    '<state_id>',
    'recovery',
    'manual_trigger'
);
```

---

## 📚 Advanced Usage

### Custom Attribution Model

```python
from hybrid_attribution import HybridAttributionEngine

engine = HybridAttributionEngine(db_url)

# Custom α for specific analysis
attribution = engine.attribute_journey(
    tenant_id, storm_id, property_id,
    journey_path=['earth2_alert', 'door_knock', 'sms', 'call'],
    alpha=0.3  # More weight on causality
)
```

### Custom MMM Parameters

```sql
-- Update channel parameters
UPDATE mmm_channels
SET saturation_k = 200,  -- Increase half-saturation point
    saturation_s = 1.5   -- Steeper curve
WHERE channel_name = 'door_knock';
```

### Custom Uplift Segmentation

```python
from hybrid_attribution import UpliftModeling

uplift = UpliftModeling(db_url)

segment = uplift.segment_by_uplift(
    property_id,
    cate=0.18,  # 18% uplift
    confidence_interval=(0.12, 0.24)
)
# Returns: 'persuadable'
```

---

## 🎓 Learning Resources

### Key Concepts

1. **Markov Removal Effect:** Measures causal contribution of a channel by comparing conversion rates with/without it

2. **Shapley Value:** Axiomatic fair credit allocation based on marginal contributions across all possible orderings

3. **Weibull Adstock:** Models memory decay of marketing effects over time

4. **Hill Saturation:** Models diminishing returns as marketing intensity increases

5. **T-Learner:** Meta-learner for estimating Conditional Average Treatment Effect (CATE)

### Formulas

**Hybrid Attribution:**
```
H_i = α·S_i + (1-α)·M_i
```

**Weibull Adstock:**
```
w(l) = (α/θ)·(l/θ)^(α-1)·exp(-(l/θ)^α)
```

**Hill Saturation:**
```
f(x) = x^s / (k^s + x^s)
```

**Brier Score:**
```
BS = (1/n)·Σ(p_i - o_i)²
```

---

## 🆘 Support

### Documentation
- Full PRD: `STORMOPS_PRD_FINAL.md`
- Technical README: `README_STORMOPS_V2.md`
- AI System Prompt: `ai_system_prompt.py`

### Code Structure
```
kirocli/
├── schema_stormops_v2.sql          # Core database schema
├── schema_marketing_science.sql    # Attribution & MMM schema
├── earth2_integration.py           # NVIDIA Earth-2 client
├── markov_engine.py                # State prediction
├── identity_resolver.py            # Probabilistic matching
├── sidebar_agent.py                # AI action queue
├── hybrid_attribution.py           # Markov-Shapley engine
├── bayesian_mmm.py                 # PyMC MMM implementation
├── app_v2.py                       # Main Streamlit UI
├── test_integration.py             # End-to-end tests
└── deploy_complete.sh              # Deployment script
```

### Common Issues

**Issue:** Operational Score stuck at 0
**Solution:** Run `SELECT calculate_operational_score('<tenant_id>', '<storm_id>')`

**Issue:** Attribution shows no data
**Solution:** Ensure journeys are logged in `customer_journeys_v2` table

**Issue:** Saturation always shows "undersaturated"
**Solution:** Adjust `saturation_k` parameter in `mmm_channels` table

---

## 🎯 Success Metrics

Track these KPIs weekly:

1. **Incremental Intent:** >60% of leads are truly incremental
2. **Conversion Velocity:** <72h from post-storm to contract
3. **Operational Score:** >80/100 sustained
4. **Attribution Stability:** <15% variance across α-sweep
5. **Model Calibration:** Brier score <0.12

---

**Version:** 2.0.0  
**Last Updated:** February 7, 2026  
**Status:** Production-Ready
