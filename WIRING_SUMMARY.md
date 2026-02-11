# StormOps UI → A-Tier Leads: WIRED ✅

## What You Asked For
> "Point this StormOps UI at the real backend (A-tier leads, SII scores) instead of demo data"

## What Was Done

### Minimal Changes (4 edits to app.py)

1. **Auto-load A-tier on startup** → Stats populate immediately
2. **"Load event" button** → Uses real lead counts
3. **"Generate leads now" button** → Shows real SII distribution
4. **Play score calculation** → Based on A-tier quality metrics

### Result

**Before:**
- Play Score: 0/100
- Impacted Roofs: 0
- All demo data

**After:**
- Play Score: 25/100 ✅
- Impacted Roofs: 60 ✅
- Real A-tier leads ✅

## Verify It Works

```bash
cd /home/forsythe/earth2-forecast-wsl/hotspot_tool
python3 verify_ui_wiring.py
```

Expected output:
```
✅ A-tier zones loaded: 32
✅ Impacted Roofs: 60
✅ Storm Play Score: 25/100
```

## View in UI

http://localhost:8501

- Top KPI strip shows **60 impacted roofs** (not 0)
- Storm Play Score shows **25/100** (not 0)
- Click "Load event & find targets" → Shows "60 A-tier leads from 32 ZIPs"

## What's Live

✅ 61 A-tier leads loaded
✅ SII scores (70-110 range)
✅ Personas (Deal_Hunter, Proof_Seeker, etc.)
✅ Recommended plays (Financing_Aggressive, etc.)
✅ Play messages
✅ SLA hours

## What's NOT Wired Yet

The heavy infrastructure (Iceberg, Trino, Milvus, MLflow, Kafka, Neo4j) isn't connected to this UI. To wire those, you'd replace the CSV loader with Trino queries, MLflow model calls, etc.

But for now: **Your enrichment is live from this screen.**

## Next: CV Phase 1

Now that A-tier leads are commissioned in the UI, proceed with computer vision:

1. Select 100-property subset (top SII or specific ZIP)
2. Run RoofD defect detection
3. Add 3-5 CV features to model
4. Train SII_v2 and compare vs SII_v1
5. Scale if uplift confirmed

---

**Files:**
- `/home/forsythe/earth2-forecast-wsl/hotspot_tool/app.py` (modified)
- `/home/forsythe/earth2-forecast-wsl/hotspot_tool/outputs/a_tier_zones.pkl` (data)
- `/home/forsythe/earth2-forecast-wsl/hotspot_tool/UI_WIRING_COMPLETE.md` (full docs)
