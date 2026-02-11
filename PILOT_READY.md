# Pilot Infrastructure - Ready to Deploy

## ✅ What's Built

### 1. Onboarding System
- **Script**: `onboard_pilot.py`
- **Usage**: `python onboard_pilot.py "Company" "email" "Name"`
- **Creates**:
  - Tenant account (pilot tier)
  - Admin user
  - Sample storm with 10 properties
  - Treatment decisions ready to route

### 2. Pilot Dashboard
- **File**: `pilot_dashboard.py`
- **Run**: `streamlit run pilot_dashboard.py`
- **Tracks**:
  - All active pilots
  - Days in pilot
  - Storms, routes, jobs
  - Conversion rates
  - Health score (0-100)
  - 7-day activity

### 3. Success Criteria
**Go/No-Go Metrics (4-6 weeks)**:
- 3+ routes per storm
- 50+ jobs completed
- 80%+ completion rate
- 20%+ conversion rate
- Weekly activity > 5 events

### 4. Playbook
- **File**: `PILOT_PLAYBOOK.md`
- Week-by-week guide
- Commands and scripts
- Feedback loop process

## 🚀 Quick Start

### Onboard First Pilot
```bash
cd /home/forsythe/earth2-forecast-wsl/hotspot_tool
python onboard_pilot.py "DFW Elite Roofing" "john@dfwelite.com" "John Smith"
```

### Monitor Pilots
```bash
streamlit run pilot_dashboard.py
# View at http://localhost:8501
```

### Generate Routes for Pilot
```python
from route_builder import RouteBuilder
import uuid

tenant_id = uuid.UUID('TENANT-ID-FROM-ONBOARDING')
storm_id = uuid.UUID('STORM-ID-FROM-ONBOARDING')

builder = RouteBuilder(tenant_id, storm_id)
routes = builder.generate_routes(max_per_route=50)
```

## 📊 What Gets Tracked

### Per Pilot:
- Activation progress (5 milestones)
- Storm count
- Routes generated
- Jobs completed
- Completion rate
- Conversion rate
- Avg claim value
- 7-day activity
- Health score

### Health Score (0-100):
- **80-100**: Excellent - ready to convert to paid
- **50-79**: Good - on track
- **0-49**: Needs attention - intervene

## 📈 Next Steps

### Week 1: Launch
1. Onboard 2-3 pilot contractors
2. Import their first real storm
3. Generate routes
4. Train on job tracking

### Week 2-4: Execute
1. Monitor dashboard daily
2. Track completion rates
3. Capture outcomes
4. Weekly check-ins

### Week 4-6: Measure
1. Calculate incrementality
2. Measure vs success criteria
3. Gather feedback
4. Decide: convert, continue, or end

### After Success:
1. Convert to paid tier
2. Document case study
3. Use for sales/marketing
4. Replicate with 3-5 more pilots

## 🔧 Technical Details

### Database Schema:
- `tenants` table has pilot tier
- `pilot_start_date` tracks duration
- `tenant_usage` logs activity
- `policy_outcomes` tracks conversions

### Files Created:
- `onboard_pilot.py` - Onboarding script
- `pilot_dashboard.py` - Monitoring dashboard
- `PILOT_PLAYBOOK.md` - Operational guide

### Integration Points:
- Works with existing route_builder.py
- Uses policy_decisions_log for targeting
- Writes to policy_outcomes for feedback
- Tracks via tenant_usage

## 💡 Key Insight

This shifts from "does it work?" to "is it valuable?" - you can now:
1. Onboard real contractors in 5 minutes
2. Track their success in real-time
3. Measure against clear criteria
4. Learn what to build next from actual usage

The infrastructure is ready. Time to run real pilots.
