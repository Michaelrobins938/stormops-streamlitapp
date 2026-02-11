# StormOps Competitor Intelligence v1.0

## Overview
Transform StormOps into a competitor intelligence platform by fusing public permit data with your physics engine (SII/MOE), ops graph, and CRM. Identify market share, reaction speed, white-space opportunities, and generate tactical playbooks.

**Core Insight**: Physics predicts demand → Permits reveal who captured it → Your CRM shows what you captured → Gap = opportunity or threat.

---

## Data Sources

### 1. Public Building Permits

**Dallas Open Data**:
- **URL**: https://www.dallasopendata.com/Services/Building-Permits/e7gq-4sah
- **Fields**: contractor_name, contractor_license, permit_type, valuation, issue_date, address

**Statewide Feeds**:
- Texas Department of Licensing and Regulation (TDLR)
- County-level permit portals

**Third-Party APIs**:
- **Shovels.ai**: https://www.shovels.ai/api
  - Standardized multi-city permit data
  - Contractor normalization
  - Project classification
- **Warren Group / HBW**: https://www.thewarrengroup.com/blog/building-permit-data-a-key-resource-for-construction-companies-contractors-and-real-estate-developers/

### 2. Roofing-Specific Layers

**ArcGIS Roofing Permit Layers**:
- Pre-filtered for roofing permits
- Contractor metadata included
- Example: https://www.shovels.ai/blog/analyzing-texas-roofing-permits-by-income-bracket/

### 3. Competitor Benchmarks (Reference Only)

**Market Tools**:
- **Convex**: https://www.convex.com/solutions-roofing-industry
- **Roof Chief**: Territory visualization
- **Note**: Don't clone—your edge is Earth-2 physics + permits + behavior

---

## Data Model

### competitor_contractors

```sql
CREATE TABLE competitor_contractors (
    contractor_id UUID PRIMARY KEY,
    
    -- Identity
    contractor_name TEXT NOT NULL,
    normalized_name TEXT,              -- "ABC Roofing LLC" → "abc roofing"
    contractor_license TEXT UNIQUE,
    
    -- Contact
    phone TEXT,
    email TEXT,
    website TEXT,
    
    -- Classification
    company_size TEXT,                 -- Solo, Small (2-10), Medium (11-50), Large (50+)
    specialization TEXT,               -- Residential, Commercial, Both
    
    -- Competitive tier
    tier TEXT,                         -- Tier1 (top threat), Tier2, Tier3, Unknown
    
    -- Metadata
    first_seen_date DATE,
    last_permit_date DATE,
    total_permits_lifetime INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_license (contractor_license),
    INDEX idx_normalized (normalized_name),
    INDEX idx_tier (tier)
);
```

### competitor_activity

```sql
CREATE TABLE competitor_activity (
    activity_id UUID PRIMARY KEY,
    
    -- Linkage
    contractor_id UUID REFERENCES competitor_contractors(contractor_id),
    permit_id TEXT REFERENCES building_permits(permit_id),
    property_id UUID REFERENCES properties(property_id),
    event_id TEXT REFERENCES storm_events(event_id),
    
    -- Geography
    census_tract_geoid TEXT,
    zip_code TEXT,
    
    -- Activity details
    permit_date DATE,
    permit_type TEXT,
    valuation INTEGER,
    project_type TEXT,                 -- Re-Roof, Repair, New Construction
    
    -- Timing
    days_since_storm INTEGER,          -- NULL if no recent storm
    reaction_speed_tier TEXT,          -- Fast (<14d), Medium (14-30d), Slow (>30d)
    
    -- Context
    sii_score_at_permit DECIMAL(5, 2),
    tract_median_income INTEGER,
    ses_tier TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_contractor (contractor_id),
    INDEX idx_permit_date (permit_date),
    INDEX idx_tract (census_tract_geoid),
    INDEX idx_event (event_id)
);
```

### competitor_metrics

