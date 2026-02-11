# StormOps Behavioral Lake v1.0

## Overview
Stack behavioral layers on top of physics and enrichment: **who they are, how they move, how they spend, and how they respond under stress**. This enables context-aware decision-making: "For this type of person, in this neighborhood, in this storm and macro context, the best play now is X."

**Core Insight**: Physics predicts damage → Demographics predict capacity → Psychographics predict messaging → Mobility predicts timing → Financial stress predicts urgency → Attribution predicts what works.

---

## Behavioral Layers

### 1. Psychographic Segmentation
**Goal**: Derive values, attitudes, risk tolerance, messaging preferences

**Personas**:
- **Proof-Seeking Engineer**: Data-driven, wants specs and warranties
- **Anxious Family Protector**: Safety-focused, emotional appeals work
- **Deal-Hunter**: Price-sensitive, responds to discounts
- **Status-Conscious**: Brand/reputation matters, premium positioning
- **Procrastinator**: Needs urgency nudges, deadline-driven

**Data Sources**:
- Census/ACS: Income, education, home value, tenure
- Behavioral events: Which scripts/channels they respond to
- Permit history: DIY vs. professional preference
- Frameworks: https://www.qualtrics.com/articles/strategy-research/psychographic-segmentation/

### 2. Mobility & Neighborhood Behavior
**Goal**: Optimize timing and route ordering by presence likelihood

**Patterns**:
- Home presence curves (hourly): When are people home?
- Commute patterns: Morning/evening rush
- Weekend vs. weekday differences
- Neighborhood flow: Tight-knit vs. isolated blocks

