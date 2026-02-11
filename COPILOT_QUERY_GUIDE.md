# StormOps Copilot - A-Tier Lead Queries

## Quick Reference

Your 61 A-tier leads are now live at http://localhost:8501

### Sample Queries for the Copilot

#### 1. Filter by SII and ZIP
```
Show A-tier leads with SII ≥ 90 in 75209 and summarize personas and recommended plays
```

**Expected Result:**
- 3 leads with SII ≥ 90
- Personas: Deal_Hunter, Proof_Seeker, Family_Protector (balanced)
- Plays: Financing_Aggressive, Impact_Report_Premium, Safety_Warranty

#### 2. Top Leads by Value
```
Show the top 10 A-tier leads by property value with their SII scores and personas
```

#### 3. Persona-Specific Targeting
```
Show all Deal_Hunter persona leads with SII ≥ 100 and their recommended plays
```

**Expected Result:**
- ~12 leads (Deal_Hunter is 44% of A-tier)
- Plays: Primarily Financing_Aggressive and Financing_Standard

#### 4. Geographic Distribution
```
Which ZIPs have the most A-tier leads and what are their average SII scores?
```

**Expected Result:**
- 75209, 75224, 75208, 75231: 4 leads each
- Avg SII ranges from 70-110

#### 5. Play Distribution
```
Summarize recommended plays across all A-tier leads and show counts
```

**Expected Result:**
- Financing_Standard: 15
- Financing_Aggressive: 12
- Impact_Report_Standard: 8
- Impact_Report_Premium: 8

### Validation Checklist

When you query the copilot, verify these fields appear:

- ✅ **SII Score** (70-110 range for A-tier)
- ✅ **Risk Score** (60-95 range)
- ✅ **Persona** (Deal_Hunter, Proof_Seeker, Family_Protector, Status_Conscious)
- ✅ **Recommended Play** (Financing_*, Impact_Report_*, Safety_*, Premium_*)
- ✅ **Play Message** (Customized messaging per persona/play)
- ✅ **SLA Hours** (12-24h for A-tier)
- ✅ **Property Value** ($200K-$500K range)

### Map Interaction

1. Click on any map marker in the UI
2. Verify the popup shows:
   - Address
   - SII score
   - Persona
   - Recommended play
   - Play message

### Filtering in UI

Use the sidebar filters:
- **Priority:** Set to "A-tier" or "High SII"
- **Persona:** Select specific personas (Deal_Hunter, etc.)
- **ZIP Code:** Filter to specific ZIPs (75209, 75224, etc.)

### Export for CV Pilot

To select the 100-property CV pilot subset:

```python
import pandas as pd

# Load A-tier leads
df = pd.read_csv('/home/forsythe/kirocli/kirocli/a_tier_leads.csv')

# Select top 100 by SII (or all 61 if you want)
cv_pilot = df.nlargest(100, 'sii_score')

# Save for CV processing
cv_pilot.to_csv('cv_pilot_subset.csv', index=False)

print(f"Selected {len(cv_pilot)} properties for CV Phase 1")
print(f"SII range: {cv_pilot['sii_score'].min():.0f} - {cv_pilot['sii_score'].max():.0f}")
```

### Troubleshooting

**Copilot not showing leads?**
```bash
cd /home/forsythe/earth2-forecast-wsl/hotspot_tool
python3 validate_copilot_query.py
```

**Need to refresh data?**
```bash
cd /home/forsythe/kirocli/kirocli
python3 load_a_tier_to_ui.py
```
Then refresh browser at http://localhost:8501

---

**Status:** ✅ A-tier leads commissioned and queryable
**Next:** CV Phase 1 pilot (100 properties → RoofD → SII_v2)
