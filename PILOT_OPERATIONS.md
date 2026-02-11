# Pilot Operations Guide - Daily Workflow

## Morning Routine (10 min)

### 1. Check Pilot Dashboard
```bash
streamlit run pilot_dashboard.py
```

**Look for:**
- Health scores < 50 (red flag)
- 7-day activity = 0 (pilot stalled)
- Completion rate dropping
- No new jobs in 3+ days

**Action:** Schedule call with any pilot showing red flags

### 2. Review Individual Pilots
For each active pilot, check:
- Days in pilot (are they on track for 4-6 week timeline?)
- Jobs completed this week
- Conversion rate trend
- Any blockers logged

## Weekly Review (30 min)

### 1. Generate Reports
```bash
# For each pilot
python generate_pilot_report.py <tenant_id>
```

### 2. Analyze Trends
- Which pilots are hitting success criteria?
- Where are pilots getting stuck?
- What features are they asking for?

### 3. Update Roadmap
Based on pilot feedback, prioritize:
1. Blockers (things preventing success)
2. High-value features (things they'd pay for)
3. Nice-to-haves (polish)

## Monthly Review (1 hour)

### 1. Measure Against Criteria
For each pilot:
- ✅ 3+ routes per storm?
- ✅ 50+ jobs completed?
- ✅ 80%+ completion rate?
- ✅ 20%+ conversion rate?

### 2. Make Go/No-Go Decisions

**If hitting criteria:**
- Convert to paid tier
- Create case study
- Use for sales collateral

**If not hitting criteria:**
- Extend pilot 2-4 weeks, OR
- End pilot and document learnings

### 3. Plan Next Wave
- How many pilots can you support?
- What did you learn from this wave?
- What needs to be fixed before next wave?

## Pilot Feedback Calls

### When to Schedule:
- Health score drops below 50
- No activity for 7 days
- Completion rate < 50%
- End of pilot period

### What to Ask:
1. **Value**: "What made StormOps obviously valuable?"
2. **Friction**: "Where did you get stuck?"
3. **Missing**: "What would make this a must-have?"
4. **ROI**: "How much time/money did this save?"

### Document:
- Quotes for case studies
- Feature requests
- Integration needs
- Training gaps

## Data to Track

### Per Pilot:
- Onboarding date
- First storm date
- Routes generated
- Jobs completed
- Conversion rate
- Lift vs control
- Health score trend
- Last activity date

### Aggregate:
- Total pilots active
- Avg health score
- Avg conversion rate
- Common blockers
- Most requested features

## Red Flags

**Immediate attention needed:**
- Health score < 30
- Zero activity for 7+ days
- Completion rate < 30%
- Multiple failed route generations

**Schedule call within 24 hours**

## Success Signals

**Pilot is working:**
- Health score > 70
- Daily activity
- Completion rate > 70%
- Positive feedback
- Asking about pricing

**Action:** Start conversion conversation

## Tools

### Onboard New Pilot
```bash
python onboard_pilot.py "Company" "email" "Name"
```

### Monitor All Pilots
```bash
streamlit run pilot_dashboard.py
```

### Generate Report
```bash
python generate_pilot_report.py <tenant_id> [storm_id]
```

### Check Specific Pilot
```python
from pilot_metrics import PilotMetrics
import uuid

metrics = PilotMetrics()
health = metrics.get_pilot_health(uuid.UUID('tenant-id'))
print(f"Health: {health['health_score']}")
print(f"Activity: {health['recent_activity']}")
```

## First 3 Pilots - Checklist

### Week 1: Launch
- [ ] Onboard 3 pilots
- [ ] Import first storm for each
- [ ] Generate routes
- [ ] Train on job tracking
- [ ] Set up weekly check-ins

### Week 2-4: Execute
- [ ] Daily dashboard review
- [ ] Track completion rates
- [ ] Capture outcomes
- [ ] Weekly feedback calls
- [ ] Document learnings

### Week 4-6: Measure
- [ ] Generate pilot reports
- [ ] Calculate incrementality
- [ ] Measure vs success criteria
- [ ] Make go/no-go decisions
- [ ] Plan next wave

## Output: Pilot Report

After each storm, generate report showing:
- Operational metrics (routes, jobs, completion)
- Conversion & ROI (rate, claim value)
- Incrementality (lift vs control)
- Success criteria status
- Next steps

**Use for:**
- Sales conversations
- Investor updates
- Case studies
- Internal learning

## Key Insight

This isn't about building more features - it's about **learning what makes pilots successful** and **proving value to real contractors**.

The infrastructure is ready. Time to run the pilots and learn.
