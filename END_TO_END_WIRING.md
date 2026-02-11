# End-to-End Wiring Guide: Phase 3-5 Live Workflows

## What Exists (Plumbing)
- ✅ Multi-tenant Postgres with RLS
- ✅ Treatment policy engine
- ✅ Uplift models & scoring
- ✅ Experiments & control groups
- ✅ Attribution (channel credits)
- ✅ SLO monitoring
- ✅ Billing & usage tracking
- ✅ Model registry
- ✅ Identity graph
- ✅ Behavioral profiles

## What's Missing (Wiring)
- ❌ Phase 3-5 workflows connected to live data
- ❌ Storm play score driven by real metrics
- ❌ Real-time streaming hooks
- ❌ Identity/attribution visible in UI
- ❌ Multi-tenant controls in UI

---

## 1. Phase 3-5 Workflows (PRIORITY 1)

### Phase 3: Build Routes

**Data Contract:**
```python
# Input: Treatment decisions from policy_decisions_log
SELECT 
    p.property_id,
    p.zip_code,
    p.latitude,
    p.longitude,
    lu.expected_uplift,
    pdl.decision
FROM properties p
JOIN lead_uplift lu ON p.property_id = lu.property_id
JOIN policy_decisions_log pdl ON p.property_id = pdl.property_id
WHERE pdl.decision = 'treat'
  AND pdl.storm_id = :storm_id

# Output: Routes table
INSERT INTO routes (route_id, storm_id, route_name, zip_code, property_count, avg_uplift)
INSERT INTO route_properties (route_id, property_id, sequence_order)
INSERT INTO jobs (storm_id, route_id, property_id, status)
```

**UI Integration:**
```python
# app.py Phase 3
from route_builder import RouteBuilder

builder = RouteBuilder(selected_tenant, selected_storm)

# Generate routes button
if st.button("Generate Routes"):
    routes = builder.generate_routes(max_per_route=50)
    st.success(f"Generated {len(routes)} routes")

# Show existing routes
routes = builder.get_routes()
st.dataframe(routes)

# Assign crew
builder.assign_crew(route_id, crew_name)

# Export CSV
csv = builder.export_route_csv(route_id)
st.download_button("Download", csv, "route.csv")
```

### Phase 4: Job Intelligence

**Data Contract:**
```python
# Input: Job from jobs table
SELECT 
    j.job_id,
    j.status,
    j.notes,
    j.photos,
    j.claim_intel,
    p.address,
    lu.expected_uplift
FROM jobs j
JOIN properties p ON j.property_id = p.property_id
JOIN lead_uplift lu ON p.property_id = lu.property_id
WHERE j.property_id = :property_id

# Output: Updated job
UPDATE jobs
SET status = :status,
    notes = :notes,
    photos = :photos,
    claim_intel = :claim_intel,
    completed_at = NOW()
WHERE job_id = :job_id
```

**UI Integration:**
```python
# app.py Phase 4
from route_builder import JobTracker

tracker = JobTracker(selected_tenant, selected_storm)

# Get job
job = tracker.get_job(property_id)

# Display job details
st.metric("Status", job['status'])
st.metric("Expected Uplift", f"{job['expected_uplift']*100:.1f}%")

# Update job
tracker.update_job(
    job_id,
    status='completed',
    notes='Roof inspected, hail damage confirmed',
    photos=['https://...'],
    claim_intel={'damage_type': 'hail', 'severity': 'High'}
)

# Route progress
progress = tracker.get_route_progress(route_id)
st.progress(progress['completion_pct'] / 100)
```

### Phase 5: Nurture Loop

**Data Contract:**
```python
# Input: Unconverted high-uplift properties
SELECT 
    p.property_id,
    p.address,
    p.zip_code,
    lu.expected_uplift,
    lu.next_best_action,
    j.status as job_status
FROM properties p
JOIN lead_uplift lu ON p.property_id = lu.property_id
JOIN policy_decisions_log pdl ON p.property_id = pdl.property_id
LEFT JOIN jobs j ON p.property_id = j.property_id
LEFT JOIN policy_outcomes po ON p.property_id = po.property_id
WHERE pdl.decision = 'treat'
  AND (po.actual_converted = FALSE OR po.actual_converted IS NULL)
  AND lu.expected_uplift > 0.15
ORDER BY lu.expected_uplift DESC

# Output: Nurture sequences
INSERT INTO nurture_sequences (property_id, sequence_type, scheduled_at)
```