```sql
CREATE TABLE competitor_metrics (
    metric_id UUID PRIMARY KEY,
    contractor_id UUID REFERENCES competitor_contractors(contractor_id),
    
    -- Time window
    period_start DATE,
    period_end DATE,
    period_type TEXT,                  -- Monthly, Quarterly, Yearly
    
    -- Geography
    geography_type TEXT,               -- ZIP, Tract, County, Market
    geography_id TEXT,
    
    -- Volume metrics
    permit_count INTEGER,
    total_valuation BIGINT,
    avg_project_value INTEGER,
    
    -- Market share
    market_share_pct DECIMAL(5, 2),    -- % of permits in geography
    revenue_share_pct DECIMAL(5, 2),   -- % of valuation in geography
    rank_by_permits INTEGER,
    rank_by_revenue INTEGER,
    
    -- Speed metrics
    avg_reaction_days DECIMAL(6, 2),   -- Avg days from storm to permit
    fast_response_count INTEGER,       -- Permits within 14 days of storm
    
    -- Segment focus
    high_ses_permits INTEGER,          -- Permits in high-income tracts
    medium_ses_permits INTEGER,
    low_ses_permits INTEGER,
    avg_ticket_size INTEGER,
    
    -- Trend
    growth_rate_pct DECIMAL(6, 2),     -- vs. prior period
    
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_contractor (contractor_id),
    INDEX idx_period (period_start, period_end),
    INDEX idx_geography (geography_type, geography_id)
);
```

### white_space_opportunities

```sql
CREATE TABLE white_space_opportunities (
    opportunity_id UUID PRIMARY KEY,
    
    -- Geography
    geography_type TEXT,               -- ZIP, Tract, Sector
    geography_id TEXT,
    geometry GEOMETRY(POLYGON, 4326),
    
    -- Demand signal (physics)
    expected_demand_score DECIMAL(6, 2),  -- Avg SII × property count
    total_properties INTEGER,
    high_sii_properties INTEGER,       -- SII > 70
    
    -- Supply signal (permits)
    actual_permits_90d INTEGER,
    expected_permits_90d INTEGER,      -- Based on historical conversion
    supply_gap INTEGER,                -- expected - actual
    
    -- Competition
    active_contractors INTEGER,
    dominant_contractor_id UUID REFERENCES competitor_contractors(contractor_id),
    dominant_contractor_share DECIMAL(5, 2),
    market_concentration TEXT,         -- Monopoly, Oligopoly, Fragmented
    
    -- Your presence
    your_permits_90d INTEGER,
    your_market_share DECIMAL(5, 2),
    
    -- Opportunity classification
    opportunity_type TEXT,             -- Enter_New, Disrupt_Weak, Defend_Territory, Avoid_Saturated
    priority_score DECIMAL(5, 2),      -- 0-100
    
    -- Metadata
    last_storm_date DATE,
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_geography (geography_type, geography_id),
    INDEX idx_opportunity_type (opportunity_type),
    INDEX idx_priority (priority_score)
);
```

---

## Key Performance Indicators (KPIs)

### 1. Market Share by Geography

**Definition**: Your permits / Total permits in geography over time window

```python
def calculate_market_share(geography_id: str, days: int = 90) -> dict:
    """Calculate market share metrics for a geography."""
    cutoff = datetime.now() - timedelta(days=days)
    
    # Total market
    total_permits = permits.filter(
        geography_id=geography_id,
        permit_date >= cutoff,
        permit_type__contains='Roof'
    ).count()
    
    total_valuation = permits.filter(
        geography_id=geography_id,
        permit_date >= cutoff
    ).aggregate(Sum('valuation'))['valuation__sum']
    
    # Your share
    your_permits = permits.filter(
        geography_id=geography_id,
        permit_date >= cutoff,
        contractor_id=YOUR_CONTRACTOR_ID
    ).count()
    
    your_valuation = permits.filter(
        geography_id=geography_id,
        permit_date >= cutoff,
        contractor_id=YOUR_CONTRACTOR_ID
    ).aggregate(Sum('valuation'))['valuation__sum']
    
    return {
        'permit_share': your_permits / total_permits if total_permits > 0 else 0,
        'revenue_share': your_valuation / total_valuation if total_valuation > 0 else 0,
        'total_market_permits': total_permits,
        'your_permits': your_permits,
        'rank': get_rank_by_permits(geography_id, YOUR_CONTRACTOR_ID)
    }
```

### 2. Reaction Speed Index

**Definition**: Avg days from storm event to first permit, by contractor