**Data Sources**:
- **WorldMove**: Synthetic mobility generator (https://arxiv.org/html/2504.10506v2)
- **Mobility Explorer**: City feeds → behavior patterns (https://github.com/mepa1363/mobility-explorer)
- Census commute data: Journey-to-work statistics

### 3. Financial & Macro-Risk Signals
**Goal**: Sense when neighborhoods are under financial stress

**Indicators**:
- Credit card delinquency rates (county/ZIP)
- Mortgage delinquency trends
- Consumer credit utilization
- Unemployment rate changes

**Data Sources**:
- **CFPB Consumer Credit Trends**: https://www.consumerfinance.gov/data-research/consumer-credit-trends/
- **Fed Large Bank Data**: https://www.philadelphiafed.org/surveys-and-data/large-bank-credit-card-and-mortgage-data
- BLS unemployment statistics

**Use Cases**:
- Adjust offers (more financing options in high-stress areas)
- Adjust script tone (empathetic vs. transactional)
- Tighten risk filters for aggressive canvassing

### 4. Multi-Touch Response & Learning
**Goal**: Understand which sequences and contexts move people

**Methods**:
- **Hybrid Attribution**: Absorbing Markov + Shapley (https://amplitude.com/blog/attribution-model-frameworks)
- **Contextual Bandits**: Learn optimal action per context (https://en.wikipedia.org/wiki/Multi-armed_bandit)
- **Reinforcement Learning**: Continuous optimization of touch sequences

---

## Core Tables

### 1. psychographic_profiles

```sql
CREATE TABLE psychographic_profiles (
    profile_id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(property_id),
    customer_id UUID,
    
    -- Derived persona
    primary_persona TEXT,               -- Proof_Seeker, Family_Protector, Deal_Hunter, Status_Conscious, Procrastinator
    persona_confidence DECIMAL(3, 2),   -- 0-1
    
    -- Psychographic dimensions (0-100 scores)
    risk_tolerance DECIMAL(5, 2),       -- Low risk averse → High risk tolerant
    price_sensitivity DECIMAL(5, 2),    -- Low (premium) → High (budget)
    urgency_baseline DECIMAL(5, 2),     -- Procrastinator → Immediate action
    social_proof_weight DECIMAL(5, 2),  -- Independent → Highly influenced by neighbors
    analytical_vs_emotional DECIMAL(5, 2),  -- Emotional appeals → Data-driven
    
    -- Messaging preferences
    preferred_channel TEXT,             -- email, sms, phone, door, mail
    preferred_tone TEXT,                -- professional, friendly, urgent, empathetic
    preferred_content_type TEXT,        -- data_heavy, visual, testimonial, offer_focused
    
    -- Decision-making
    decision_speed_days INTEGER,        -- Typical days from awareness to decision
    influencer_count INTEGER,           -- Estimated decision-makers in household
    financing_preference TEXT,          -- cash, payment_plan, insurance_claim
    
    -- Derived from
    census_features JSONB,              -- Income, education, home value, tenure
    behavioral_features JSONB,          -- Response rates by channel, time-to-convert
    permit_features JSONB,              -- DIY history, contractor preferences
    
    -- Model metadata
    model_version TEXT,
    calculated_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_property (property_id),
    INDEX idx_persona (primary_persona),
    INDEX idx_channel (preferred_channel)
);
```

### 2. mobility_patterns

```sql
CREATE TABLE mobility_patterns (
    pattern_id UUID PRIMARY KEY,
    
    -- Geography
    geography_type TEXT,                -- Property, Block, Tract
    geography_id TEXT,
    geometry GEOMETRY(POLYGON, 4326),
    
    -- Home presence likelihood (hourly, 0-1)
    presence_weekday_0h DECIMAL(3, 2),  -- Midnight
    presence_weekday_6h DECIMAL(3, 2),  -- 6 AM
    presence_weekday_9h DECIMAL(3, 2),  -- 9 AM
    presence_weekday_12h DECIMAL(3, 2), -- Noon
    presence_weekday_15h DECIMAL(3, 2), -- 3 PM
    presence_weekday_18h DECIMAL(3, 2), -- 6 PM (peak)
    presence_weekday_21h DECIMAL(3, 2), -- 9 PM
    
    presence_weekend_9h DECIMAL(3, 2),
    presence_weekend_12h DECIMAL(3, 2),
    presence_weekend_15h DECIMAL(3, 2),
    presence_weekend_18h DECIMAL(3, 2),
    
    -- Optimal contact windows
    best_door_knock_window TEXT,       -- "Weekday 18:00-20:00"
    best_phone_window TEXT,             -- "Weekend 10:00-12:00"
    
    -- Neighborhood characteristics
    commute_pattern TEXT,               -- Car_Dominant, Transit, Mixed, Remote_Work
    avg_commute_minutes INTEGER,
    social_connectivity_score DECIMAL(3, 2),  -- 0-1, tight-knit vs isolated
    foot_traffic_level TEXT,            -- Low, Medium, High
    
    -- Data source
    data_source TEXT,                   -- WorldMove, Census, Observed
    model_version TEXT,
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_geography (geography_type, geography_id),
    INDEX idx_geom USING GIST (geometry)
);
```

### 3. financial_stress_indicators

```sql
CREATE TABLE financial_stress_indicators (
    indicator_id UUID PRIMARY KEY,
    
    -- Geography
    geography_type TEXT,                -- ZIP, County, Tract
    geography_id TEXT,
    
    -- Time period
    period_start DATE,
    period_end DATE,
    
    -- Credit stress (aggregate, privacy-preserving)
    credit_card_delinquency_rate DECIMAL(5, 2),  -- % 30+ days past due
    mortgage_delinquency_rate DECIMAL(5, 2),
    avg_credit_utilization DECIMAL(5, 2),        -- % of available credit used
    
    -- Economic indicators
    unemployment_rate DECIMAL(5, 2),
    median_debt_to_income DECIMAL(5, 2),
    foreclosure_rate DECIMAL(5, 2),
    
    -- Derived stress score
    financial_stress_score DECIMAL(5, 2),        -- 0-100 (0=healthy, 100=severe stress)
    stress_tier TEXT,                            -- Low, Medium, High, Severe
    
    -- Trend
    stress_change_vs_prior_period DECIMAL(6, 2), -- % change
    trend_direction TEXT,                        -- Improving, Stable, Worsening
    
    -- Data sources
    data_sources JSONB,                          -- ["CFPB", "Fed", "BLS"]
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_geography (geography_type, geography_id),
    INDEX idx_period (period_start, period_end),
    INDEX idx_stress (stress_tier)
);
```

### 4. contextual_actions

```sql
CREATE TABLE contextual_actions (
    action_id UUID PRIMARY KEY,
    
    -- Context snapshot
    property_id UUID REFERENCES properties(property_id),
    customer_id UUID,
    timestamp TIMESTAMP,
    
    -- Physical context
    sii_score DECIMAL(5, 2),
    days_since_storm INTEGER,
    roof_age_years INTEGER,
    
    -- Psychographic context
    persona TEXT,
    risk_tolerance DECIMAL(5, 2),
    price_sensitivity DECIMAL(5, 2),
    urgency_baseline DECIMAL(5, 2),
    
    -- Mobility context
    home_presence_likelihood DECIMAL(3, 2),      -- At time of action
    optimal_contact_window BOOLEAN,
    
    -- Financial context
    tract_stress_score DECIMAL(5, 2),
    stress_tier TEXT,
    
    -- Behavioral history
    prior_touchpoints INTEGER,
    last_contact_days_ago INTEGER,
    response_rate_to_date DECIMAL(3, 2),
    
    -- Action taken
    action_type TEXT,                            -- email, sms, phone, door, offer
    channel TEXT,
    message_variant TEXT,                        -- analytical, emotional, urgency, deal
    offer_type TEXT,                             -- standard, financing, discount, premium
    
    -- Outcome
    response BOOLEAN,
    response_time_hours INTEGER,
    conversion BOOLEAN,
    conversion_value_usd INTEGER,
    
    -- Attribution
    shapley_value DECIMAL(5, 4),
    markov_removal_effect DECIMAL(5, 4),
    
    -- Bandit learning
    expected_reward DECIMAL(5, 4),               -- Pre-action prediction
    actual_reward DECIMAL(5, 4),                 -- Post-action result
    regret DECIMAL(5, 4),                        -- actual - expected
    
    -- Model metadata
    model_version TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_property (property_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_persona (persona),
    INDEX idx_action_type (action_type),
    INDEX idx_conversion (conversion)
);
```

---

## Integrated Property View

```sql
CREATE VIEW properties_behavioral_context AS
SELECT 
    p.property_id,
    p.address,
    p.census_tract_geoid,
    
    -- Physical layer
    pe.sii_score,
    pe.moe_usd,
    r.roof_age_years,
    r.roof_condition,
    
    -- Structural layer
    p.year_built,
    ct.median_household_income,
    ct.median_home_value,
    
    -- Psychographic layer
    pp.primary_persona,
    pp.persona_confidence,
    pp.risk_tolerance,
    pp.price_sensitivity,
    pp.urgency_baseline,
    pp.preferred_channel,
    pp.preferred_tone,
    pp.decision_speed_days,
    
    -- Mobility layer
    mp.best_door_knock_window,
    mp.best_phone_window,
    mp.social_connectivity_score,
    mp.presence_weekday_18h AS evening_presence_likelihood,
    
    -- Financial context layer
    fsi.financial_stress_score,
    fsi.stress_tier,
    fsi.trend_direction,
    
    -- Behavioral history
    COUNT(ca.action_id) AS total_touchpoints,
    MAX(ca.timestamp) AS last_contact_date,
    AVG(CASE WHEN ca.response THEN 1.0 ELSE 0.0 END) AS response_rate,
    SUM(CASE WHEN ca.conversion THEN 1 ELSE 0 END) AS conversions,
    SUM(ca.conversion_value_usd) AS lifetime_value,
    
    -- Governance
    pgov.has_sms_consent,
    pgov.has_phone_consent,
    pgov.next_eligible_contact,
    pgov.in_exclusion_zone

FROM properties p
LEFT JOIN property_exposure pe ON p.property_id = pe.property_id
LEFT JOIN roofs r ON p.property_id = r.property_id
LEFT JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
LEFT JOIN psychographic_profiles pp ON p.property_id = pp.property_id
LEFT JOIN mobility_patterns mp ON p.property_id = mp.geography_id AND mp.geography_type = 'Property'
LEFT JOIN financial_stress_indicators fsi ON p.census_tract_geoid = fsi.geography_id AND fsi.geography_type = 'Tract'
LEFT JOIN properties_with_governance pgov ON p.property_id = pgov.property_id
LEFT JOIN contextual_actions ca ON p.property_id = ca.property_id
GROUP BY p.property_id, pe.sii_score, r.roof_age_years, ct.median_household_income, 
         pp.primary_persona, mp.best_door_knock_window, fsi.financial_stress_score, pgov.has_sms_consent;
```

---

## Decision Engine: Context-Aware Action Selection

```python
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

@dataclass
class ActionContext:
    """Complete context for decision-making."""
    # Physical
    sii_score: float
    days_since_storm: int
    roof_age: int
    
    # Psychographic
    persona: str
    risk_tolerance: float
    price_sensitivity: float
    urgency: float
    
    # Mobility
    current_hour: int
    is_weekend: bool
    home_presence_likelihood: float
    
    # Financial
    stress_score: float
    stress_tier: str
    
    # Behavioral
    prior_touchpoints: int
    response_rate: float
    days_since_last_contact: int

@dataclass
class Action:
    """Possible action to take."""
    action_type: str  # email, sms, phone, door
    message_variant: str  # analytical, emotional, urgency, deal
    offer_type: str  # standard, financing, discount, premium
    expected_reward: float  # Predicted conversion probability

class ContextualBandit:
    """Multi-armed bandit for context-aware action selection."""
    
    def __init__(self):
        self.action_space = self._build_action_space()
        self.model = None  # Placeholder for trained model
    
    def _build_action_space(self) -> List[Action]:
        """Define all possible actions."""
        actions = []
        for action_type in ['email', 'sms', 'phone', 'door']:
            for variant in ['analytical', 'emotional', 'urgency', 'deal']:
                for offer in ['standard', 'financing', 'discount']:
                    actions.append(Action(
                        action_type=action_type,
                        message_variant=variant,
                        offer_type=offer,
                        expected_reward=0.0
                    ))
        return actions
    
    def select_action(self, context: ActionContext, epsilon: float = 0.1) -> Action:
        """
        Select best action given context using epsilon-greedy strategy.
        
        Args:
            context: Current situation
            epsilon: Exploration rate (0.1 = 10% random exploration)
        
        Returns:
            Best action to take
        """
        # Exploration: random action
        if np.random.random() < epsilon:
            return np.random.choice(self.action_space)
        
        # Exploitation: best predicted action
        scored_actions = []
        for action in self.action_space:
            reward = self._predict_reward(context, action)
            action.expected_reward = reward
            scored_actions.append((reward, action))
        
        scored_actions.sort(reverse=True, key=lambda x: x[0])
        return scored_actions[0][1]
    
    def _predict_reward(self, context: ActionContext, action: Action) -> float:
        """
        Predict conversion probability for action in context.
        
        Simplified heuristic (replace with trained model in production).
        """
        score = 0.0
        
        # Physical urgency
        if context.sii_score > 80:
            score += 0.3
        if context.days_since_storm < 14:
            score += 0.2
        
        # Persona-action fit
        if context.persona == 'Proof_Seeker' and action.message_variant == 'analytical':
            score += 0.25
        elif context.persona == 'Family_Protector' and action.message_variant == 'emotional':
            score += 0.25
        elif context.persona == 'Deal_Hunter' and action.message_variant == 'deal':
            score += 0.25
        elif context.persona == 'Procrastinator' and action.message_variant == 'urgency':
            score += 0.25
        
        # Financial stress → offer fit
        if context.stress_tier == 'High' and action.offer_type == 'financing':
            score += 0.2
        elif context.stress_tier == 'Low' and action.offer_type == 'standard':
            score += 0.1
        
        # Mobility timing
        if action.action_type == 'door':
            if context.home_presence_likelihood > 0.7:
                score += 0.15
            else:
                score -= 0.3  # Penalize door knock when not home
        
        # Behavioral history
        if context.prior_touchpoints > 5:
            score -= 0.1  # Fatigue penalty
        if context.response_rate > 0.3:
            score += 0.15  # Engaged customer bonus
        
        return max(0.0, min(1.0, score))  # Clamp to [0, 1]

def generate_recommendation(property_context: dict) -> dict:
    """
    Generate context-aware action recommendation.
    
    Args:
        property_context: Dict from properties_behavioral_context view
    
    Returns:
        Recommendation with action, rationale, expected outcome
    """
    context = ActionContext(
        sii_score=property_context['sii_score'],
        days_since_storm=property_context.get('days_since_storm', 999),
        roof_age=property_context['roof_age_years'],
        persona=property_context['primary_persona'],
        risk_tolerance=property_context['risk_tolerance'],
        price_sensitivity=property_context['price_sensitivity'],
        urgency=property_context['urgency_baseline'],
        current_hour=datetime.now().hour,
        is_weekend=datetime.now().weekday() >= 5,
        home_presence_likelihood=property_context['evening_presence_likelihood'],
        stress_score=property_context['financial_stress_score'],
        stress_tier=property_context['stress_tier'],
        prior_touchpoints=property_context['total_touchpoints'],
        response_rate=property_context['response_rate'],
        days_since_last_contact=property_context.get('days_since_last_contact', 999)
    )
    
    bandit = ContextualBandit()
    best_action = bandit.select_action(context, epsilon=0.05)
    
    # Build rationale
    rationale_parts = []
    
    if context.sii_score > 80:
        rationale_parts.append(f"High damage likelihood (SII {context.sii_score})")
    
    if context.persona:
        rationale_parts.append(f"{context.persona} persona → {best_action.message_variant} messaging")
    
    if context.stress_tier in ['High', 'Severe']:
        rationale_parts.append(f"High financial stress → {best_action.offer_type} offer")
    
    if best_action.action_type == 'door' and context.home_presence_likelihood > 0.7:
        rationale_parts.append(f"High presence likelihood ({context.home_presence_likelihood:.0%}) → door knock optimal")
    
    return {
        'action_type': best_action.action_type,
        'message_variant': best_action.message_variant,
        'offer_type': best_action.offer_type,
        'expected_conversion_rate': best_action.expected_reward,
        'rationale': ' | '.join(rationale_parts),
        'timing': context.current_hour if best_action.action_type in ['phone', 'door'] else 'ASAP',
        'priority_score': context.sii_score * best_action.expected_reward
    }
```

---

## Example Query: Optimal Next Actions

```sql
-- Top 100 properties to contact right now with context-aware recommendations
SELECT 
    pbc.property_id,
    pbc.address,
    pbc.sii_score,
    pbc.primary_persona,
    pbc.stress_tier,
    pbc.evening_presence_likelihood,
    pbc.preferred_channel,
    pbc.preferred_tone,
    
    -- Recommended action (simplified heuristic)
    CASE 
        WHEN pbc.primary_persona = 'Proof_Seeker' THEN 'email_analytical_standard'
        WHEN pbc.primary_persona = 'Family_Protector' THEN 'phone_emotional_standard'
        WHEN pbc.primary_persona = 'Deal_Hunter' THEN 'sms_deal_discount'
        WHEN pbc.primary_persona = 'Procrastinator' THEN 'door_urgency_standard'
        ELSE 'email_professional_standard'
    END AS recommended_action,
    
    -- Timing
    CASE 
        WHEN EXTRACT(HOUR FROM NOW()) BETWEEN 18 AND 20 AND pbc.evening_presence_likelihood > 0.7 
        THEN 'Contact NOW (optimal window)'
        ELSE CONCAT('Wait until ', pbc.best_door_knock_window)
    END AS timing_recommendation,
    
    -- Offer adjustment
    CASE 
        WHEN pbc.stress_tier IN ('High', 'Severe') THEN 'Emphasize financing options'
        WHEN pbc.price_sensitivity > 70 THEN 'Lead with discount'
        ELSE 'Standard pricing'
    END AS offer_strategy,
    
    -- Priority score
    (pbc.sii_score * 0.4 + 
     pbc.urgency_baseline * 0.3 + 
     (100 - pbc.total_touchpoints * 5) * 0.2 +
     pbc.response_rate * 100 * 0.1) AS priority_score

FROM properties_behavioral_context pbc
WHERE pbc.sii_score > 60
  AND pbc.has_sms_consent = TRUE
  AND pbc.next_eligible_contact <= NOW()
  AND pbc.in_exclusion_zone = FALSE
ORDER BY priority_score DESC
LIMIT 100;
```

---

## Implementation Roadmap

### Phase 1: Psychographic Segmentation (Week 1-2)
- [ ] Build persona classifier from Census + behavioral data
- [ ] Populate `psychographic_profiles` table
- [ ] Validate personas against historical conversion data

### Phase 2: Mobility Patterns (Week 3-4)
- [ ] Integrate WorldMove or Census commute data
- [ ] Calculate home presence curves
- [ ] Populate `mobility_patterns` table

### Phase 3: Financial Stress (Week 5)
- [ ] Ingest CFPB/Fed credit data
- [ ] Calculate stress scores by geography
- [ ] Populate `financial_stress_indicators` table

### Phase 4: Contextual Bandit (Week 6-8)
- [ ] Build action space and context features
- [ ] Train initial model on historical data
- [ ] Implement epsilon-greedy selection
- [ ] Log actions to `contextual_actions` table

### Phase 5: Integration & Testing (Week 9-10)
- [ ] Create `properties_behavioral_context` view
- [ ] Build recommendation API
- [ ] A/B test bandit vs. rule-based
- [ ] Monitor regret and adjust epsilon

---

## Success Metrics

**Segmentation Quality**:
- Persona classification accuracy (vs. manual labels)
- Within-cluster response rate variance

**Timing Optimization**:
- Door knock success rate by presence likelihood
- Contact-to-response time reduction

**Financial Context**:
- Financing offer acceptance rate in high-stress areas
- Conversion rate lift with stress-adjusted messaging

**Bandit Performance**:
- Cumulative regret vs. random baseline
- Conversion rate lift vs. rule-based system
- Revenue per contact improvement

---

## References

Content was rephrased for compliance with licensing restrictions.

[1] Psychographic Segmentation - https://www.qualtrics.com/articles/strategy-research/psychographic-segmentation/
[2] Adobe Psychographic Guide - https://business.adobe.com/blog/basics/psychographic-segmentation
[3] Census Psychographic Research - https://pmc.ncbi.nlm.nih.gov/articles/PMC9819545/
[4] WorldMove Mobility Generator - https://arxiv.org/html/2504.10506v2
[5] Mobility Explorer - https://github.com/mepa1363/mobility-explorer
[6] CFPB Consumer Credit Trends - https://www.consumerfinance.gov/data-research/consumer-credit-trends/
[7] Fed Large Bank Credit Data - https://www.philadelphiafed.org/surveys-and-data/large-bank-credit-card-and-mortgage-data
[8] Attribution Model Frameworks - https://amplitude.com/blog/attribution-model-frameworks
[9] Multi-Armed Bandit - https://en.wikipedia.org/wiki/Multi-armed_bandit
[10] Simon-Kucher Psychographics - https://www.simon-kucher.com/en/insights/power-psychographic-segmentation
