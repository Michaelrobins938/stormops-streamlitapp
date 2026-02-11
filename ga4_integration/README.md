# GA4 → StormOps Integration v1.0

## Overview
Wire Google Analytics 4 directly into StormOps so "marketing" becomes another sensor feeding your physics → behavior engine. Track which campaigns/pages produce actual jobs, not just form fills.

**Flow**: GA4 → BigQuery → Iceberg/Trino → StormOps attribution → Google Ads optimization

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  GA4 (Website/Landing Pages)                                     │
│  - Page views, form submits, estimate tool usage                │
│  - Tagged with: parcel_id, event_id, playbook_id                │
└────────────────┬─────────────────────────────────────────────────┘
                 │ Daily + Streaming Export
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  BigQuery (GCP)                                                  │
│  - events_YYYYMMDD tables                                        │
│  - Raw GA4 events with parameters                                │
└────────────────┬─────────────────────────────────────────────────┘
                 │ ETL (Hourly)
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  Iceberg (StormOps Lakehouse)                                    │
│  - web_behavior_events                                           │
│  - Joined with properties, leads, jobs                           │
└────────────────┬─────────────────────────────────────────────────┘
                 │ Attribution Analysis
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  Hybrid Attribution Engine                                       │
│  - Markov + Shapley across GA4 + CRM + StormOps touches         │
│  - Channel values: Google Ads, LSA, SEO, SMS, Door, Call        │
└────────────────┬─────────────────────────────────────────────────┘
                 │ Offline Conversions
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  Google Ads API                                                  │
│  - Upload real job conversions                                   │
│  - Optimize bids to SII/ROI, not form fills                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Step 1: GA4 → BigQuery Export

### Enable BigQuery Export

1. **In GA4 Admin**:
   - Go to Admin → Property → BigQuery Links
   - Click "Link" and select your GCP project
   - Choose export options:
     - ✅ Daily export (events_YYYYMMDD)
     - ✅ Streaming export (events_intraday_YYYYMMDD) - optional
   - Select all events or specific events

2. **Result**: Raw event tables in BigQuery
   ```
   project.analytics_PROPERTY_ID.events_20260207
   project.analytics_PROPERTY_ID.events_intraday_20260207
   ```

### GA4 Event Schema

```sql
-- BigQuery table structure
SELECT
    event_date,              -- YYYYMMDD
    event_timestamp,         -- Microseconds since epoch
    event_name,              -- 'page_view', 'lead_form_submit', etc.
    user_pseudo_id,          -- GA4 client ID
    user_id,                 -- Your custom user ID
    
    -- Event parameters (nested)
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') as page_url,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'parcel_id') as parcel_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'event_id') as storm_event_id,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'playbook_id') as playbook_id,
    
    -- Traffic source
    traffic_source.source,
    traffic_source.medium,
    traffic_source.name as campaign,
    
    -- Device
    device.category,
    device.operating_system,
    
    -- Geo
    geo.city,
    geo.region,
    geo.country
    
FROM `project.analytics_PROPERTY_ID.events_*`
WHERE _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', CURRENT_DATE())
```

---

## Step 2: Tag GA4 Events with StormOps Keys

### Add Custom Parameters to GA4

**On your website (gtag.js)**:
```html
<script>
// Get StormOps context from URL params or hidden fields
const urlParams = new URLSearchParams(window.location.search);
const parcelId = urlParams.get('parcel_id') || document.getElementById('parcel_id')?.value;
const eventId = urlParams.get('event_id');
const playbook = urlParams.get('playbook');

// Send page view with StormOps context
gtag('event', 'page_view', {
  'parcel_id': parcelId,
  'event_id': eventId,
  'playbook_id': playbook,
  'sii_score': urlParams.get('sii_score')
});

// Track lead form submission
document.getElementById('lead-form').addEventListener('submit', function(e) {
  gtag('event', 'lead_form_submit', {
    'parcel_id': parcelId,
    'event_id': eventId,
    'playbook_id': playbook,
    'form_type': 'estimate_request'
  });
});

// Track estimate tool usage
document.getElementById('estimate-tool').addEventListener('click', function() {
  gtag('event', 'estimate_tool_used', {
    'parcel_id': parcelId,
    'event_id': eventId,
    'tool_type': 'roof_calculator'
  });
});
</script>
```

### Define GA4 Conversions

In GA4 Admin → Events → Mark as conversion:
- `lead_form_submit`
- `estimate_tool_used`
- `quote_started`
- `call_click`

