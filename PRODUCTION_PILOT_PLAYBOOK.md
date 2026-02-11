# Production Pilot Playbook

## Overview

This playbook guides you through running a **fully instrumented production pilot storm** with a real contractor. Use this for the first 3-5 storms to validate the platform before scaling.

---

## Pre-Pilot Checklist

### Infrastructure
- [ ] Postgres deployed and healthy
- [ ] Monitoring dashboard configured
- [ ] Alerts configured (Slack/PagerDuty)
- [ ] Backup verified (< 24h old)

### Tenant Setup
- [ ] Tenant provisioned
- [ ] Admin user created
- [ ] Tier configured (trial/standard/enterprise)
- [ ] Feature flags set

### Data Readiness
- [ ] Properties loaded
- [ ] Uplift model scored
- [ ] Experiments assigned
- [ ] Policy applied

---

## Pilot Execution

### Day -1: Pre-Storm Setup

```bash
# 1. Provision tenant (if new)
python3 << 'EOF'
from tenant_manager import TenantManager
import uuid

manager = TenantManager()
tenant = manager.provision_tenant(
    org_name='DFW Elite Roofing',
    tier='standard',
    admin_email='admin@dfwelite.com'
)
print(f"Tenant ID: {tenant['tenant_id']}")
EOF

# 2. Create storm
python3 << 'EOF'
from sqlalchemy import create_engine, text
import uuid

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')
tenant_id = uuid.UUID('...')  # From step 1
storm_id = uuid.uuid4()

with engine.begin() as conn:
    conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': tenant_id})
    conn.execute(text("""
        INSERT INTO storms (storm_id, tenant_id, event_id, name, status)
        VALUES (:sid, :tid, 'DFW_STORM_001', 'DFW Storm Feb 2026', 'planning')
    """), {'sid': storm_id, 'tid': tenant_id})

print(f"Storm ID: {storm_id}")
EOF

# 3. Load properties (from contractor's data)
# ... property loading script ...

# 4. Score uplift
python3 << 'EOF'
from model_registry import ModelRegistry

registry = ModelRegistry()
active_model = registry.get_active_model('uplift', 'production')
print(f"Using model: {active_model['version']}")

# Score properties
# ... scoring logic ...
EOF

# 5. Apply policy
python3 << 'EOF'
from policy_control_plane import PolicyControlPlane

plane = PolicyControlPlane(policy_mode='moderate')
result = plane.apply_policy(storm_id)

print(f"Policy applied:")
print(f"  Treat: {result['treat']} ({result['treat_pct']:.1f}%)")
print(f"  Hold: {result['hold']}")
EOF

# 6. Verify data quality
python3 << 'EOF'
from observability import DataObservability

obs = DataObservability(tenant_id)
dashboard = obs.get_health_dashboard(storm_id)

print(f"Health: {dashboard['health_status']}")
if dashboard['issues']:
    print(f"Issues: {dashboard['issues']}")
EOF
```

**Checklist:**
- [ ] Tenant provisioned
- [ ] Storm created
- [ ] Properties loaded
- [ ] Uplift scored
- [ ] Policy applied
- [ ] Data quality verified
- [ ] Crew briefed on control group importance

---

### Day 0-7: Storm Execution

**Monitor SLOs:**
```bash
python3 << 'EOF'
from slo_monitor import SLOMonitor

monitor = SLOMonitor()
dashboard = monitor.get_slo_dashboard(hours=24)

for slo_name, metrics in dashboard.items():
    print(f"{slo_name}: {metrics['status']}")
    if metrics['breaches'] > 0:
        print(f"  ⚠️ {metrics['breaches']} breaches")
EOF
```

**Log outcomes as they happen:**
```python
from policy_control_plane import PolicyControlPlane

plane = PolicyControlPlane(policy_mode='moderate')

# For each property outcome
plane.log_outcome(
    property_id='...',
    event_id='DFW_STORM_001',
    converted=True,  # or False
    value=15000  # if converted
)
```

**Daily checks:**
- [ ] Check active alerts
- [ ] Review conversion rates (treat vs hold)
- [ ] Check data quality metrics
- [ ] Verify no control contamination

---

### Day 8-14: Post-Storm Analysis

**Run pilot report:**
```bash
python3 << 'EOF'
from pilot_storm_runner import PilotStormRunner
import uuid

tenant_id = uuid.UUID('...')
storm_id = uuid.UUID('...')

runner = PilotStormRunner(tenant_id, storm_id)
results = runner.run_pilot(policy_mode='moderate')

print(f"Lift: {results['outcomes']['lift']['absolute']*100:+.1f} pts")
print(f"ROI: {results['roi']['roi_pct']:.1f}%")
print(f"Incremental Revenue: ${results['roi']['incremental_revenue']:,.0f}")

# Generate PDF report
runner.generate_report_pdf(results)
EOF

# Convert to PDF
pandoc pilot_storm_report.md -o pilot_storm_report.pdf
```

