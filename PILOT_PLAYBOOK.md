# Pilot Program Playbook

## Quick Start

### 1. Onboard New Pilot (5 min)

```bash
cd /home/forsythe/earth2-forecast-wsl/hotspot_tool
python onboard_pilot.py "DFW Elite Roofing" "john@dfwelite.com" "John Smith"
```

This creates:
- ✅ Tenant account
- ✅ Admin user
- ✅ Sample storm with 10 properties
- ✅ Treatment decisions ready to route

### 2. Monitor Pilot Health

```bash
streamlit run pilot_dashboard.py
```

View at: http://localhost:8501

Tracks:
- Days in pilot
- Storms, routes, jobs
- Conversion rates
- Health score (0-100)
- 7-day activity

### 3. Success Criteria (4-6 weeks)

**Go/No-Go Metrics:**
- ✅ 3+ routes per storm
- ✅ 50+ jobs completed
- ✅ 80%+ completion rate
- ✅ 20%+ conversion rate
- ✅ Weekly activity > 5 events

**Health Score:**
- 80-100: Excellent (ready to convert)
- 50-79: Good (on track)
- 0-49: Needs attention (intervene)

## Pilot Workflow

### Week 1: Activation
1. Onboard tenant
2. Import first real storm
3. Generate routes
4. Assign to crews

**Success:** Routes generated, crews assigned

### Week 2-3: Execution
1. Track jobs daily
2. Capture photos/claims
3. Monitor completion rate

**Success:** 50%+ jobs completed

### Week 4-6: Outcomes
1. Measure conversion rate
2. Calculate lift vs control
3. Gather feedback

**Success:** Positive ROI, ready to scale

## Commands

### Onboard Pilot
```bash
python onboard_pilot.py "Company" "email" "Name"
```

### View Dashboard
```bash
streamlit run pilot_dashboard.py
```

### Check Tenant Status
```python
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT org_name, pilot_start_date, 
               (SELECT COUNT(*) FROM storms WHERE tenant_id = t.tenant_id) as storms
        FROM tenants t
        WHERE tier = 'pilot'
    """))
    for row in result:
        print(f"{row[0]}: {row[2]} storms, started {row[1]}")
```

### Generate Routes for Pilot
```python
from route_builder import RouteBuilder
import uuid

tenant_id = uuid.UUID('YOUR-TENANT-ID')
storm_id = uuid.UUID('YOUR-STORM-ID')

builder = RouteBuilder(tenant_id, storm_id)
routes = builder.generate_routes(max_per_route=50)
print(f"Generated {len(routes)} routes")
```

## Feedback Loop

### Weekly Check-in
1. Review pilot dashboard
2. Check health score
3. Note blockers
4. Update roadmap

### Monthly Review
1. Measure against success criteria
2. Calculate incrementality
3. Document learnings
4. Decide: continue, convert, or end

## Scaling

Once pilot hits success criteria:
1. Convert to paid tier
2. Use as case study
3. Replicate with 2-3 more pilots
4. Build public roadmap from feedback