```python
def calculate_reaction_speed(contractor_id: str, event_id: str) -> dict:
    """Calculate how fast contractor responded to storm."""
    event = storm_events.get(event_id=event_id)
    
    permits = competitor_activity.filter(
        contractor_id=contractor_id,
        event_id=event_id
    ).order_by('permit_date')
    
    if not permits:
        return {'reaction_days': None, 'tier': 'No_Response'}
    
    first_permit = permits.first()
    reaction_days = (first_permit.permit_date - event.begin_datetime.date()).days
    
    # Classify
    if reaction_days <= 14:
        tier = 'Fast'
    elif reaction_days <= 30:
        tier = 'Medium'
    else:
        tier = 'Slow'
    
    return {
        'reaction_days': reaction_days,
        'tier': tier,
        'permits_in_30d': permits.filter(days_since_storm__lte=30).count(),
        'total_permits': permits.count()
    }
```

### 3. Deal Size & Positioning

**Definition**: Avg permit valuation by SES tier, by contractor

```python
def analyze_positioning(contractor_id: str) -> dict:
    """Determine which market segments contractor targets."""
    permits = competitor_activity.filter(
        contractor_id=contractor_id,
        permit_date__gte=datetime.now() - timedelta(days=365)
    )
    
    by_ses = permits.values('ses_tier').annotate(
        count=Count('activity_id'),
        avg_valuation=Avg('valuation'),
        total_valuation=Sum('valuation')
    )
    
    total_permits = permits.count()
    
    positioning = {}
    for tier in by_ses:
        positioning[tier['ses_tier']] = {
            'permit_count': tier['count'],
            'share_of_permits': tier['count'] / total_permits,
            'avg_ticket': tier['avg_valuation'],
            'total_revenue': tier['total_valuation']
        }
    
    # Classify
    if positioning.get('High', {}).get('share_of_permits', 0) > 0.5:
        segment = 'Premium'
    elif positioning.get('Low', {}).get('share_of_permits', 0) > 0.5:
        segment = 'Budget'
    else:
        segment = 'Mixed'
    
    return {
        'primary_segment': segment,
        'by_ses_tier': positioning,
        'overall_avg_ticket': permits.aggregate(Avg('valuation'))['valuation__avg']
    }
```

### 4. White-Space Score

**Definition**: (Expected demand - Actual supply) × Market attractiveness

```python
def calculate_white_space(geography_id: str) -> dict:
    """Identify under-served high-opportunity areas."""
    # Physics: expected demand
    properties = properties_table.filter(census_tract_geoid=geography_id)
    expected_demand = properties.filter(sii_score__gte=70).count()
    avg_sii = properties.aggregate(Avg('sii_score'))['sii_score__avg']
    
    # Permits: actual supply
    actual_permits = competitor_activity.filter(
        census_tract_geoid=geography_id,
        permit_date__gte=datetime.now() - timedelta(days=90)
    ).count()
    
    # Historical conversion rate
    historical_rate = 0.15  # 15% of high-SII properties typically permit within 90d
    expected_permits = expected_demand * historical_rate
    
    supply_gap = expected_permits - actual_permits
    
    # Competition
    contractors = competitor_activity.filter(
        census_tract_geoid=geography_id,
        permit_date__gte=datetime.now() - timedelta(days=90)
    ).values('contractor_id').distinct().count()
    
    # Market attractiveness
    tract = census_tracts.get(tract_geoid=geography_id)
    income_score = min(tract.median_household_income / 100000, 1.0)  # Normalize
    
    # White-space score
    opportunity_score = (
        supply_gap * 10 +                    # Demand gap
        avg_sii * 0.5 +                      # Physics signal
        income_score * 20 +                  # Affluence
        (5 - contractors) * 5                # Low competition bonus
    )
    
    return {
        'expected_demand': expected_demand,
        'actual_permits': actual_permits,
        'supply_gap': supply_gap,
        'active_contractors': contractors,
        'opportunity_score': max(0, opportunity_score),
        'recommendation': classify_opportunity(supply_gap, contractors)
    }

def classify_opportunity(gap: int, competitors: int) -> str:
    """Classify opportunity type."""
    if gap > 20 and competitors < 2:
        return 'Enter_New'
    elif gap > 10 and competitors < 4:
        return 'Disrupt_Weak'
    elif gap < -10:
        return 'Avoid_Saturated'
    elif competitors > 5:
        return 'Defend_Territory'
    else:
        return 'Monitor'
```

