# StormOps Product Programs Roadmap

## Overview

Transform 8 whitepapers into **3 product programs** that become core StormOps features.

**Repo Structure:**
```
integrations/
├── probabilistic-identity-resolution/     → Identity Program
├── behavioral-profiling-*/                → Identity Program  
├── first-principles-attribution/          → Attribution Program
└── real-time-streaming-*/                 → Real-Time Program
```

---

## Program 1: Identity & Profiles (Foundation)

**Whitepapers:**
- `probabilistic-identity-resolution/WHITEPAPER.md`
- `probabilistic-identity-resolution/docs/Multiplatform_Identity_Resolution.pdf`
- `behavioral-profiling-*/WHITEPAPER.md`

**What to Build:**

### 1.1 Unified Identity Graph
**File:** `identity_graph.py`

```python
"""
Unified identity graph for homeowners across channels/devices/storms
Deterministic + probabilistic linking
"""

class IdentityGraph:
    def link_property(self, property_id, identifiers: Dict) -> uuid.UUID
    def resolve_identity(self, identifier: str) -> uuid.UUID
    def get_profile(self, identity_id: uuid.UUID) -> Dict
    def merge_identities(self, id_a: uuid.UUID, id_b: uuid.UUID)
```

**Schema:**
```sql
CREATE TABLE identities (
    identity_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE identity_links (
    link_id UUID PRIMARY KEY,
    identity_id UUID NOT NULL REFERENCES identities(identity_id),
    identifier_type TEXT NOT NULL,  -- email, phone, device_id, property_id
    identifier_value TEXT NOT NULL,
    link_strength FLOAT NOT NULL,   -- 0.0-1.0 (deterministic=1.0)
    linked_at TIMESTAMPTZ NOT NULL
);
```

### 1.2 Behavioral Profile Service
**File:** `behavioral_profiles.py`

```python
"""
Behavioral profiles keyed by identity_id
Aggregates journeys, plays, experiments, SII, uplift, claims
"""

class BehavioralProfileService:
    def get_profile(self, identity_id: uuid.UUID) -> Dict
    def update_profile(self, identity_id: uuid.UUID, event: Dict)
    def get_segment(self, identity_id: uuid.UUID) -> str
    def get_lifetime_value(self, identity_id: uuid.UUID) -> float
```

**Schema:**
```sql
CREATE TABLE behavioral_profiles (
    identity_id UUID PRIMARY KEY REFERENCES identities(identity_id),
    tenant_id UUID NOT NULL,
    total_storms INT DEFAULT 0,
    total_conversions INT DEFAULT 0,
    lifetime_value FLOAT DEFAULT 0,
    avg_sii_score FLOAT,
    avg_uplift FLOAT,
    primary_channel TEXT,
    segment TEXT,
    last_updated TIMESTAMPTZ NOT NULL
);
```

**Integration Points:**
- Link `properties` → `identities` via `identity_links`
- Link `customer_journeys` → `identities`
- Update profiles on every journey event
- Use in targeting: "target identities with LTV > $50k"

---

## Program 2: Causal & Incrementality (Core IP)

**Whitepapers:**
- `first-principles-attribution/docs/WHITEPAPER.md` (causal inference)
- Existing: `experiments`, `control_groups`, `uplift_models`

**What to Build:**

### 2.1 Experiments Platform
**File:** `experiments_platform.py`

```python
"""
First-class experiments with templates
Geo-split, holdout, creative/policy tests, model A/B
"""

class ExperimentsPlatform:
    def create_experiment(self, template: str, config: Dict) -> uuid.UUID
    def assign_properties(self, experiment_id: uuid.UUID, properties: List)
    def measure_lift(self, experiment_id: uuid.UUID) -> Dict
    def get_confidence_interval(self, experiment_id: uuid.UUID) -> Tuple
```