---

## Step 3: ETL BigQuery → Iceberg

### Airflow DAG

**dags/ga4_to_iceberg_dag.py**:
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from google.cloud import bigquery
from pyiceberg.catalog import load_catalog
import pandas as pd
from datetime import datetime, timedelta

def extract_ga4_events(execution_date):
    """Extract GA4 events from BigQuery."""
    client = bigquery.Client(project='your-gcp-project')
    
    query = f"""
    SELECT
        event_date,
        TIMESTAMP_MICROS(event_timestamp) as event_timestamp,
        event_name,
        user_pseudo_id as ga_client_id,
        user_id as customer_id,
        
        -- Extract custom parameters
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'parcel_id') as parcel_id,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'event_id') as storm_event_id,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'playbook_id') as playbook_id,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'sii_score') as sii_score,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') as page_url,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title') as page_title,
        
        -- Traffic source
        traffic_source.source as utm_source,
        traffic_source.medium as utm_medium,
        traffic_source.name as utm_campaign,
        
        -- Device
        device.category as device_category,
        device.operating_system,
        
        -- Geo
        geo.city,
        geo.region as state,
        geo.country
        
    FROM `your-gcp-project.analytics_PROPERTY_ID.events_{execution_date.strftime('%Y%m%d')}`
    WHERE event_name IN (
        'page_view', 'lead_form_submit', 'estimate_tool_used', 
        'quote_started', 'call_click', 'online_estimate_completed'
    )
    """
    
    df = client.query(query).to_dataframe()
    return df

def load_to_iceberg(df: pd.DataFrame):
    """Load GA4 events to Iceberg."""
    catalog = load_catalog("stormops")
    table = catalog.load_table("stormops.enriched.web_behavior_events")
    table.append(df)
    
    print(f"Loaded {len(df)} GA4 events to Iceberg")

with DAG(
    'ga4_to_iceberg',
    default_args={'owner': 'stormops'},
    schedule_interval='0 */4 * * *',  # Every 4 hours
    start_date=datetime(2026, 1, 1),
    catchup=False
) as dag:
    
    extract = PythonOperator(
        task_id='extract_ga4',
        python_callable=extract_ga4_events,
        op_kwargs={'execution_date': '{{ ds }}'}
    )
    
    load = PythonOperator(
        task_id='load_to_iceberg',
        python_callable=load_to_iceberg,
        op_kwargs={'df': '{{ ti.xcom_pull(task_ids="extract_ga4") }}'}
    )
    
    extract >> load
```

### Iceberg Table Schema

```python
from pyiceberg.schema import Schema
from pyiceberg.types import *

web_behavior_events_schema = Schema(
    NestedField(1, "event_date", StringType(), required=True),
    NestedField(2, "event_timestamp", TimestampType(), required=True),
    NestedField(3, "event_name", StringType(), required=True),
    NestedField(4, "ga_client_id", StringType()),
    NestedField(5, "customer_id", StringType()),
    NestedField(6, "parcel_id", StringType()),
    NestedField(7, "property_id", StringType()),
    NestedField(8, "storm_event_id", StringType()),
    NestedField(9, "playbook_id", StringType()),
    NestedField(10, "sii_score", IntegerType()),
    NestedField(11, "page_url", StringType()),
    NestedField(12, "page_title", StringType()),
    NestedField(13, "utm_source", StringType()),
    NestedField(14, "utm_medium", StringType()),
    NestedField(15, "utm_campaign", StringType()),
    NestedField(16, "device_category", StringType()),
    NestedField(17, "city", StringType()),
    NestedField(18, "state", StringType())
)
```

---

## Step 4: Join GA4 with StormOps Outcomes

### Create Unified Customer Journey Table

**Trino Query**:
```sql
CREATE TABLE iceberg.analytics.customer_journeys_unified AS
SELECT 
    COALESCE(cj.customer_id, wbe.customer_id) as customer_id,
    COALESCE(cj.property_id, wbe.property_id) as property_id,
    
    -- Web touchpoints
    wbe.event_timestamp as web_event_timestamp,
    wbe.event_name as web_event_type,
    wbe.utm_source,
    wbe.utm_medium,
    wbe.utm_campaign,
    wbe.page_url,
    
    -- StormOps touchpoints
    be.event_timestamp as stormops_event_timestamp,
    be.event_type as stormops_event_type,
    be.channel as stormops_channel,
    
    -- Outcome
    cj.converted,
    cj.conversion_date,
    cj.job_value_usd,
    
    -- Context
    pe.sii_score,
    pp.primary_persona,
    ct.median_household_income

