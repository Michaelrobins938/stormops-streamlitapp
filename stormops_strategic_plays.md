# StormOps Strategic Plays v1.0

## Overview
Transform StormOps from a control plane into a **strategy compiler** by making plays first-class, data-driven objects. Each play explicitly defines targeting logic, channel mix, capacity, financial goals, and which parts of the analytics stack it relies on.

**Core Insight**: Plays aren't ad-hoc campaigns—they're measurable, iterable assets with historical performance data, A/B test results, and auto-adaptation logic.

---

## Play Schema

### Playbook Object (Postgres)

```sql
CREATE TABLE playbooks (
    playbook_id UUID PRIMARY KEY,
    
    -- Identity
    playbook_name TEXT UNIQUE NOT NULL,     -- "Frisco-Alpha", "Loyalty-DFW-HighSES"
    playbook_version TEXT,                  -- "v1.2.0"
    status TEXT,                            -- Draft, Active, Paused, Retired
    
    -- Targeting logic
    targeting_rules JSONB NOT NULL,         -- See targeting schema below
    expected_property_count INTEGER,
    
    -- Channel mix
    channel_strategy JSONB NOT NULL,        -- See channel schema below
    message_variants JSONB,                 -- Persona-specific scripts
    
    -- Capacity & constraints
    max_daily_contacts INTEGER,
    max_concurrent_properties INTEGER,
    team_size_required INTEGER,
    budget_allocated INTEGER,
    
    -- Financial goals
    target_conversion_rate DECIMAL(5, 4),
    target_avg_ticket INTEGER,
    target_roi DECIMAL(5, 2),
    
    -- Stack dependencies
    requires_vector_search BOOLEAN,
    requires_graph_analysis BOOLEAN,
    requires_streaming_triggers BOOLEAN,
    requires_ml_scoring BOOLEAN,
    
    -- Metadata
    created_by TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_status (status),
    INDEX idx_name (playbook_name)
);
```

### Targeting Rules Schema

```json
{
  "physics": {
    "min_sii_score": 70,
    "max_days_since_storm": 30,
    "roof_age_min": 10,
    "roof_age_max": 40
  },
  "geography": {
    "zips": ["75034", "75035"],
    "tracts": null,
    "custom_polygon": null
  },
  "demographics": {
    "ses_tiers": ["High", "Medium"],
    "min_median_income": 80000,
    "homeownership_rate_min": 0.7
  },
  "psychographics": {
    "personas": ["Proof_Seeker", "Family_Protector"],
    "exclude_personas": ["Procrastinator"]
  },
  "behavioral": {
    "prior_touchpoints_max": 3,
    "response_rate_min": 0.2,
    "exclude_recent_converts": true
  },
  "competition": {
    "competitor_pressure_max": 0.6,
    "white_space_score_min": 50
  },
  "similarity": {
    "enabled": true,
    "reference_property_ids": ["prop_123", "prop_456"],
    "similarity_threshold": 0.75,
    "top_k": 500
  }
}
```

### Channel Strategy Schema

```json
{
  "sequence": [
    {
      "step": 1,
      "channel": "email",
      "timing_hours": 0,
      "message_variant": "analytical",
      "offer_type": "standard",
      "success_criteria": "open_rate > 0.3"
    },
    {
      "step": 2,
      "channel": "sms",
      "timing_hours": 48,
      "condition": "if_no_response_to_step_1",
      "message_variant": "urgency",
      "offer_type": "discount"
    },
    {
      "step": 3,
      "channel": "door_knock",
      "timing_hours": 120,
      "condition": "if_response_to_step_2",
      "timing_window": "weekday_18:00-20:00",
      "message_variant": "emotional"
    }
  ],
  "adaptive": {
    "enabled": true,
    "bandit_epsilon": 0.1,
    "reoptimize_after_n_contacts": 100
  }
}
```

---

## Play Execution (Postgres)