**Templates:**
```python
EXPERIMENT_TEMPLATES = {
    'geo_split': {
        'description': 'Geographic holdout test',
        'assignment': 'by_zip',
        'variants': ['treatment', 'control']
    },
    'policy_test': {
        'description': 'Test treatment policy',
        'assignment': 'by_uplift_band',
        'variants': ['aggressive', 'moderate', 'conservative']
    },
    'model_ab': {
        'description': 'A/B test model versions',
        'assignment': 'random',
        'variants': ['model_a', 'model_b']
    },
    'creative_test': {
        'description': 'Test messaging/creative',
        'assignment': 'by_persona',
        'variants': ['creative_a', 'creative_b', 'creative_c']
    }
}
```

### 2.2 Incrementality Reporting
**File:** `incrementality_reporting.py`

```python
"""
Standard incrementality reports with confidence intervals
Per-play, per-channel, per-tenant lift
"""

class IncrementalityReporter:
    def calculate_lift(self, experiment_id: uuid.UUID) -> Dict
    def get_confidence_interval(self, lift: float, n_treat: int, n_control: int) -> Tuple
    def generate_report(self, storm_id: uuid.UUID) -> Dict
```

**UI Integration:**
Add to `app.py`:
```python
# New phase: INCREMENTALITY
elif phase == "6. INCREMENTALITY":
    st.subheader("Incrementality Report")
    
    reporter = IncrementalityReporter()
    report = reporter.generate_report(selected_storm)
    
    st.metric("Overall Lift", f"{report['lift']*100:+.1f} pts")
    st.metric("Confidence", f"{report['confidence']*100:.0f}%")
    
    # Per-channel lift
    st.subheader("Lift by Channel")
    for channel, metrics in report['by_channel'].items():
        st.metric(channel, f"{metrics['lift']*100:+.1f} pts")
```

---

## Program 3: First-Principles Attribution (Defensible IP)

**Whitepapers:**
- `first-principles-attribution/docs/WHITEPAPER.md`
- `first-principles-attribution/docs/TECHNICAL_DOCUMENTATION.md`

**What to Build:**

### 3.1 Configurable Attribution Engine
**File:** `attribution_engine.py`

```python
"""
Rules-based + Markov + Shapley attribution
Per-tenant configs
"""

class AttributionEngine:
    def __init__(self, tenant_id: uuid.UUID, config: Dict):
        self.tenant_id = tenant_id
        self.config = config  # rules, markov, shapley, hybrid
    
    def attribute_journey(self, journey_id: uuid.UUID) -> Dict
    def attribute_storm(self, storm_id: uuid.UUID) -> Dict
    def compare_methods(self, storm_id: uuid.UUID) -> Dict
```

**Attribution Methods:**
```python
ATTRIBUTION_METHODS = {
    'last_touch': {
        'description': 'Last touchpoint gets 100% credit',
        'complexity': 'low'
    },
    'first_touch': {
        'description': 'First touchpoint gets 100% credit',
        'complexity': 'low'
    },
    'linear': {
        'description': 'Equal credit across all touchpoints',
        'complexity': 'low'
    },
    'time_decay': {
        'description': 'More recent touchpoints get more credit',
        'complexity': 'medium',
        'params': {'half_life_days': 7}
    },
    'markov': {
        'description': 'Removal effect based on transition probabilities',
        'complexity': 'high'
    },
    'shapley': {
        'description': 'Game-theoretic fair allocation',
        'complexity': 'very_high'
    }
}
```

### 3.2 Incremental Attribution
**File:** `incremental_attribution.py`

```python
"""
Lift-based attribution (incremental credit)
Combines causal lift with fractional credit
"""

class IncrementalAttribution:
    def calculate_incremental_credit(self, journey_id: uuid.UUID) -> Dict
    def compare_fractional_vs_incremental(self, storm_id: uuid.UUID) -> Dict
```

**Formula:**
```
Incremental Credit = Fractional Credit × Lift Multiplier

Where:
  Fractional Credit = Shapley/Markov credit (0-1)
  Lift Multiplier = (Treatment Rate - Control Rate) / Control Rate
```

**Schema:**
```sql
CREATE TABLE attribution_results (
    result_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    storm_id UUID NOT NULL,
    journey_id UUID NOT NULL,
    method TEXT NOT NULL,
    touchpoint_credits JSONB NOT NULL,  -- {channel: credit}
    incremental_credits JSONB,          -- {channel: incremental_credit}
    calculated_at TIMESTAMPTZ NOT NULL
);
```

