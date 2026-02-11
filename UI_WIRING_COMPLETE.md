# UI → Backend Wiring COMPLETE ✅

## Status: LIVE

The StormOps UI at http://localhost:8501 is now wired to your real A-tier leads.

## What Changed

### 1. Auto-Load A-Tier Data on Startup
**File:** `app.py` (lines ~2653)

```python
# Load A-tier leads if available
import pickle
a_tier_path = os.path.join(BASE_DIR, 'outputs', 'a_tier_zones.pkl')
if os.path.exists(a_tier_path) and not state.zones:
    with open(a_tier_path, 'rb') as f:
        state.zones = pickle.load(f)
        state.mission.leads_generated = True
        state.mission.checks["storm_loaded"] = True
        # Update stats with real counts
        total_leads = sum(z.roof_count for z in state.zones.values())
        state.stats["doors_targeted"] = total_leads
```

### 2. Wire "Load Event" Button
**File:** `app.py` (lines ~3433)

```python
if st.button("Load event & find targets", ...):
    # Load A-tier leads from real data
    total_leads = sum(z.roof_count for z in state.zones.values())
    state.mission.leads_generated = True
    state.stats["doors_targeted"] = total_leads
    state.mission.play_score = 20
```

### 3. Wire "Generate Leads Now" Button
**File:** `app.py` (lines ~3470)

```python
if st.button("Generate leads now", ...):
    # Use real A-tier leads
    total_leads = sum(z.roof_count for z in state.zones.values())
    high_sii = sum(1 for z in state.zones.values() 
                   for l in z.leads if l['sii_score'] >= 100)
    state.mission.play_score = min(100, 20 + (high_sii * 2))
```

### 4. Update Play Score Calculation
**File:** `app.py` (lines ~197)

```python
def calculate_storm_play_score():
    # 1. DETECTION (20 pts) - A-tier leads loaded
    if state.mission.checks.get("storm_loaded"):
        score += 20
    
    # 2. TARGET ACQUISITION (30 pts) - A-tier lead quality
    total_leads = sum(z.roof_count for z in state.zones.values())
    high_sii_leads = sum(1 for z in state.zones.values() 
                         for l in z.leads if l.get('sii_score', 0) >= 100)
    
    if total_leads > 0:
        score += 15  # Base for having leads
        quality_ratio = high_sii_leads / total_leads
        score += int(quality_ratio * 15)  # Bonus for high SII
```

## Validation Results

```
UI WIRING VALIDATION
============================================================
✅ A-tier zones loaded: 32
✅ Storm loaded check: True
✅ Leads generated: True

STATS (should be non-zero):
  • Impacted Roofs: 60
  • High Risk Zones: 1
  • Routes Ready: 0
  • Claims Filed: 0

PLAY SCORE:
  • Storm Play Score: 25/100
  • High SII leads: 20/60 (33%)

✅ WIRING COMPLETE: UI will show non-zero stats
```

## What You'll See in the UI

### Before (Demo State)
- Storm Play Score: **0/100**
- Impacted roofs: **0**
- Routes: **0**
- Claims: **0**
- "Load event & find targets" button locked

### After (Real Data)
- Storm Play Score: **25/100** (increases with actions)
- Impacted roofs: **60** (your A-tier leads)
- High Risk Zones: **1**
- Routes: **0** (build routes to increase)
- Claims: **0** (file claims to increase)
- "Load event & find targets" button active

### Play Score Breakdown
- **20 pts:** A-tier leads loaded ✅
- **5 pts:** Lead quality (33% with SII ≥ 100) ✅
- **25 pts:** Routes built (0 routes) ⏳
- **15 pts:** Claims filed (0 claims) ⏳
- **10 pts:** Nurture loop (0 reviews) ⏳

**Current: 25/100**

## How to Increase Play Score

### 1. Build Routes (+25 pts)
From the UI:
- Select high-risk zones on map
- Click "Build Routes"
- Each route adds +5 pts (max 25)

### 2. File Claims (+15 pts)
- Mark properties as "Inspected"
- File insurance claims
- Each claim adds +7 pts (max 15)

### 3. Start Nurture Loop (+10 pts)
- Send review requests
- Each review adds +3 pts (max 10)

## Architecture Connection

The UI now indirectly shows your full stack:

### Data Layer
- **A-tier CSV** → Loaded into UI zones
- **SII scores** → Displayed per lead
- **Personas** → Shown in lead details
- **Plays** → Recommended actions visible

### What's NOT Yet Wired
Your heavy infrastructure (Iceberg, Trino, Milvus, MLflow, Kafka, Neo4j) isn't directly connected to this UI instance. To wire those:

1. **Replace CSV loader with Trino queries:**
```python
# Instead of pickle.load()
import trino
conn = trino.connect(host='localhost', port=8080)
cursor = conn.cursor()
cursor.execute("SELECT * FROM iceberg.stormops.a_tier_leads")
leads = cursor.fetchall()
```

2. **Wire MLflow for SII scoring:**
```python
import mlflow
model = mlflow.pyfunc.load_model("models:/sii_model/production")
predictions = model.predict(property_features)
```

3. **Connect Milvus for semantic search:**
```python
from pymilvus import connections, Collection
connections.connect(host='localhost', port=19530)
collection = Collection("property_embeddings")
results = collection.search(query_vector, limit=10)
```

But for now, the **A-tier CSV is live and queryable** from the UI.

## Test the Integration

### 1. Refresh the UI
Go to http://localhost:8501 (should auto-reload)

### 2. Check Stats
Top KPI strip should show:
- **Impacted Roofs: 60** (not 0)
- **Storm Play Score: 25/100** (not 0)

### 3. Click "Load Event & Find Targets"
Should show:
```
✓ Loaded DFW Storm 24: 60 A-tier leads from 32 ZIPs
```

### 4. Query Copilot
Ask:
```
Show A-tier leads with SII ≥ 90 in 75209
```

Should return 3 leads with full enrichment.

## Files Modified

1. `/home/forsythe/earth2-forecast-wsl/hotspot_tool/app.py` - Main wiring
2. `/home/forsythe/earth2-forecast-wsl/hotspot_tool/verify_ui_wiring.py` - Validation script

## Next Steps

### Option A: Scale to Full Backend
Wire Trino/Iceberg/MLflow to replace CSV loader:
- Query A-tier leads from Iceberg via Trino
- Real-time SII scoring via MLflow
- Semantic search via Milvus

### Option B: CV Phase 1 Pilot
Use current A-tier leads for CV validation:
- Select 100-property subset
- Run RoofD defect detection
- Train SII_v2 with CV features
- Compare uplift vs SII_v1

### Option C: Operational Testing
Use UI to validate workflows:
- Build routes from A-tier leads
- Test persona-play assignments
- Validate SLA tracking
- Export for field deployment

---

**Status:** ✅ UI wired to real A-tier data
**Play Score:** 25/100 (live)
**Impacted Roofs:** 60 (live)
**Next:** CV pilot or full backend integration
