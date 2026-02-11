#!/usr/bin/env python3
# Step 4: Enable GA4 Integration

import os
import sys
from google.cloud import bigquery
from pyiceberg.catalog import load_catalog
import pandas as pd

print("🎯 Enabling GA4 Integration")
print("=" * 50)

# Check prerequisites
print("\n📋 Prerequisites Check:")

gcp_project = os.getenv('GCP_PROJECT_ID')
ga4_property = os.getenv('GA4_PROPERTY_ID')

if not gcp_project:
    print("  ❌ GCP_PROJECT_ID not set")
    print("  💡 Set: export GCP_PROJECT_ID=your-project-id")
    sys.exit(1)

if not ga4_property:
    print("  ❌ GA4_PROPERTY_ID not set")
    print("  💡 Set: export GA4_PROPERTY_ID=123456789")
    sys.exit(1)

print(f"  ✅ GCP Project: {gcp_project}")
print(f"  ✅ GA4 Property: {ga4_property}")

# 1. Verify BigQuery Export
print("\n📊 Step 1: Verify BigQuery Export")
print("  Manual steps required:")
print("  1. Go to GA4 Admin → BigQuery Links")
print("  2. Click 'Link' and select your GCP project")
print("  3. Enable: Daily export + Streaming export (optional)")
print("  4. Wait 24h for first export")
print("")
input("  Press Enter when BigQuery export is configured...")

# 2. Test BigQuery Connection
print("\n🔌 Step 2: Testing BigQuery Connection...")
try:
    client = bigquery.Client(project=gcp_project)
    
    # Check if GA4 dataset exists
    dataset_id = f"analytics_{ga4_property}"
    tables = list(client.list_tables(dataset_id))
    
    if not tables:
        print(f"  ⚠️  No tables found in {dataset_id}")
        print(f"  💡 Wait for first daily export (runs at ~3 AM PT)")
        sys.exit(1)
    
    print(f"  ✅ Found {len(tables)} tables in {dataset_id}")
    
    # Test query
    query = f"""
    SELECT 
        event_date,
        COUNT(*) as event_count
    FROM `{gcp_project}.{dataset_id}.events_*`
    WHERE _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', CURRENT_DATE() - 1)
    GROUP BY event_date
    LIMIT 1
    """
    
    result = client.query(query).result()
    for row in result:
        print(f"  ✅ Yesterday's events: {row.event_count:,}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    print(f"  💡 Ensure BigQuery API is enabled")
    print(f"  💡 Authenticate: gcloud auth application-default login")
    sys.exit(1)

# 3. Create Iceberg Table for GA4 Events
print("\n🧊 Step 3: Creating Iceberg Table...")
try:
    catalog = load_catalog("stormops")
    
    from pyiceberg.schema import Schema
    from pyiceberg.types import *
    
    schema = Schema(
        NestedField(1, "event_date", StringType(), required=True),
        NestedField(2, "event_timestamp", TimestampType(), required=True),
        NestedField(3, "event_name", StringType(), required=True),
        NestedField(4, "ga_client_id", StringType()),
        NestedField(5, "customer_id", StringType()),
        NestedField(6, "property_id", StringType()),
        NestedField(7, "storm_event_id", StringType()),
        NestedField(8, "playbook_id", StringType()),
        NestedField(9, "page_url", StringType()),
        NestedField(10, "utm_source", StringType()),
        NestedField(11, "utm_medium", StringType()),
        NestedField(12, "utm_campaign", StringType())
    )
    
    try:
        catalog.create_namespace("stormops.enriched")
    except:
        pass
    
    catalog.create_table("stormops.enriched.web_behavior_events", schema=schema)
    print("  ✅ Iceberg table created: web_behavior_events")
    
except Exception as e:
    print(f"  ⚠️  Table may already exist: {e}")

# 4. Run Initial ETL
print("\n⚙️  Step 4: Running Initial ETL...")
try:
    # Extract yesterday's events
    query = f"""
    SELECT
        event_date,
        TIMESTAMP_MICROS(event_timestamp) as event_timestamp,
        event_name,
        user_pseudo_id as ga_client_id,
        user_id as customer_id,
        
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'property_id') as property_id,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'storm_event_id') as storm_event_id,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'playbook_id') as playbook_id,
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') as page_url,
        
        traffic_source.source as utm_source,
        traffic_source.medium as utm_medium,
        traffic_source.name as utm_campaign
        
    FROM `{gcp_project}.analytics_{ga4_property}.events_*`
    WHERE _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', CURRENT_DATE() - 1)
    LIMIT 10000
    """
    
    df = client.query(query).to_dataframe()
    
    # Load to Iceberg
    table = catalog.load_table("stormops.enriched.web_behavior_events")
    table.append(df)
    
    print(f"  ✅ Loaded {len(df)} GA4 events to Iceberg")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# 5. Setup Airflow DAG
print("\n🔄 Step 5: Setting up Airflow DAG...")

dag_code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from google.cloud import bigquery
from pyiceberg.catalog import load_catalog

def sync_ga4_to_iceberg(execution_date):
    client = bigquery.Client()
    catalog = load_catalog("stormops")
    
    query = f"""
    SELECT * FROM `{GCP_PROJECT}.analytics_{GA4_PROPERTY}.events_{execution_date.strftime('%Y%m%d')}`
    """
    
    df = client.query(query).to_dataframe()
    table = catalog.load_table("stormops.enriched.web_behavior_events")
    table.append(df)

with DAG(
    'ga4_to_iceberg',
    schedule_interval='0 */4 * * *',
    start_date=datetime(2026, 1, 1),
    catchup=False
) as dag:
    
    sync = PythonOperator(
        task_id='sync_ga4',
        python_callable=sync_ga4_to_iceberg
    )
'''

with open('dags/ga4_sync_dag.py', 'w') as f:
    f.write(dag_code)

print("  ✅ Created Airflow DAG: dags/ga4_sync_dag.py")

print("\n" + "=" * 50)
print("✅ GA4 Integration Enabled!")
print("\n📊 Summary:")
print(f"  BigQuery Dataset: analytics_{ga4_property}")
print(f"  Iceberg Table: stormops.enriched.web_behavior_events")
print(f"  Airflow DAG: ga4_to_iceberg (runs every 4h)")
print("\n💡 Next: python deploy_playbooks.py")