FROM iceberg.enriched.web_behavior_events wbe
FULL OUTER JOIN postgres.public.behavior_events be 
    ON wbe.customer_id = be.customer_id
    AND ABS(EXTRACT(EPOCH FROM (wbe.event_timestamp - be.event_timestamp))) < 3600
FULL OUTER JOIN postgres.public.customer_journeys cj 
    ON COALESCE(wbe.customer_id, be.customer_id) = cj.customer_id
LEFT JOIN postgres.public.property_exposure pe 
    ON COALESCE(wbe.property_id, be.property_id) = pe.property_id
LEFT JOIN postgres.public.psychographic_profiles pp 
    ON COALESCE(wbe.property_id, be.property_id) = pp.property_id
LEFT JOIN postgres.public.census_tracts ct 
    ON pe.census_tract_geoid = ct.tract_geoid
WHERE wbe.event_timestamp > CURRENT_DATE - INTERVAL '90' DAY
   OR be.event_timestamp > CURRENT_DATE - INTERVAL '90' DAY;
```

### Analysis: Which Campaigns Drive Jobs?

```sql
-- Revenue per click by campaign and SII band
SELECT 
    utm_campaign,
    CASE 
        WHEN sii_score >= 80 THEN 'High SII (80+)'
        WHEN sii_score >= 60 THEN 'Medium SII (60-79)'
        ELSE 'Low SII (<60)'
    END as sii_band,
    COUNT(DISTINCT customer_id) as total_visitors,
    SUM(CASE WHEN converted THEN 1 ELSE 0 END) as conversions,
    SUM(job_value_usd) as total_revenue,
    SUM(job_value_usd) / COUNT(DISTINCT customer_id) as revenue_per_click,
    AVG(CASE WHEN converted THEN job_value_usd END) as avg_job_value
FROM iceberg.analytics.customer_journeys_unified
WHERE utm_campaign IS NOT NULL
GROUP BY utm_campaign, sii_band
ORDER BY revenue_per_click DESC;
```

---

## Step 5: Hybrid Attribution Engine

### Combine GA4 + StormOps Touches

```python
# attribution/hybrid_attribution.py
import pandas as pd
import numpy as np
from itertools import combinations

