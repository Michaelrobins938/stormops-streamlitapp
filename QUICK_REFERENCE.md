# StormOps Quick Reference

## Run Production Pilot

```bash
# 1. Setup
./setup_multitenant.sh

# 2. Provision tenant
python3 -c "
from tenant_manager import TenantManager
m = TenantManager()
t = m.provision_tenant('DFW Elite Roofing', 'standard', 'admin@dfw.com')
print(t['tenant_id'])
"

# 3. Run pilot
python3 pilot_storm_runner.py

# 4. Generate report
pandoc pilot_storm_report.md -o pilot_storm_report.pdf
```

## Monitor SLOs

```python
from slo_monitor import SLOMonitor

monitor = SLOMonitor()

# Measure
monitor.measure_slo('journey_ingestion_latency', 3.5)

# Dashboard
dashboard = monitor.get_slo_dashboard(hours=24)

# Alerts
alerts = monitor.get_active_alerts()
```

## Track Billing

```python
from billing_manager import BillingManager

billing = BillingManager()

# Log usage
billing.log_usage(tenant_id, 'storm_created', 1)

# Dashboard
dashboard = billing.get_billing_dashboard(tenant_id)

# Invoice
invoice_id = billing.create_invoice(tenant_id, start, end)
```

## Manage Models

```python
from model_registry import ModelRegistry

registry = ModelRegistry()

# Register
v_id = registry.register_model('uplift', 'v2', 'xgboost', 
                                datetime.now(), {'auc': 0.78})

# Deploy
registry.deploy_model(v_id, 'production', 'shadow')

# Compare
comparison = registry.compare_models(v1_id, v2_id)
```

## Troubleshooting

### Low Lift
```python
from observability import DataObservability
obs = DataObservability(tenant_id)
rates = obs.check_conversion_rates(storm_id)
```

### Uplift Drift
```python
dist = obs.check_uplift_distribution(storm_id)
if dist['drift_detected']:
    print(f"Mean: {dist['mean']:.3f}")
```

### Active Alerts
```python
from slo_monitor import SLOMonitor
monitor = SLOMonitor()
alerts = monitor.get_active_alerts()
```

## Pricing

| Tier | Base | Storms | Properties | Model Calls |
|------|------|--------|------------|-------------|
| Trial | $0 | 1 | 500 | 1k |
| Standard | $500 | 5 | 5k | 10k |
| Enterprise | $2k | ∞ | ∞ | ∞ |

## SLOs

| Metric | Target | Threshold |
|--------|--------|-----------|
| Journey ingestion | 5s | 10s |
| Model scoring | 1s | 5s |
| UI error rate | 0.1% | 1% |
| Query P99 | 5s | 10s |

## Success Criteria

- Lift > 10 pts
- ROI > 300%
- No data quality issues
- Contractor satisfied

---

**Docs:** PRODUCTION_PILOT_PLAYBOOK.md
**UI:** streamlit run app.py