```sql
CREATE TABLE playbook_executions (
    execution_id UUID PRIMARY KEY,
    playbook_id UUID REFERENCES playbooks(playbook_id),
    
    -- Trigger
    triggered_by_event_id TEXT REFERENCES storm_events(event_id),
    execution_start TIMESTAMP,
    execution_end TIMESTAMP,
    status TEXT,                            -- Running, Completed, Aborted
    
    -- Targeting results
    properties_targeted INTEGER,
    properties_contacted INTEGER,
    properties_converted INTEGER,
    
    -- Financial results
    total_revenue INTEGER,
    total_cost INTEGER,
    roi DECIMAL(5, 2),
    avg_ticket INTEGER,
    
    -- Performance vs goals
    conversion_rate DECIMAL(5, 4),
    conversion_rate_vs_target DECIMAL(6, 2),  -- % difference
    roi_vs_target DECIMAL(6, 2),
    
    -- Stack usage
    vector_search_queries INTEGER,
    ml_scoring_runs INTEGER,
    streaming_triggers_fired INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_playbook (playbook_id),
    INDEX idx_event (triggered_by_event_id),
    INDEX idx_start (execution_start)
);
```

---

## Example Plays

### Play 1: Frisco-Alpha (Precision Entry)

**Goal**: Enter Frisco market with high-value, low-competition targeting

**Targeting**:
```python
{
    "physics": {"min_sii_score": 75, "max_days_since_storm": 14},
    "geography": {"zips": ["75034", "75035"]},
    "demographics": {"ses_tiers": ["High"], "min_median_income": 100000},
    "psychographics": {"personas": ["Proof_Seeker", "Status_Conscious"]},
    "competition": {"competitor_pressure_max": 0.4, "white_space_score_min": 60},
    "similarity": {
        "enabled": true,
        "reference_property_ids": ["top_50_high_margin_conversions"],
        "similarity_threshold": 0.8,
        "top_k": 300
    }
}
```

**Channel Strategy**:
1. Email (analytical tone) → Day 0
2. SMS (urgency) → Day 3 if no response
3. Door knock (premium positioning) → Day 7 if engaged

**Stack Dependencies**:
- ✅ Vector search (Milvus): Find lookalikes to top converters
- ✅ Graph analysis (Neo4j): Identify low-competition ZIPs
- ✅ ML scoring: SII + uplift + competitor pressure
- ✅ Lakehouse (Iceberg): Historical performance in similar markets

**KPIs**:
- Target conversion rate: 25%
- Target avg ticket: $18,000
- Target ROI: 400%
- Max properties: 300
- Budget: $15,000

**Retrospective Query** (Trino):
```sql
SELECT 
    pe.execution_id,
    pe.conversion_rate,
    pe.avg_ticket,
    pe.roi,
    hist.avg_conversion_rate_similar_plays,
    comp.competitor_response_days,
    uplift.incremental_revenue
FROM iceberg.analytics.playbook_executions pe
JOIN iceberg.analytics.playbook_history hist 
    ON pe.playbook_id = hist.playbook_id
JOIN iceberg.analytics.competitor_activity comp 
    ON pe.triggered_by_event_id = comp.event_id
JOIN iceberg.analytics.uplift_analysis uplift 
    ON pe.execution_id = uplift.execution_id
WHERE pe.playbook_name = 'Frisco-Alpha'
  AND pe.execution_start > CURRENT_DATE - INTERVAL '1' YEAR
ORDER BY pe.execution_start DESC;
```

---

### Play 2: Loyalty-DFW-HighSES (Retention)

**Goal**: Defend high-value territory against Tier1 competitors

**Targeting**:
```python
{
    "physics": {"min_sii_score": 60, "max_days_since_storm": 45},
    "geography": {"zips": ["75230", "75225"]},  # Historical strongholds
    "demographics": {"ses_tiers": ["High"], "min_median_income": 90000},
    "behavioral": {
        "prior_touchpoints_max": 10,
        "response_rate_min": 0.3,
        "past_customers_only": true
    },
    "competition": {"competitor_pressure_max": 0.8},  # High threat
    "similarity": {"enabled": false}
}
```

**Channel Strategy**:
1. Phone call (friendly, referral incentive) → Day 0
2. Direct mail (loyalty discount) → Day 5
3. In-person visit (VIP treatment) → Day 10 if high LTV

**Stack Dependencies**:
- ✅ Streaming triggers (Kafka): Instant alert when competitor files permit in territory
- ✅ Graph analysis (Neo4j): Word-of-mouth diffusion paths
- ✅ ML scoring: Churn risk + LTV
- ❌ Vector search: Not needed (known customers)

