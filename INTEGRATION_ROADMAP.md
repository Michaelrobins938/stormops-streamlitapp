# StormOps Integration Roadmap

## Status: Repos Cloned ✅

All 5 repos are now in `/home/forsythe/kirocli/kirocli/integrations/`

## The 5 Engines

### 1. first-principles-attribution ⭐ START HERE
**Path:** `integrations/first-principles-attribution/`

**What it does:**
- Markov chain + Shapley value attribution
- Bayesian uncertainty quantification
- Channel/play credit allocation with confidence intervals

**StormOps integration:**
```
Lakehouse (Iceberg) → Trino query → Journey events
    ↓
Attribution Engine (Node.js)
    ↓
Channel/Play credits → Postgres
    ↓
UI displays attribution
```

**Minimal wiring:**
1. Create `attribution_integration.py` (done ✅)
2. Wire `_fetch_journeys_from_lakehouse()` to Trino
3. Create Postgres tables:
   - `channel_attribution` (zip, event, channel, credit, timestamp)
   - `play_attribution` (zip, event, play_id, credit, timestamp)
4. Call from UI: "Show attribution for DFW Storm 24"

**Example query:**
```python
from attribution_integration import AttributionEngine

engine = AttributionEngine()
attribution = engine.get_channel_attribution(
    zip_code='75209',
    event_id='DFW_STORM_24'
)

# Returns:
# {
#   'channels': {'door_knock': 0.35, 'sms': 0.25, 'ga4': 0.20, 'call': 0.20},
#   'plays': {'Financing_Aggressive': 0.40, 'Impact_Report_Premium': 0.35, ...},
#   'uncertainty': {'door_knock': [0.30, 0.40], ...}  # 90% CI
# }
```

---

### 2. behavioral-profiling-attribution-psychographic-priors
**Path:** `integrations/behavioral-profiling-attribution-psychographic-priors/`

**What it does:**
- Psychographic segmentation (matches your personas)
- Channel/script priors per household
- Behavioral profiling features

**StormOps integration:**
```
Property features → Profiling engine
    ↓
Persona + channel priors → Property table
    ↓
Used in SII model + attribution
```

**Minimal wiring:**
1. Extract persona classification logic
2. Generate priors for each A-tier lead:
   - Deal_Hunter → High sensitivity to financing plays, SMS channel
   - Proof_Seeker → High sensitivity to impact reports, email channel
3. Store as `persona_priors` JSON column in properties table
4. Use in attribution engine as Markov transition weights

**Example:**
```python
from behavioral_profiling import PersonaEngine

engine = PersonaEngine()
priors = engine.get_priors(
    persona='Deal_Hunter',
    income=45000,
    property_value=450000
)

# Returns:
# {
#   'channels': {'sms': 1.3, 'door_knock': 1.2, 'email': 0.8},
#   'plays': {'Financing_Aggressive': 1.5, 'Premium_Showcase': 0.6}
# }
```

---

### 3. real-time-streaming-attribution-dashboard
**Path:** `integrations/real-time-streaming-attribution-dashboard/`

**What it does:**
- Flink streaming jobs for live attribution
- WebSocket patterns for real-time UI updates
- Event-driven architecture

**StormOps integration:**
```
Kafka events → Flink job → Live attribution
    ↓
WebSocket → UI updates in real-time
```

**Minimal wiring:**
1. Adapt Flink job templates for StormOps events
2. Create WebSocket endpoint in UI
3. Stream live updates:
   - New lead generated → Update play score
   - Door knock logged → Update attribution
   - Claim filed → Update conversion metrics

**Example Flink job:**
```sql
-- Real-time play performance
SELECT 
    play_id,
    COUNT(*) as touches,
    SUM(CASE WHEN converted THEN 1 ELSE 0 END) as conversions,
    AVG(sii_score) as avg_sii
FROM stormops_events
WHERE event_timestamp > NOW() - INTERVAL '1' HOUR
GROUP BY play_id, TUMBLE(event_timestamp, INTERVAL '5' MINUTE)
```

---

### 4. probabilistic-identity-resolution
**Path:** `integrations/probabilistic-identity-resolution/`

**What it does:**
- Stitch GA4, CRM, call tracking, door knock events
- Probabilistic matching without hard IDs
- Household-level identity graph

**StormOps integration:**
```
GA4 events (cookie_id) + Door knocks (address) + Calls (phone)
    ↓
Identity resolution
    ↓
Unified household_id → Journey table
```

**Minimal wiring:**
1. Create identity graph in Neo4j
2. Match events across sources:
   - GA4 session → Address (via ZIP + property features)
   - Phone number → Property (via CRM)
   - Email → Household (via enrichment)
3. Write resolved `household_id` to journey events