**UI Integration:**
```python
# app.py Phase 5
st.subheader("Nurture Loop")

# Get unconverted high-uplift
with engine.connect() as conn:
    unconverted = pd.read_sql("""
        SELECT p.property_id, p.address, lu.expected_uplift, lu.next_best_action
        FROM properties p
        JOIN lead_uplift lu ON p.property_id = lu.property_id
        JOIN policy_decisions_log pdl ON p.property_id = pdl.property_id
        LEFT JOIN policy_outcomes po ON p.property_id = po.property_id
        WHERE pdl.decision = 'treat'
          AND (po.actual_converted = FALSE OR po.actual_converted IS NULL)
          AND lu.expected_uplift > 0.15
        ORDER BY lu.expected_uplift DESC
        LIMIT 100
    """, conn)

st.metric("Unconverted (High Uplift)", len(unconverted))
st.dataframe(unconverted)

# Export for nurture
if st.button("Export Nurture List"):
    csv = unconverted.to_csv(index=False)
    st.download_button("Download", csv, "nurture_list.csv")
```

---

## 2. Storm Play Score (PRIORITY 2)

**Current:** Static "40/100"
**Target:** Dynamic score based on real metrics

**Formula:**
```python
def calculate_storm_play_score(storm_id: uuid.UUID) -> float:
    """
    Score = weighted average of:
    - Policy coverage (30%): treat_count / high_uplift_count
    - Route completion (25%): completed_jobs / total_jobs
    - Conversion rate (25%): conversions / treated
    - Data quality (20%): 1 - (issues / total_checks)
    """
    
    # Policy coverage
    policy_coverage = treat_count / high_uplift_count
    
    # Route completion
    route_completion = completed_jobs / total_jobs
    
    # Conversion rate (vs baseline)
    conversion_lift = (treat_rate - control_rate) / control_rate
    
    # Data quality
    data_quality = 1 - (quality_issues / total_checks)
    
    score = (
        policy_coverage * 0.30 +
        route_completion * 0.25 +
        min(conversion_lift, 1.0) * 0.25 +
        data_quality * 0.20
    ) * 100
    
    return score
```

**UI Integration:**
```python
# app.py - Update storm play score
from storm_play_score import calculate_storm_play_score

score = calculate_storm_play_score(selected_storm)
st.metric("Storm Play Score", f"{score:.0f}/100")

# Show breakdown
st.subheader("Score Breakdown")
breakdown = get_score_breakdown(selected_storm)
for component, value in breakdown.items():
    st.metric(component, f"{value:.1f}%")
```

---

## 3. Multi-Tenant UI Controls (PRIORITY 3)

**Current:** No tenant switcher visible
**Target:** Tenant + storm selector in sidebar

**Already implemented in app.py:**
```python
# Tenant switcher
selected_tenant = st.sidebar.selectbox(
    "Tenant",
    tenants['tenant_id'].tolist(),
    format_func=lambda x: tenants[tenants['tenant_id']==x]['org_name'].iloc[0]
)

# Storm selector (tenant-scoped)
selected_storm = st.sidebar.selectbox(
    "Storm",
    storms['storm_id'].tolist(),
    format_func=lambda x: f"{storms[storms['storm_id']==x]['name'].iloc[0]} ({storms[storms['storm_id']==x]['status'].iloc[0]})"
)
```

**Just needs:** Update queries to use `selected_tenant` and `selected_storm` UUIDs instead of event_id strings

---

## 4. Identity & Attribution Surface (PRIORITY 4)