**KPIs**:
- Target retention rate: 80%
- Target avg ticket: $16,000
- Target ROI: 350%
- Max properties: 500
- Budget: $25,000

**Real-Time Guardrail** (Flink):
```python
# Alert if competitor moves into territory
def check_competitor_threat(permit_event):
    if (permit_event['zip_code'] in ['75230', '75225'] and
        permit_event['contractor_tier'] == 'Tier1' and
        permit_event['contractor_id'] != YOUR_CONTRACTOR_ID):
        
        # Trigger defensive play
        create_proposal(
            playbook_id='loyalty-dfw-highses',
            priority=1,
            reason=f"Tier1 competitor {permit_event['contractor_name']} entered territory"
        )
```

---

### Play 3: Expansion-Lookalike (Growth)

**Goal**: Scale into new markets using behavioral twins

**Targeting**:
```python
{
    "physics": {"min_sii_score": 70, "max_days_since_storm": 30},
    "geography": {"zips": null},  # Discovered via similarity
    "demographics": {"ses_tiers": ["High", "Medium"]},
    "similarity": {
        "enabled": true,
        "mode": "neighborhood_embedding",
        "reference_tract_ids": ["48113010101", "48113010102"],  # Best tracts
        "similarity_threshold": 0.85,
        "top_k_tracts": 10,
        "properties_per_tract": 50
    }
}
```

**Channel Strategy**:
1. Paid ads (Facebook/Google) → Day 0-7
2. Email (social proof from similar neighborhoods) → Day 3
3. Door knock (yard sign campaign) → Day 10-20

**Stack Dependencies**:
- ✅ Vector search (Milvus): Find neighborhoods with similar embeddings
- ✅ Graph analysis (Neo4j): Predict word-of-mouth diffusion
- ✅ ML scoring: SII + uplift + psychographic segmentation
- ✅ Lakehouse: Historical performance by neighborhood type

**KPIs**:
- Target conversion rate: 18%
- Target avg ticket: $15,000
- Target ROI: 300%
- Max properties: 500
- Budget: $30,000

**Similarity Search** (Milvus):
```python
def find_expansion_targets(reference_tract_ids: List[str]) -> List[str]:
    """Find neighborhoods similar to best-performing tracts."""
    # Get embeddings for reference tracts
    ref_embeddings = []
    for tract_id in reference_tract_ids:
        embedding = get_tract_embedding(tract_id)  # From Milvus
        ref_embeddings.append(embedding)
    
    # Average reference embeddings
    avg_embedding = np.mean(ref_embeddings, axis=0)
    
    # Search for similar tracts
    results = milvus_collection.search(
        data=[avg_embedding.tolist()],
        anns_field="embedding",
        param={"metric_type": "L2", "params": {"nprobe": 10}},
        limit=50,
        output_fields=["tract_geoid", "median_income", "property_count"]
    )
    
    # Filter by criteria
    expansion_tracts = [
        hit.entity.get('tract_geoid')
        for hit in results[0]
        if hit.entity.get('median_income') > 75000
        and 1 / (1 + hit.distance) > 0.85  # Similarity threshold
    ][:10]
    
    return expansion_tracts
```

---

## Closed-Loop Learning

### Nightly Model Retraining (Airflow + MLflow)

```python
# dags/playbook_learning_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator

def retrain_uplift_model():
    """Retrain uplift model on latest playbook execution data."""
    import mlflow
    from pyiceberg.catalog import load_catalog
    
    mlflow.set_experiment("playbook_uplift")
    
    with mlflow.start_run():
        # Load execution history from Iceberg
        catalog = load_catalog("stormops")
        executions_table = catalog.load_table("stormops.analytics.playbook_executions")
        df = executions_table.scan().to_pandas()
        
        # Train uplift model (treatment = playbook, control = no contact)
        X = df[['sii_score', 'ses_tier_encoded', 'persona_encoded', 'competitor_pressure']]
        treatment = df['contacted']
        y = df['converted']
        
        model = train_causal_forest(X, treatment, y)
        
        # Log model
        mlflow.sklearn.log_model(model, "uplift_model")
        
        # Score all properties and write to Postgres
        all_properties = load_all_properties()
        all_properties['uplift_score'] = model.predict(all_properties[X.columns])
        write_to_postgres(all_properties[['property_id', 'uplift_score']])

with DAG('playbook_learning', schedule_interval='@daily') as dag:
    retrain_uplift = PythonOperator(
        task_id='retrain_uplift',
        python_callable=retrain_uplift_model
    )
```