**Example:**
```python
from identity_resolution import IdentityGraph

graph = IdentityGraph()
household_id = graph.resolve(
    ga4_cookie='abc123',
    address='8611 Chadbourne Rd, Dallas, TX 75209',
    phone='+1-555-0100'
)

# Returns: household_uuid
# All events now linked to same household for attribution
```

---

### 5. portfolio-hub
**Path:** `integrations/portfolio-hub/`

**What it does:**
- Next.js command center UI
- Tactical dashboards
- Strategy lab front-end

**StormOps integration:**
```
Replace/augment Streamlit UI with Next.js
    ↓
Show SII/MOE metrics, attribution, persona mix
    ↓
Tactical command center
```

**Minimal wiring:**
1. Adapt dashboard components for StormOps
2. Create API endpoints in backend
3. Deploy as separate strategy lab UI
4. Keep Streamlit for operational control plane

**Example pages:**
- `/storm/DFW_STORM_24` - Event overview
- `/attribution` - Channel/play performance
- `/personas` - Persona distribution + performance
- `/plays` - Play effectiveness + SLA tracking

---

## Integration Sequence

### Phase 1: Attribution Engine (Week 1)
1. ✅ Clone repos
2. Wire `attribution_integration.py` to Trino
3. Create Postgres attribution tables
4. Run attribution on A-tier journeys
5. Display in UI

**Deliverable:** "Show attribution for DFW Storm 24" query works

### Phase 2: Persona Priors (Week 2)
1. Extract persona classification from behavioral-profiling
2. Generate priors for A-tier leads
3. Store in properties table
4. Use in attribution engine

**Deliverable:** Attribution weighted by persona priors

### Phase 3: Identity Resolution (Week 3)
1. Set up Neo4j identity graph
2. Implement probabilistic matching
3. Resolve household IDs across sources
4. Update journey table

**Deliverable:** Unified household journeys

### Phase 4: Real-Time Streaming (Week 4)
1. Adapt Flink jobs for StormOps
2. Set up Kafka → Flink → WebSocket pipeline
3. Add real-time UI updates
4. Live play score updates

**Deliverable:** Live attribution dashboard

### Phase 5: Strategy Lab UI (Week 5)
1. Adapt portfolio-hub components
2. Create StormOps API endpoints
3. Deploy Next.js UI
4. Integrate with attribution + personas

**Deliverable:** Tactical command center UI

---

## Quick Start: Attribution Engine

### 1. Install Dependencies
```bash
cd integrations/first-principles-attribution
npm install
```

### 2. Test Attribution Engine
```bash
node src/attribution.js --input sample_journeys.json --output test_output.json
```

### 3. Wire to StormOps
```python
from attribution_integration import AttributionEngine

engine = AttributionEngine()
attribution = engine.get_channel_attribution('75209', 'DFW_STORM_24')
print(attribution)
```

### 4. Create Postgres Tables
```sql
CREATE TABLE channel_attribution (
    zip_code TEXT,
    event_id TEXT,
    channel TEXT,
    credit FLOAT,
    timestamp TIMESTAMP,
    PRIMARY KEY (zip_code, event_id, channel)
);

CREATE TABLE play_attribution (
    zip_code TEXT,
    event_id TEXT,
    play_id TEXT,
    credit FLOAT,
    timestamp TIMESTAMP,
    PRIMARY KEY (zip_code, event_id, play_id)
);
```

### 5. Query from UI
```python
# In UI copilot or dashboard
attribution = get_attribution('75209', 'DFW_STORM_24')

# Display:
# Door Knock: 35% ± 5%
# SMS: 25% ± 4%
# GA4: 20% ± 6%
# Call: 20% ± 5%
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     StormOps Control Plane                  │
│                    (Streamlit + Next.js)                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Integration Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Attribution  │  │  Behavioral  │  │   Identity   │     │
│  │   Engine     │  │  Profiling   │  │  Resolution  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Iceberg    │  │   Postgres   │  │    Neo4j     │     │
│  │  (Lakehouse) │  │  (Ops Data)  │  │  (Identity)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Streaming Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Kafka     │  │    Flink     │  │  WebSocket   │     │
│  │  (Events)    │  │ (Real-time)  │  │   (Live UI)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Files Created

1. `/home/forsythe/kirocli/kirocli/integrations/` - All 5 repos cloned
2. `/home/forsythe/kirocli/kirocli/attribution_integration.py` - Minimal adapter
3. This roadmap document

## Next Action

**Start with attribution engine:**

```bash
cd /home/forsythe/kirocli/kirocli/integrations/first-principles-attribution
npm install
node src/attribution.js --input sample_journeys.json --output test.json
cat test.json
```

Then wire `attribution_integration.py` to your Trino lakehouse.