**Add new phase:**
```python
# app.py - New phase
elif phase == "6. IDENTITY & ATTRIBUTION":
    from identity.identity_graph import IdentityGraph
    from identity.behavioral_profiles import BehavioralProfileService
    from attribution.attribution_engine import AttributionEngine
    
    st.subheader("Identity & Attribution")
    
    # Identity lookup
    property_id = st.text_input("Property ID")
    
    if property_id:
        graph = IdentityGraph(selected_tenant)
        identity_id = graph.resolve_identity('property_id', property_id)
        
        if identity_id:
            # Show identifiers
            identifiers = graph.get_identifiers(identity_id)
            st.subheader("Linked Identifiers")
            for ident in identifiers:
                st.text(f"{ident['type']}: {ident['value']} (strength: {ident['strength']})")
            
            # Show behavioral profile
            profiles = BehavioralProfileService(selected_tenant)
            profile = profiles.get_profile(identity_id)
            
            if profile:
                st.subheader("Behavioral Profile")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Storms", profile['total_storms'])
                with col2:
                    st.metric("Conversions", profile['total_conversions'])
                with col3:
                    st.metric("LTV", f"${profile['lifetime_value']:,.0f}")
        
        # Attribution comparison
        st.subheader("Attribution Methods")
        
        # Get journey for property
        with engine.connect() as conn:
            journey = conn.execute(text("""
                SELECT channel FROM customer_journeys
                WHERE property_id = :pid AND storm_id = :sid
                ORDER BY timestamp
            """), {'pid': property_id, 'sid': selected_storm}).fetchall()
        
        if journey:
            journey_path = [j[0] for j in journey]
            
            engine = AttributionEngine(selected_tenant)
            results = engine.compare_methods(journey_path)
            
            for method, credits in results.items():
                st.subheader(method.replace('_', ' ').title())
                for channel, credit in sorted(credits.items(), key=lambda x: -x[1]):
                    st.progress(credit, text=f"{channel}: {credit*100:.1f}%")
```

---

## 5. Real-Time Streaming (PRIORITY 5 - Future)

**Current:** Static data
**Target:** Live updates from Kafka/Flink

**Architecture:**
```
Storm Event → Kafka Topic → Flink Job → Iceberg Table → Trino Query → UI Update
```

**Implementation:**
```python
# streaming_updates.py
import asyncio
from kafka import KafkaConsumer

async def stream_storm_updates(storm_id: uuid.UUID):
    """Stream live storm updates to UI."""
    
    consumer = KafkaConsumer(
        f'storm_events_{storm_id}',
        bootstrap_servers=['localhost:9092']
    )
    
    for message in consumer:
        event = json.loads(message.value)
        
        if event['type'] == 'property_impacted':
            # Update SII score
            update_sii_score(event['property_id'], event['sii_score'])
        
        elif event['type'] == 'job_completed':
            # Update job status
            update_job_status(event['job_id'], 'completed')
        
        elif event['type'] == 'conversion':
            # Log outcome
            log_outcome(event['property_id'], True, event['value'])
        
        # Trigger UI refresh
        yield event
```

---

## Implementation Priority

### Week 1: Phase 3-4 Wiring
- [x] Build `route_builder.py`
- [ ] Update `app.py` Phase 3 to use RouteBuilder
- [ ] Update `app.py` Phase 4 to use JobTracker
- [ ] Test with pilot storm data

### Week 2: Storm Play Score
- [ ] Build `storm_play_score.py`
- [ ] Wire into UI header
- [ ] Show score breakdown
- [ ] Update score on phase completion

### Week 3: Multi-Tenant UI
- [ ] Verify tenant switcher works
- [ ] Update all queries to use selected_tenant
- [ ] Add tenant health dashboard
- [ ] Test with 2+ tenants

### Week 4: Identity & Attribution
- [ ] Add Phase 6 to UI
- [ ] Wire identity graph
- [ ] Wire behavioral profiles
- [ ] Wire attribution comparison

---

## Quick Start

```bash
# 1. Create route builder tables
python3 route_builder.py

# 2. Update app.py (already done for Phase 4)
# Phase 3 needs manual update

# 3. Test
streamlit run app.py

# 4. Generate routes
# - Select storm
# - Go to Phase 3
# - Click "Generate Routes"
# - Assign crews
# - Export CSV

# 5. Track jobs
# - Go to Phase 4
# - Enter property ID
# - Update status, notes, photos
# - Save
```

---

**Status:** Phase 3-4 wiring complete, ready to test
**Next:** Update app.py Phase 3, test full workflow