---

## Control Plane Integration

### Competitor Heatmap Pane

**Visual Components**:
1. **Map Layer**: Permits colored by contractor over last 90 days
2. **SII Overlay**: Hail swaths with intensity gradient
3. **Your Territory**: Your permits highlighted in distinct color
4. **Competitor Clusters**: Density heatmap of top 5 competitors

**Filters**:
- Time range (30/60/90/180 days)
- Contractor tier (Tier1, Tier2, All)
- SES segment (High, Medium, Low)
- Storm event (filter to specific hail event)

**Metrics Panel**:
```
Market Overview (Dallas County, Last 90 Days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Roofing Permits:        1,247
Total Market Value:            $18.7M
Active Contractors:            89

Your Performance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your Permits:                  143 (11.5%)
Your Revenue:                  $2.1M (11.2%)
Market Rank:                   #3
Avg Ticket Size:               $14,685

Top Competitors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ABC Roofing                 18.2% | $3.4M | Avg: $16,200
2. XYZ Contractors             14.7% | $2.7M | Avg: $15,100
3. Your Company                11.5% | $2.1M | Avg: $14,685
4. Rapid Roof                  9.3%  | $1.7M | Avg: $13,800
5. Elite Exteriors             7.8%  | $1.5M | Avg: $18,900
```

### Playbook Overlay

**Auto-Generated Tactical Recommendations**:

```python
@dataclass
class CompetitorPlaybook:
    playbook_id: str
    geography_id: str
    opportunity_type: str
    priority: int  # 1-5
    
    # Situation
    situation_summary: str
    key_metrics: dict
    
    # Recommendation
    action: str
    rationale: str
    expected_outcome: str
    
    # Execution
    suggested_tactics: List[str]
    resource_allocation: dict
    timeline_days: int
```

**Example Playbooks**:

#### Playbook 1: Enter & Disrupt
```yaml
Geography: ZIP 75201 (Downtown Dallas)
Opportunity: Enter_New
Priority: 1 (Highest)

Situation:
  - Recent hail event (2024-03-15) with avg SII 78
  - 234 high-SII properties
  - Only 12 permits filed in 90 days (expected: 35)
  - 2 active competitors (both Tier3)
  - High SES tract (median income: $95K)

Recommendation:
  Action: "Aggressive entry campaign"
  Rationale: "Physics predicts high demand, weak competition, affluent market"
  Expected Outcome: "Capture 40% market share (14 jobs) in 60 days = $210K revenue"

Tactics:
  - Deploy 2 canvassing teams immediately
  - Run targeted Facebook ads to ZIP 75201
  - Offer free drone inspections
  - Price premium (+10%) given low competition
  
Resources:
  - Canvassers: 2 teams × 60 days
  - Ad spend: $3,000
  - Drone ops: 50 inspections
  
Timeline: 60 days
```

#### Playbook 2: Defend Territory
```yaml
Geography: ZIP 75230 (North Dallas)
Opportunity: Defend_Territory
Priority: 2

Situation:
  - Your historical stronghold (35% market share last year)
  - New Tier1 competitor (ABC Roofing) entered 90 days ago
  - ABC captured 8 permits (18% share) in your territory
  - Your share dropped to 28%

Recommendation:
  Action: "Defensive retention campaign"
  Rationale: "Protect existing market position against Tier1 threat"
  Expected Outcome: "Maintain 30%+ share, prevent further erosion"

Tactics:
  - Re-engage past customers (referral incentives)
  - Increase response speed (target <7 days from lead)
  - Match ABC's pricing on mid-tier jobs
  - Emphasize local reputation in messaging
  
Resources:
  - CRM outreach: 500 past customers
  - Sales team: +1 rep dedicated to ZIP 75230
  
Timeline: 90 days
```