### Live Guardrails (Flink)

```python
# flink_jobs/playbook_guardrails.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

def compute_guardrail_signals():
    """Compute real-time guardrail metrics."""
    env = StreamExecutionEnvironment.get_execution_environment()
    t_env = StreamTableEnvironment.create(env)
    
    # Source: behavior_events stream
    t_env.execute_sql("""
        CREATE TABLE behavior_events (
            property_id STRING,
            customer_id STRING,
            event_type STRING,
            event_timestamp TIMESTAMP(3),
            complaint BOOLEAN,
            WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
        ) WITH ('connector' = 'kafka', 'topic' = 'behavior_events')
    """)
    
    # Sink: guardrail_signals table
    t_env.execute_sql("""
        CREATE TABLE guardrail_signals (
            property_id STRING,
            contact_frequency_7d INT,
            complaint_count_30d INT,
            last_contact_hours_ago DOUBLE,
            throttle_flag BOOLEAN,
            escalate_flag BOOLEAN,
            PRIMARY KEY (property_id) NOT ENFORCED
        ) WITH ('connector' = 'jdbc', 'table-name' = 'guardrail_signals')
    """)
    
    # Compute guardrails
    t_env.execute_sql("""
        INSERT INTO guardrail_signals
        SELECT 
            property_id,
            COUNT(*) FILTER (WHERE event_timestamp > CURRENT_TIMESTAMP - INTERVAL '7' DAY) as contact_frequency_7d,
            SUM(CAST(complaint AS INT)) FILTER (WHERE event_timestamp > CURRENT_TIMESTAMP - INTERVAL '30' DAY) as complaint_count_30d,
            TIMESTAMPDIFF(HOUR, MAX(event_timestamp), CURRENT_TIMESTAMP) as last_contact_hours_ago,
            CASE WHEN COUNT(*) FILTER (WHERE event_timestamp > CURRENT_TIMESTAMP - INTERVAL '7' DAY) > 5 THEN TRUE ELSE FALSE END as throttle_flag,
            CASE WHEN SUM(CAST(complaint AS INT)) > 2 THEN TRUE ELSE FALSE END as escalate_flag
        FROM behavior_events
        GROUP BY property_id
    """)
```

### Proposal Engine with Guardrails

```python
# proposal_engine.py
def generate_playbook_proposals(event_id: str):
    """Generate proposals for all active playbooks, respecting guardrails."""
    active_playbooks = get_active_playbooks()
    
    for playbook in active_playbooks:
        # Get targeting results
        targeted_properties = execute_targeting_query(playbook.targeting_rules)
        
        # Apply guardrails
        safe_properties = []
        for prop in targeted_properties:
            guardrails = get_guardrail_signals(prop['property_id'])
            
            if guardrails['throttle_flag']:
                log_throttle(prop['property_id'], "Contact frequency exceeded")
                continue
            
            if guardrails['escalate_flag']:
                log_escalation(prop['property_id'], "Complaint threshold exceeded")
                notify_human(prop['property_id'], playbook.playbook_name)
                continue
            
            safe_properties.append(prop)
        
        # Create execution
        if len(safe_properties) >= playbook.min_property_count:
            create_playbook_execution(
                playbook_id=playbook.playbook_id,
                event_id=event_id,
                properties=safe_properties
            )
```

---

## Post-Storm Retrospective (Strategy Lab)

### Playbook Performance Analysis (Spark + Trino)