---

## Program 4: Real-Time & MMM (Later)

**Whitepapers:**
- `real-time-streaming-attribution-dashboard/WHITEPAPER.md`

**What to Build (Phase 2):**

### 4.1 Live Event Attribution
**File:** `live_attribution.py`

```python
"""
Real-time attribution on Kafka/Flink
Updates cockpit during storm
"""

class LiveAttribution:
    def process_event(self, event: Dict)
    def update_attribution(self, journey_id: uuid.UUID)
    def get_live_dashboard(self, storm_id: uuid.UUID) -> Dict
```

### 4.2 MMM Layer
**File:** `mmm.py`

```python
"""
Marketing Mix Modeling for long-range budgeting
Uses identity and causal primitives
"""

class MMM:
    def fit_model(self, tenant_id: uuid.UUID, months: int)
    def predict_roi(self, budget_allocation: Dict) -> Dict
    def optimize_budget(self, total_budget: float) -> Dict
```

---

## Implementation Sequence

### Sprint 1: Identity Foundation
**Week 1-2**
- [ ] Build `identity_graph.py`
- [ ] Add schema tables
- [ ] Link properties → identities
- [ ] Test with pilot storm data

### Sprint 2: Behavioral Profiles
**Week 3-4**
- [ ] Build `behavioral_profiles.py`
- [ ] Add profile schema
- [ ] Update profiles on journey events
- [ ] Add profile view to UI

### Sprint 3: Experiments Platform
**Week 5-6**
- [ ] Build `experiments_platform.py`
- [ ] Add experiment templates
- [ ] Build experiment UI
- [ ] Run first geo-split test

### Sprint 4: Incrementality Reporting
**Week 7-8**
- [ ] Build `incrementality_reporting.py`
- [ ] Add confidence intervals
- [ ] Build report UI
- [ ] Generate first report

### Sprint 5: Attribution Engine
**Week 9-10**
- [ ] Build `attribution_engine.py`
- [ ] Implement Markov + Shapley
- [ ] Add per-tenant configs
- [ ] Compare methods

### Sprint 6: Incremental Attribution
**Week 11-12**
- [ ] Build `incremental_attribution.py`
- [ ] Combine lift + fractional credit
- [ ] Add to UI
- [ ] Validate with pilot data

---

## File Structure

```
stormops/
├── identity/
│   ├── identity_graph.py
│   ├── behavioral_profiles.py
│   └── tests/
├── experiments/
│   ├── experiments_platform.py
│   ├── incrementality_reporting.py
│   └── templates/
├── attribution/
│   ├── attribution_engine.py
│   ├── incremental_attribution.py
│   ├── methods/
│   │   ├── markov.py
│   │   ├── shapley.py
│   │   └── time_decay.py
│   └── tests/
└── integrations/  (existing whitepapers)
    ├── probabilistic-identity-resolution/
    ├── behavioral-profiling-*/
    ├── first-principles-attribution/
    └── real-time-streaming-*/
```

---

## Success Metrics

### Identity Program
- ✅ 95%+ property → identity link rate
- ✅ < 1% false positive links
- ✅ Profiles update in < 1s

### Causal Program
- ✅ 5+ experiment templates
- ✅ Confidence intervals on all lift metrics
- ✅ One-click incrementality reports

### Attribution Program
- ✅ 3+ attribution methods (Markov, Shapley, hybrid)
- ✅ Per-tenant configs
- ✅ Incremental credit calculated
- ✅ "StormOps improved conversions by +X pts with 95% confidence"

---

## Next Steps

1. **Review this roadmap** with team
2. **Start Sprint 1** (Identity Foundation)
3. **Migrate whitepaper code** into product programs
4. **Run pilot** with identity + experiments
5. **Iterate** based on contractor feedback

---

**Status:** Roadmap defined, ready to build
**Timeline:** 12 weeks to complete all 3 programs
**Priority:** Identity → Causal → Attribution
