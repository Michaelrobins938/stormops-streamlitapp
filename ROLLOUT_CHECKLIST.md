# StormOps v1.0: Rollout Checklist

## ✅ Calibration Complete (Today)
- [x] SII_v2 calibration: 45 → 109.9 avg
- [x] Uplift models: 0 → 61 predictions
- [x] E2E test: All phases passing
- [x] All KPIs: PASS

---

## 📋 This Week: Scale + First Team

### Day 1-2: Scale to 4,200 Roofs
- [ ] Expand A-tier leads (61 → 4,200)
  ```bash
  # Modify journey_ingestion.py to process full footprint
  # Run: python3 journey_ingestion.py --full-scale
  ```
- [ ] Test Trino query performance
  ```sql
  -- Monitor query time for 4,200 roofs
  SELECT COUNT(*) FROM customer_journeys; -- Should be ~14k events
  ```
- [ ] Monitor CV inference throughput
  ```bash
  # Time CV feature generation for 4,200 properties
  # Target: <5 minutes for full batch
  ```
- [ ] Verify attribution at scale
  ```bash
  python3 attribution_integration.py
  # Check: Processing time < 1 second
  ```

### Day 3: Team Onboarding Prep
- [ ] Review `onboarding_dfw_elite_roofing/checklist.md`
- [ ] Schedule Day 1 training (2 hours)
- [ ] Prepare sample storm data (DFW_STORM_24)
- [ ] Set up team accounts in control plane
- [ ] Configure 2 Strategic Plays:
  - Financing_Aggressive (Deal_Hunter)
  - Impact_Report_Premium (Proof_Seeker)

### Day 4-5: Day 1-2 Training
- [ ] Day 1: System overview (2 hours)
  - StormOps philosophy
  - Control plane walkthrough
  - Attribution dashboard
  - Copilot basics
- [ ] Day 2: Hands-on training (4 hours)
  - Load DFW_STORM_24
  - Review A-tier leads
  - Execute Strategic Play
  - Track attribution

### Week 1: Supervised Usage
- [ ] Daily check-ins with team
- [ ] Monitor KPIs:
  - Response time: <6 hours
  - Doors/hour: 10-15
  - Conversion rate: 30-50%
  - CAC: <$1500
- [ ] Collect feedback (use `feedback_template.md`)
- [ ] Adjust plays based on input

### Week 2: Independent Usage
- [ ] Team operates autonomously
- [ ] Weekly KPI review
- [ ] Document success stories
- [ ] Identify feature requests

---

## 📋 Next 2 Weeks: Production Infrastructure

### Postgres Migration
- [ ] Start Postgres container
  ```bash
  docker run -d -p 5432:5432 \
    -e POSTGRES_PASSWORD=password \
    -e POSTGRES_DB=stormops \
    postgres:latest
  ```
- [ ] Create tables
  ```bash
  psql -h localhost -U postgres -d stormops -f schema_full.sql
  ```
- [ ] Migrate data from SQLite
  ```bash
  python3 migrate_to_postgres.py
  ```
- [ ] Update connection strings in:
  - attribution_integration.py
  - play_attribution.py
  - journey_ingestion.py
  - uplift_models.py

### Kafka + Flink Stack
- [ ] Start infrastructure
  ```bash
  docker-compose up -d
  ```
- [ ] Verify services
  ```bash
  docker-compose ps
  # Should show: kafka, zookeeper, flink, trino, postgres
  ```
- [ ] Deploy Flink jobs
  ```bash
  python flink_guardrails_job.py &
  python flink_triggers_job.py &
  ```
- [ ] Start action consumer
  ```bash
  python action_consumer.py &
  ```

### Monitoring & Alerts
- [ ] Set up basic monitoring
  - Kafka lag
  - Flink job status
  - Trino query latency
  - Attribution processing time
- [ ] Configure alerts
  - SLA breaches (>24h response)
  - Error rates (>5%)
  - Storm Play Score drops (<20)
- [ ] Create ops dashboard
  - System health
  - KPI trends
  - Team performance

---

## 📋 Month 1: Multi-Team Rollout

### Week 3-4: Second Team
- [ ] Select second contractor
- [ ] Generate onboarding package
- [ ] Execute 3-day training
- [ ] Monitor Week 1 supervised usage

### Week 4: Real CV Integration
- [ ] Replace mock CV with RoofD
- [ ] Run inference on aerial imagery
- [ ] Validate SII_v2 uplift with real features
- [ ] Scale across territory

### Week 4: Performance Review
- [ ] Compare Team 1 vs Team 2 KPIs
- [ ] Identify best practices
- [ ] Update playbook library
- [ ] Document lessons learned

---

## Success Criteria

### Technical
- [ ] System handles 4,200 roofs without performance degradation
- [ ] All services running on production infrastructure
- [ ] Monitoring and alerts operational
- [ ] Zero data loss or corruption

### Business
- [ ] Team 1 achieves 80%+ system adoption
- [ ] Conversion rate meets or exceeds 30%
- [ ] CAC below $1500
- [ ] Team reports 8+/10 confidence in system

### Product
- [ ] Feedback incorporated into roadmap
- [ ] 2+ success stories documented
- [ ] Feature requests prioritized
- [ ] Onboarding process validated

---

## Quick Commands

### Run Full Pipeline
```bash
cd /home/forsythe/kirocli/kirocli

# 1. Generate journeys
python3 journey_ingestion.py

# 2. Run attribution
python3 attribution_integration.py
python3 play_attribution.py

# 3. Train models
python3 uplift_models.py
python3 cv_phase1_sii_v2.py

# 4. Test E2E
python3 e2e_storm_test.py

# 5. View UI
# http://localhost:8501
```

### Check System Status
```bash
# Database stats
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///stormops_attribution.db')
with engine.connect() as conn:
    print('SII_v2:', conn.execute(text('SELECT COUNT(*) FROM sii_v2_scores')).scalar())
    print('Uplift:', conn.execute(text('SELECT COUNT(*) FROM lead_uplift')).scalar())
    print('Attribution:', conn.execute(text('SELECT COUNT(*) FROM channel_attribution')).scalar())
"

# Services status
docker-compose ps

# UI status
curl -s http://localhost:8501 | grep -q "StormOps" && echo "✓ UI running" || echo "✗ UI down"
```

---

**Current Status:** ✅ v1.0 calibrated and tested
**This Week:** Scale to 4,200 + onboard Team 1
**Next 2 Weeks:** Production infrastructure + Team 2
**Month 1:** Multi-team rollout + real CV