```sql
-- Compare all playbook executions for recent storm
WITH storm_executions AS (
    SELECT 
        pb.playbook_name,
        pe.execution_id,
        pe.properties_targeted,
        pe.properties_converted,
        pe.conversion_rate,
        pe.avg_ticket,
        pe.roi,
        pe.total_revenue,
        pe.total_cost
    FROM iceberg.analytics.playbook_executions pe
    JOIN postgres.public.playbooks pb ON pe.playbook_id = pb.playbook_id
    WHERE pe.triggered_by_event_id = 'event_2024_03_15'
),
control_group AS (
    SELECT 
        AVG(conversion_rate) as baseline_conversion,
        AVG(avg_ticket) as baseline_ticket
    FROM iceberg.analytics.property_outcomes
    WHERE event_id = 'event_2024_03_15'
      AND contacted = FALSE
)
SELECT 
    se.playbook_name,
    se.properties_targeted,
    se.conversion_rate,
    se.conversion_rate - cg.baseline_conversion as uplift,
    se.avg_ticket,
    se.roi,
    se.total_revenue,
    RANK() OVER (ORDER BY se.roi DESC) as roi_rank
FROM storm_executions se
CROSS JOIN control_group cg
ORDER BY se.roi DESC;
```

### Sensitivity Analysis

```python
# analysis/playbook_sensitivity.py
def analyze_playbook_sensitivity(playbook_id: str):
    """Analyze how playbook performance varies by context."""
    import duckdb
    
    con = duckdb.connect()
    
    # Load execution history
    df = con.execute(f"""
        SELECT 
            pe.*,
            ct.median_household_income,
            ct.homeownership_rate,
            tm.contractor_density,
            se.magnitude as hail_size
        FROM iceberg_scan('s3://stormops-lakehouse/analytics/playbook_executions') pe
        JOIN iceberg_scan('s3://stormops-lakehouse/enriched/census_tracts') ct 
            ON pe.primary_tract_geoid = ct.tract_geoid
        JOIN iceberg_scan('s3://stormops-lakehouse/enriched/tract_metrics') tm 
            ON pe.primary_tract_geoid = tm.tract_geoid
        JOIN iceberg_scan('s3://stormops-lakehouse/raw/storm_events') se 
            ON pe.triggered_by_event_id = se.event_id
        WHERE pe.playbook_id = '{playbook_id}'
    """).df()
    
    # Analyze sensitivity
    results = {
        'by_income': df.groupby(pd.cut(df['median_household_income'], bins=5))['roi'].mean(),
        'by_competition': df.groupby(pd.cut(df['contractor_density'], bins=3))['roi'].mean(),
        'by_hail_size': df.groupby(pd.cut(df['hail_size'], bins=4))['roi'].mean(),
        'by_timing': df.groupby(pd.cut(df['days_since_storm'], bins=[0, 7, 14, 30, 90]))['roi'].mean()
    }
    
    return results
```

---

## Stack Integration Summary

| Play Component | Stack Layer | Purpose |
|----------------|-------------|---------|
| Targeting rules | Postgres + Trino | Query operational + historical data |
| Similarity search | Milvus | Find lookalike properties/neighborhoods |
| Competition analysis | Neo4j | Identify white space, predict diffusion |
| Scoring | MLflow models | SII, uplift, churn, psychographics |
| Execution history | Iceberg | Long-term storage, retrospectives |
| Real-time triggers | Kafka + Flink | Instant reactions, guardrails |
| Learning | Spark + Airflow | Nightly retraining, auto-adaptation |
| Retrospectives | Trino + DuckDB | Cross-play analysis, sensitivity |

---

## Next Steps

1. **Implement playbook CRUD** in Streamlit control plane
2. **Build targeting query compiler** (JSON rules → SQL)
3. **Create first 3 plays**: Frisco-Alpha, Loyalty-DFW, Expansion-Lookalike
4. **Set up Airflow DAG** for nightly playbook learning
5. **Deploy Flink job** for live guardrails
6. **Run first retrospective** after next storm event

---

## References

Content was rephrased for compliance with licensing restrictions.

[1] Commercial Roofing Leads - https://www.servicetitan.com/blog/commercial-roofing-leads
[2] Building Modern Data Lake - https://openmetal.io/resources/blog/building-a-modern-data-lake-using-open-source-tools/
[3] Vector DB for Behavior Analysis - https://www.meegle.com/en_us/topics/vector-databases/vector-database-for-user-behavior-analysis
[4] Dremio Data Lakehouse - https://www.dremio.com/blog/open-source-and-the-data-lakehouse-apache-arrow-apache-iceberg-nessie-and-dremio/
[5] Data Lakehouse Tools - https://azumo.com/artificial-intelligence/ai-insights/data-lakehouse-tools