**Analysis checklist:**
- [ ] Treatment vs control conversion calculated
- [ ] Lift measured (target: >10 pts)
- [ ] ROI calculated (target: >300%)
- [ ] Uplift prediction accuracy checked
- [ ] Data quality issues documented
- [ ] Report generated and reviewed

---

## Success Criteria

### Technical
- ✅ Treatment > Control by 10+ pts
- ✅ ROI > 300%
- ✅ No data quality issues
- ✅ No SLO breaches
- ✅ No control contamination

### Business
- ✅ Contractor satisfied with results
- ✅ Incremental revenue > $5k
- ✅ CAC < $500
- ✅ Revenue/hour > $100

---

## Troubleshooting

### Low Lift (< 5 pts)

**Symptoms:**
- Treatment conversion only slightly higher than control
- Uplift predictions not matching reality

**Runbook:**
1. Check policy compliance (were decisions followed?)
2. Check for control contamination
3. Review experiment assignments
4. Analyze by segment (ZIP, persona)
5. Check uplift model drift

**Commands:**
```python
from observability import DataObservability

obs = DataObservability(tenant_id)
rates = obs.check_conversion_rates(storm_id)

if rates.get('anomaly'):
    print("⚠️ Conversion anomaly detected")
    print(f"Treat: {rates['treat']['rate']*100:.1f}%")
    print(f"Hold: {rates['hold']['rate']*100:.1f}%")
    print(f"Lift: {rates['lift']*100:.1f} pts")
```

### Uplift Drift

**Symptoms:**
- Uplift mean < 0.10 or > 0.30
- Predictions don't match outcomes

**Runbook:**
1. Check storm characteristics vs training data
2. Verify feature engineering
3. Check data quality
4. Consider retraining model
5. Switch to shadow mode if severe

**Commands:**
```python
from observability import DataObservability

obs = DataObservability(tenant_id)
dist = obs.check_uplift_distribution(storm_id)

if dist['drift_detected']:
    print("⚠️ Drift detected")
    print(f"Mean: {dist['mean']:.3f} (expected ~0.20)")
    print(f"Stddev: {dist['stddev']:.3f}")
```

### High Error Rate

**Symptoms:**
- UI errors
- Failed API calls
- Database timeouts

**Runbook:**
1. Check application logs
2. Check database connectivity
3. Check for recent deployments
4. Roll back if needed
5. Scale up if load-related

**Commands:**
```bash
# Check active alerts
python3 << 'EOF'
from slo_monitor import SLOMonitor

monitor = SLOMonitor()
alerts = monitor.get_active_alerts()

for alert in alerts:
    print(f"[{alert['severity']}] {alert['message']}")
EOF

# Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM pg_stat_activity"
```

---

## Post-Pilot Actions

### If Successful (Lift > 10 pts, ROI > 300%)

1. **Share results with contractor**
   - Send pilot report PDF
   - Schedule review call
   - Discuss scaling to more storms

2. **Document learnings**
   - What worked well
   - What needs improvement
   - Data quality issues
   - Feature requests

3. **Prepare for next tenant**
   - Update playbook with learnings
   - Automate manual steps
   - Improve monitoring

4. **Scale up**
   - Onboard 2-3 more contractors
   - Run parallel storms
   - Monitor system load

### If Unsuccessful (Lift < 5 pts or ROI < 100%)

1. **Root cause analysis**
   - Review all data quality checks
   - Check policy compliance
   - Analyze by segment
   - Review model performance

2. **Fix issues**
   - Retrain model if drift detected
   - Adjust policy threshold
   - Improve data quality
   - Fix bugs

3. **Re-run pilot**
   - Apply fixes
   - Run another storm
   - Measure improvement

---

## Billing

**Calculate invoice:**
```python
from billing_manager import BillingManager
from datetime import datetime

billing = BillingManager()

# Get current month usage
dashboard = billing.get_billing_dashboard(tenant_id)

print(f"Tier: {dashboard['tier']}")
print(f"Base: ${dashboard['current_period']['base_amount']:.2f}")
print(f"Overage: ${dashboard['current_period']['overage_amount']:.2f}")
print(f"Total: ${dashboard['current_period']['total_amount']:.2f}")

# Create invoice
period_start = datetime(2026, 2, 1)
period_end = datetime(2026, 3, 1)
invoice_id = billing.create_invoice(tenant_id, period_start, period_end)

print(f"Invoice created: {invoice_id}")
```

---

## Next Pilot

Use this playbook for the next 2-3 pilots, updating it with learnings each time. After 3 successful pilots, move to automated onboarding.

---

**Last Updated:** 2026-02-07
**Version:** 1.0.0