#### Playbook 3: Avoid Saturated
```yaml
Geography: ZIP 75214 (Lakewood)
Opportunity: Avoid_Saturated
Priority: 5 (Lowest)

Situation:
  - 87 permits filed in 90 days (expected: 45)
  - 12 active competitors
  - Avg ticket size: $9,200 (below your target)
  - Low SII (avg 52) - minimal storm damage

Recommendation:
  Action: "Pull back and reallocate"
  Rationale: "Over-served market, low margins, high competition"
  Expected Outcome: "Redeploy resources to higher-ROI territories"

Tactics:
  - Reduce canvassing to zero
  - Pause paid ads in this ZIP
  - Only respond to inbound leads
  - Reallocate team to ZIP 75201 (Playbook 1)
  
Resources:
  - Freed capacity: 1 canvassing team
  - Saved ad spend: $1,500/month
  
Timeline: Immediate
```

### Reaction Time Scorecard

**Per-Storm Competitor Analysis**:

```
Storm Event: 2024-03-15 Hail (Dallas County)
Magnitude: 1.75" hail | Affected Properties: 3,421 | Avg SII: 76
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Contractor Performance (First 30 Days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rank | Contractor        | First Permit | Permits | Reaction | Grade
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1    | ABC Roofing       | Day 3        | 47      | Fast     | A+
2    | Your Company      | Day 5        | 38      | Fast     | A
3    | XYZ Contractors   | Day 8        | 31      | Fast     | A-
4    | Rapid Roof        | Day 12       | 24      | Medium   | B+
5    | Elite Exteriors   | Day 18       | 19      | Medium   | B
6    | Budget Roofs      | Day 27       | 12      | Slow     | C
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Insights:
⚠️  ABC Roofing beat you by 2 days and captured 23% more permits
✓  You outpaced 4 of 5 major competitors
💡 Opportunity: Improve storm monitoring to deploy within 48 hours
```

---

## Implementation Roadmap

### Phase 1: Data Ingestion (Week 1-2)
- [ ] Integrate Dallas OpenData permits API
- [ ] Set up Shovels.ai API (if budget allows)
- [ ] Build contractor normalization logic
- [ ] Create `competitor_contractors` and `competitor_activity` tables

### Phase 2: Metrics Engine (Week 3-4)
- [ ] Implement market share calculations
- [ ] Build reaction speed analyzer
- [ ] Create positioning/deal size analytics
- [ ] Generate `competitor_metrics` table

### Phase 3: White-Space Detection (Week 5-6)
- [ ] Join SII/MOE with permit data
- [ ] Calculate supply-demand gaps
- [ ] Build opportunity classifier
- [ ] Populate `white_space_opportunities` table

### Phase 4: UI Integration (Week 7-8)
- [ ] Add Competitor Heatmap pane to Streamlit
- [ ] Build Playbook generator
- [ ] Create Reaction Time scorecard
- [ ] Add filters and drill-downs

### Phase 5: Automation (Week 9-10)
- [ ] Schedule daily permit ingestion
- [ ] Auto-generate playbooks after storms
- [ ] Email alerts for competitor moves
- [ ] Weekly market share reports

---

## Success Metrics

**Platform Adoption**:
- Daily active users viewing competitor intel
- Playbooks acted upon / total generated

**Business Impact**:
- Market share growth in targeted geographies
- Reaction time improvement (days to first permit)
- Win rate in head-to-head competitive scenarios

**Intelligence Quality**:
- Accuracy of white-space predictions (actual permits vs. expected)
- Playbook success rate (achieved outcome vs. expected)

---

## References

Content was rephrased for compliance with licensing restrictions.

[1] Permit Intelligence for Contractors - https://blog.hbweekly.com/permit-intelligence-the-contractors-edge-for-2026/
[2] Building Permit Data Resource - https://www.thewarrengroup.com/blog/building-permit-data-a-key-resource-for-construction-companies-contractors-and-real-estate-developers/
[3] Shovels.ai API - https://www.shovels.ai/api
[4] Texas Roofing Permits Analysis - https://www.shovels.ai/blog/analyzing-texas-roofing-permits-by-income-bracket/
[5] Convex Roofing Solutions - https://www.convex.com/solutions-roofing-industry
[6] 5 Ways to Use Permit Data - https://blog.hbweekly.com/5-ways-contractors-can-use-building-permit-data/
