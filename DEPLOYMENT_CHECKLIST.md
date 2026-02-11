# StormOps Multi-Tenant Platform - Deployment Checklist

## Pre-Deployment

### Infrastructure
- [ ] Provision Postgres instance (RDS, Cloud SQL, or self-hosted)
- [ ] Configure connection pooling (PgBouncer recommended)
- [ ] Setup backups (daily snapshots, 30-day retention)
- [ ] Configure monitoring (CloudWatch, Datadog, or Prometheus)
- [ ] Setup alerting (PagerDuty, Slack, or email)

### Security
- [ ] Generate strong database password
- [ ] Configure SSL/TLS for database connections
- [ ] Setup VPC/network isolation
- [ ] Configure firewall rules (allow only app servers)
- [ ] Enable audit logging

### Environment Variables
```bash
DATABASE_URL=postgresql://stormops:PASSWORD@HOST:5432/stormops
ENVIRONMENT=production
LOG_LEVEL=info
```

---

## Deployment Steps

### 1. Database Setup

```bash
# Connect to Postgres
psql $DATABASE_URL

# Run schema
\i schema_postgres.sql

# Verify tables
\dt

# Check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('storms', 'properties', 'customer_journeys');
```

- [ ] Schema applied successfully
- [ ] All tables created (15+ tables)
- [ ] RLS enabled on all tenant-scoped tables
- [ ] Indexes created
- [ ] Functions created

### 2. Application Deployment

```bash
# Install dependencies
pip install -r requirements-multitenant.txt

# Run tests
pytest test_e2e_multitenant.py -v

# Deploy application
# (Use your deployment method: Docker, K8s, etc.)
```

- [ ] Dependencies installed
- [ ] Tests passing
- [ ] Application deployed
- [ ] Health check endpoint responding

### 3. Tenant Provisioning

```python
from tenant_manager import TenantManager

manager = TenantManager()

# Provision first tenant
tenant = manager.provision_tenant(
    org_name='DFW Elite Roofing',
    tier='standard',
    admin_email='admin@dfwelite.com'
)

print(f"Tenant ID: {tenant['tenant_id']}")
```

- [ ] First tenant provisioned
- [ ] Admin user created
- [ ] Tenant context working
- [ ] RLS verified (tenant can only see own data)

### 4. Data Migration (if applicable)

```bash
# Migrate from SQLite
python3 migrate_to_postgres.py
```

- [ ] Properties migrated
- [ ] Journeys migrated
- [ ] Uplift scores migrated
- [ ] Experiments migrated
- [ ] Policy decisions migrated
- [ ] Data integrity verified

### 5. Observability Setup

```python
from observability import DataObservability, SystemMonitoring

# Check health
obs = DataObservability(tenant_id)
dashboard = obs.get_health_dashboard(storm_id)

print(f"Status: {dashboard['health_status']}")
```

- [ ] Health checks working
- [ ] Drift detection configured
- [ ] Metrics being logged
- [ ] Alerts configured

---

## Post-Deployment

### Smoke Tests

```bash
# 1. Tenant isolation
python3 << 'EOF'
from tenant_manager import TenantContext
import uuid

tenant_a = uuid.UUID('...')
tenant_b = uuid.UUID('...')

# Create storm for tenant A
with TenantContext(tenant_a) as conn:
    conn.execute("INSERT INTO storms (...)")

# Verify tenant B cannot see it
with TenantContext(tenant_b) as conn:
    count = conn.execute("SELECT COUNT(*) FROM storms").scalar()
    assert count == 0, "Tenant isolation broken!"

print("✅ Tenant isolation verified")
EOF

# 2. Full storm cycle
python3 << 'EOF'
# Create storm → Apply policy → Log outcomes → Check lift
# (See test_e2e_multitenant.py for full example)
EOF

# 3. Observability
python3 observability.py
```

- [ ] Tenant isolation verified
- [ ] Full storm cycle working
- [ ] Observability checks passing
- [ ] No errors in logs

### Performance Tests

```bash
# Load test with multiple tenants
# (Use locust, k6, or similar)
```

- [ ] Query latency < 5s P99
- [ ] No connection pool exhaustion
- [ ] No memory leaks
- [ ] CPU usage acceptable

### Monitoring

- [ ] Dashboard created (Grafana, Datadog, etc.)
- [ ] Key metrics tracked:
  - Active tenants
  - Queries per second
  - Query latency (P50, P95, P99)
  - Error rate
  - DB connection pool usage
  - Storage per tenant
- [ ] Alerts configured:
  - High error rate (> 1%)
  - High latency (P99 > 10s)
  - DB connection pool > 80%
  - Drift detected
  - Low conversion lift

---

## Rollback Plan

If issues arise:

### 1. Application Rollback
```bash
# Revert to previous version
git checkout <previous-tag>
# Redeploy
```

### 2. Database Rollback
```bash
# Restore from backup
pg_restore -d stormops backup.dump
```

### 3. Tenant Suspension
```python
from tenant_manager import TenantManager

manager = TenantManager()
manager.suspend_tenant(tenant_id, reason='deployment_issue')
```

---

## Go-Live Checklist

### Day -1 (Pre-Launch)
- [ ] All deployment steps completed
- [ ] Smoke tests passing
- [ ] Performance tests passing
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Rollback plan tested
- [ ] Team briefed

### Day 0 (Launch)
- [ ] Deploy to production
- [ ] Run smoke tests
- [ ] Monitor for 1 hour
- [ ] Provision first tenant
- [ ] Run first storm
- [ ] Verify results

### Day +1 (Post-Launch)
- [ ] Review metrics
- [ ] Check for errors
- [ ] Verify tenant isolation
- [ ] Check data quality
- [ ] Review costs
- [ ] Document learnings

### Week +1
- [ ] Onboard 2nd tenant
- [ ] Onboard 3rd tenant
- [ ] Review performance
- [ ] Optimize queries if needed
- [ ] Update documentation

---

## Success Criteria

### Technical
- ✅ Zero cross-tenant data leaks
- ✅ < 1% data quality issues
- ✅ < 5 min P99 query latency
- ✅ 99.9% uptime
- ✅ Automated deployments working

### Business
- ✅ 3+ active tenants
- ✅ Positive feedback from users
- ✅ No critical bugs
- ✅ Cost per tenant < $200/month
- ✅ Ready to scale to 10+ tenants

---

## Contacts

### On-Call
- Primary: [Name] - [Phone]
- Secondary: [Name] - [Phone]

### Escalation
- Engineering Lead: [Name]
- Product Manager: [Name]
- CTO: [Name]

---

## Resources

- **Documentation:** MULTI_TENANT_PLATFORM.md
- **Runbook:** observability.py (RUNBOOK dict)
- **Tests:** test_e2e_multitenant.py
- **Monitoring:** [Dashboard URL]
- **Logs:** [Log aggregation URL]

---

**Last Updated:** 2026-02-07
**Version:** 1.0.0
**Status:** Ready for production deployment
