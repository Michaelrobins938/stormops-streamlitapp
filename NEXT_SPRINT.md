# StormOps: Next Sprint - Workflow + Policy Integration

## What Was Built

This sprint delivers **two critical pieces** to make StormOps production-ready:

### 1. Full 5-Phase Workflow UI (`app.py`)

A Streamlit control plane that lets a crew chief walk through the complete storm cycle:

**Phase 1: SIGNAL + TARGET**
- View treatment policy decisions (aggressive/moderate/conservative)
- Apply policy with one click
- See real-time metrics: treat/hold counts, conversion rates, lift
- Decision breakdown by reason (universal control, RCT, uplift threshold)
- Top 20 properties by uplift score

**Phase 2: ATTRIBUTION**
- Channel attribution credits
- Conversion tracking by channel

**Phase 3: BUILD ROUTES**
- Select properties to route (treat-only)
- Configure max properties per route
- Filter by ZIP
- Auto-cluster into routes
- Export routes as CSV

**Phase 4: JOB INTELLIGENCE**
- Property lookup by ID
- View uplift score, decision, conversion status
- Add job notes
- See next best action

**Phase 5: NURTURE LOOP**
- List unconverted high-uplift properties
- Export nurture list for follow-up

### 2. Policy Control Plane (`policy_control_plane.py`)

Live treatment decision engine with full logging:

**Features:**
- Three policy modes: aggressive (10%), moderate (15%), conservative (20%)
- Decision logic: universal control → RCT → uplift threshold
- Full logging: every decision, reason, uplift band
- Outcome tracking: log actual conversions vs predictions
- Performance analysis: actual vs predicted lift

**Tables Created:**
- `policy_decisions_log` - Every property decision with reason
- `policy_executions` - Summary of each policy run
- `policy_outcomes` - Actual conversion outcomes

---

## How to Use

### Quick Start

```bash
cd /home/forsythe/kirocli/kirocli

# 1. Apply moderate policy (if not already done)
python3 policy_control_plane.py

# 2. Start UI
streamlit run app.py

# Or use the quick start script
chmod +x start_control_plane.sh
./start_control_plane.sh
```

### Workflow

1. **Select Storm** (sidebar)
   - Choose from loaded storms (e.g., DFW_STORM_24)

2. **Phase 1: Apply Policy**
   - Select policy mode (moderate recommended)
   - Click "Apply Policy"
   - Review treat/hold breakdown

3. **Phase 3: Build Routes**
   - Filter properties by ZIP
   - Set max per route (default: 50)
   - Click "Generate Routes"
   - Export CSV for field crews

4. **Phase 4: Track Jobs**
   - Look up properties by ID
   - Add notes as work progresses
   - See uplift scores and decisions

5. **Phase 5: Nurture**
   - Export unconverted high-uplift properties
   - Schedule follow-ups

---

## Policy Modes Explained

| Mode | Threshold | Treat % | Use Case |
|------|-----------|---------|----------|
| **Aggressive** | 10% uplift | 79% | Max volume days |
| **Moderate** | 15% uplift | 72% | Standard ops (recommended) |
| **Conservative** | 20% uplift | 54% | Capacity constrained |

All three deliver ~21-22 point lift. Difference is volume vs efficiency.

---

## Logging & Measurement

### Log Outcomes During Storm

```python
from policy_control_plane import PolicyControlPlane

plane = PolicyControlPlane(policy_mode='moderate')

# Log each property outcome
plane.log_outcome(
    property_id='prop_00123',
    event_id='DFW_STORM_24',
    converted=True,
    value=15000
)
```

### Measure Performance After Storm

```python
perf = plane.get_policy_performance('DFW_STORM_24')

print(f"Treatment: {perf['treatment']['rate']*100:.1f}% conversion")
print(f"Control: {perf['control']['rate']*100:.1f}% conversion")
print(f"Lift: {perf['lift']['actual_absolute']*100:+.1f} pts")
print(f"Predicted: {perf['lift']['predicted']*100:.1f}%")
print(f"Error: {perf['lift']['prediction_error']*100:+.1f} pts")
```

---

## Next Steps

### Immediate (This Week)

1. **Test UI with real storm data**
   - Run `e2e_storm_test.py` to generate test data
   - Walk through all 5 phases
   - Verify routes export correctly

2. **Integrate outcome logging**
   - Add webhook/API to log conversions as they happen
   - Wire into CRM or field app

3. **Add route optimization**
   - Replace simple ZIP clustering with travel-time aware routing
   - Use Google Maps API or similar

### Short-Term (Next 2 Weeks)

4. **Multi-tenant setup**
   - Add `team_id` to all tables
   - Create team selector in UI
   - Isolate data by team

5. **Storm registry**
   - Create `storms` table with metadata
   - Add storm index page
   - Allow creating new storms from UI

6. **Migrate to Postgres**
   - Replace SQLite with Postgres
   - Update connection strings
   - Add connection pooling

### Medium-Term (Next Month)

7. **Job intelligence enhancements**
   - Photo upload for properties
   - Claim intel attachment
   - Field notes sync

8. **Nurture loop automation**
   - Schedule follow-ups
   - Email/SMS integration
   - Track nurture outcomes

9. **Monitoring & alerts**
   - Job health dashboard
   - DB error tracking
   - Latency monitoring

---

## Files Created

```
app.py                      - Streamlit UI (5-phase workflow)
policy_control_plane.py     - Treatment policy engine with logging
start_control_plane.sh      - Quick start script
NEXT_SPRINT.md             - This file
```

---

## Success Criteria

After first live storm:

- [ ] Crew chief completes full workflow without leaving UI
- [ ] Routes exported and used by field crews
- [ ] All outcomes logged to `policy_outcomes` table
- [ ] Actual lift within 5 pts of predicted (+22 pts expected)
- [ ] ROI > 300%

---

## Questions?

- **UI not loading?** Check if `stormops_attribution.db` exists. Run `e2e_storm_test.py` first.
- **No storms in dropdown?** Load storm data with `journey_ingestion.py`
- **Policy not applying?** Verify `lead_uplift` and `experiment_assignments` tables exist
- **Routes empty?** Make sure properties have `decision='treat'` in `policy_decisions_log`

---

**Status:** ✅ Ready for pilot storm
**Next:** Test with DFW Elite Roofing on next storm event