def calculate_hybrid_attribution(journey_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Markov + Shapley attribution across GA4 and StormOps channels.
    """
    # Build touchpoint sequences
    journeys = []
    for customer_id, group in journey_df.groupby('customer_id'):
        touches = []
        
        # Combine web and StormOps touches
        for _, row in group.sort_values('event_timestamp').iterrows():
            if pd.notna(row['web_event_type']):
                touches.append(f"web_{row['utm_source']}_{row['utm_medium']}")
            if pd.notna(row['stormops_event_type']):
                touches.append(f"stormops_{row['stormops_channel']}")
        
        journeys.append({
            'customer_id': customer_id,
            'touchpoints': touches,
            'converted': group['converted'].iloc[0],
            'value': group['job_value_usd'].iloc[0] if group['converted'].iloc[0] else 0
        })
    
    journeys_df = pd.DataFrame(journeys)
    
    # Markov chain attribution
    markov_values = calculate_markov_attribution(journeys_df)
    
    # Shapley value attribution
    shapley_values = calculate_shapley_attribution(journeys_df)
    
    # Hybrid: average of Markov and Shapley
    hybrid_values = {}
    all_channels = set(markov_values.keys()) | set(shapley_values.keys())
    
    for channel in all_channels:
        hybrid_values[channel] = (
            markov_values.get(channel, 0) * 0.5 +
            shapley_values.get(channel, 0) * 0.5
        )
    
    return pd.DataFrame([
        {'channel': ch, 'markov_value': markov_values.get(ch, 0), 
         'shapley_value': shapley_values.get(ch, 0), 'hybrid_value': val}
        for ch, val in hybrid_values.items()
    ]).sort_values('hybrid_value', ascending=False)

def calculate_markov_attribution(journeys_df: pd.DataFrame) -> dict:
    """Calculate Markov removal effect."""
    # Build transition matrix
    transitions = {}
    conversions_with_channel = {}
    
    for _, journey in journeys_df.iterrows():
        path = ['start'] + journey['touchpoints'] + ['conversion' if journey['converted'] else 'null']
        
        for i in range(len(path) - 1):
            from_state = path[i]
            to_state = path[i + 1]
            
            if from_state not in transitions:
                transitions[from_state] = {}
            transitions[from_state][to_state] = transitions[from_state].get(to_state, 0) + 1
        
        # Track conversions by channel
        for channel in set(journey['touchpoints']):
            if journey['converted']:
                conversions_with_channel[channel] = conversions_with_channel.get(channel, 0) + journey['value']
    
    # Calculate removal effect (simplified)
    removal_effects = {}
    total_conversions = journeys_df[journeys_df['converted']]['value'].sum()
    
    for channel in conversions_with_channel.keys():
        # Conversions without this channel (approximation)
        journeys_without = journeys_df[~journeys_df['touchpoints'].apply(lambda x: channel in x)]
        conversions_without = journeys_without[journeys_without['converted']]['value'].sum()
        
        removal_effect = total_conversions - conversions_without
        removal_effects[channel] = removal_effect
    
    return removal_effects

def calculate_shapley_attribution(journeys_df: pd.DataFrame) -> dict:
    """Calculate Shapley values."""
    shapley_values = {}
    
    for _, journey in journeys_df[journeys_df['converted']].iterrows():
        channels = list(set(journey['touchpoints']))
        n = len(channels)
        value = journey['value']
        
        # Calculate marginal contributions
        for channel in channels:
            marginal_sum = 0
            
            # All subsets not containing channel
            for r in range(n):
                for subset in combinations([c for c in channels if c != channel], r):
                    subset = list(subset)
                    
                    # Marginal contribution
                    weight = (np.math.factorial(r) * np.math.factorial(n - r - 1)) / np.math.factorial(n)
                    marginal = value / n  # Simplified: equal split
                    marginal_sum += weight * marginal
            
            shapley_values[channel] = shapley_values.get(channel, 0) + marginal_sum
    
    return shapley_values
```

---

## Step 6: Upload Offline Conversions to Google Ads

### Google Ads API Integration

```python
# google_ads/offline_conversions.py
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import pandas as pd

def upload_offline_conversions(conversions_df: pd.DataFrame):
    """Upload real job conversions to Google Ads."""
    client = GoogleAdsClient.load_from_storage("google-ads.yaml")
    
    conversion_upload_service = client.get_service("ConversionUploadService")
    customer_id = "YOUR_CUSTOMER_ID"
    
    # Prepare conversions
    click_conversions = []
    
    for _, row in conversions_df.iterrows():
        click_conversion = client.get_type("ClickConversion")
        click_conversion.gclid = row['gclid']  # From GA4 or URL param
        click_conversion.conversion_action = f"customers/{customer_id}/conversionActions/JOB_COMPLETED"
        click_conversion.conversion_date_time = row['conversion_date'].strftime('%Y-%m-%d %H:%M:%S+00:00')
        click_conversion.conversion_value = row['job_value_usd']
        click_conversion.currency_code = "USD"
        
        click_conversions.append(click_conversion)
    
    # Upload
    request = client.get_type("UploadClickConversionsRequest")
    request.customer_id = customer_id
    request.conversions = click_conversions
    request.partial_failure = True
    
    try:
        response = conversion_upload_service.upload_click_conversions(request=request)
        print(f"Uploaded {len(click_conversions)} conversions")
        
        if response.partial_failure_error:
            print(f"Partial failures: {response.partial_failure_error}")
    
    except GoogleAdsException as ex:
        print(f"Request failed: {ex}")

# Run daily
def sync_conversions_to_google_ads():
    """Sync yesterday's conversions to Google Ads."""
    # Get conversions from Postgres
    engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')
    
    conversions = pd.read_sql("""
        SELECT 
            cj.customer_id,
            cj.conversion_date,
            cj.job_value_usd,
            wbe.ga_client_id,
            (SELECT value FROM UNNEST(event_params) WHERE key = 'gclid') as gclid
        FROM customer_journeys cj
        JOIN web_behavior_events wbe ON cj.customer_id = wbe.customer_id
        WHERE cj.conversion_date >= CURRENT_DATE - INTERVAL '1 day'
          AND cj.conversion_date < CURRENT_DATE
          AND wbe.utm_source = 'google'
          AND wbe.utm_medium = 'cpc'
    """, engine)
    
    upload_offline_conversions(conversions)
```

---

## Step 7: Real-Time Intent Triggers

### Stream High-Intent Events to Kafka

```python
# streaming/ga4_to_kafka.py
from google.cloud import pubsub_v1
from kafka import KafkaProducer
import json

def stream_ga4_to_kafka():
    """Stream high-intent GA4 events to Kafka for real-time triggers."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path('your-project', 'ga4-events')
    
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    def callback(message):
        event = json.loads(message.data)
        
        # Filter high-intent events
        if event['event_name'] in ['estimate_tool_used', 'quote_started', 'call_click']:
            # Enrich with StormOps context
            parcel_id = event.get('parcel_id')
            if parcel_id:
                # Send to Kafka
                producer.send('high_intent_events', {
                    'event_name': event['event_name'],
                    'parcel_id': parcel_id,
                    'timestamp': event['event_timestamp'],
                    'ga_client_id': event['user_pseudo_id']
                })
        
        message.ack()
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for GA4 events on {subscription_path}")
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
```

### Flink Job: React to High-Intent

```python
# flink_jobs/high_intent_triggers.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

def process_high_intent_events():
    """Create proposals for high-intent web visitors."""
    env = StreamExecutionEnvironment.get_execution_environment()
    t_env = StreamTableEnvironment.create(env)
    
    # Source: high_intent_events from Kafka
    t_env.execute_sql("""
        CREATE TABLE high_intent_events (
            event_name STRING,
            parcel_id STRING,
            event_timestamp TIMESTAMP(3),
            ga_client_id STRING,
            WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
        ) WITH ('connector' = 'kafka', 'topic' = 'high_intent_events')
    """)
    
    # Sink: proposals table
    t_env.execute_sql("""
        CREATE TABLE proposals (
            proposal_id STRING,
            property_id STRING,
            trigger_type STRING,
            priority INT,
            rationale STRING,
            created_at TIMESTAMP(3),
            PRIMARY KEY (proposal_id) NOT ENFORCED
        ) WITH ('connector' = 'jdbc', 'table-name' = 'proposals')
    """)
    
    # Generate proposals
    t_env.execute_sql("""
        INSERT INTO proposals
        SELECT 
            CONCAT('web_intent_', parcel_id, '_', CAST(event_timestamp AS STRING)) as proposal_id,
            parcel_id as property_id,
            'high_web_intent' as trigger_type,
            1 as priority,
            CONCAT('High intent: ', event_name, ' at ', CAST(event_timestamp AS STRING)) as rationale,
            event_timestamp as created_at
        FROM high_intent_events
        WHERE event_name IN ('estimate_tool_used', 'quote_started')
    """)
```

---

## Summary

### Data Flow
1. GA4 → BigQuery (daily + streaming)
2. BigQuery → Iceberg (every 4 hours)
3. Iceberg + Postgres → Unified customer journeys
4. Attribution engine → Channel values
5. Offline conversions → Google Ads
6. High-intent events → Kafka → Flink → Proposals

### Key Metrics
- Revenue per click by campaign × SII band
- Conversion rate by traffic source × persona
- Attribution values: GA4 channels vs. StormOps channels
- Time from first web touch to job completion

### Next Steps
1. Enable GA4 → BigQuery export
2. Add StormOps parameters to website tracking
3. Run first ETL: BigQuery → Iceberg
4. Create unified journey table (Trino)
5. Calculate hybrid attribution
6. Upload offline conversions to Google Ads
7. Deploy Flink job for real-time intent triggers

---

## References

Content was rephrased for compliance with licensing restrictions.

[1] GA4 for Lead Generation - https://www.demand-iq.com/blog/harnessing-google-analytics-4-for-digital-lead-generation-in-solar-roofing-home-service-businesses
[2] GA4 to BigQuery Export - https://www.phranking.com/en/knowledge/je745y/exporting-ga4-data-to-bigquery-for-advanced-analysis
[3] GA4 BigQuery Integration - https://hevodata.com/learn/how-to-integrate-google-analytics-ga4-to-bigquery/
[4] GA4 Custom Parameters - https://support.google.com/analytics/answer/11053644?hl=en
[5] Google Ads Conversion Tracking - https://findbestlocalcontractors.com/google-ads/google-ads-conversion-tracking-optimization-for-roofers/
[6] Attribution Model Frameworks - https://amplitude.com/blog/attribution-model-frameworks
[7] Why Google Ads Fail Roofers - https://jobnimbusmarketing.com/blog/why-google-ads-fail-roofing-companies/
