# StormOps Analytics Stack v1.0

## Overview
Production-grade data infrastructure that extends StormOps beyond operational Postgres/PostGIS into heavy-duty analytics, ML, streaming, and similarity search. **Postgres stays the operational source of truth**; the analytics stack handles offline heavy lifting and writes enriched outputs back.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OPERATIONAL LAYER (Real-Time)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL + PostGIS (Source of Truth)                          │  │
│  │  - properties, roofs, storm_events, permits                      │  │
│  │  - sector_features, parcel_impacts, Proposals                    │  │
│  │  - behavior_events, customer_journeys                            │  │
│  └────────────┬─────────────────────────────────────────────────────┘  │
│               │                                                          │
│               ├──► Streamlit Control Plane (localhost:8501)             │
│               ├──► TriggerService (Python)                              │
│               └──► API Layer (FastAPI)                                  │
│                                                                           │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                │ CDC (Debezium)
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        STREAMING LAYER (Seconds-Minutes)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────┐      ┌──────────────────┐                        │
│  │  Kafka / Redpanda│◄─────┤  Weather Alerts  │                        │
│  │  Event Bus       │      │  NOAA Streams    │                        │
│  └────────┬─────────┘      └──────────────────┘                        │
│           │                                                              │
│           ├──► behavior_events stream                                   │
│           ├──► storm_alerts stream                                      │
│           ├──► moe_state_changes stream                                 │
│           └──► crm_updates stream                                       │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Flink / Spark Streaming                                         │  │
│  │  - Rolling features (engagement_7d, permit_velocity_30d)         │  │
│  │  - Anomaly detection (sudden permit spike, competitor move)      │  │
│  │  - Real-time scoring (SII updates, opportunity score refresh)    │  │
│  └────────────┬─────────────────────────────────────────────────────┘  │
│               │                                                          │
│               └──► Write back to Postgres (sector_features updates)     │
│                                                                           │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                │ Batch Sync (Hourly)
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAKEHOUSE LAYER (Batch Analytics)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Apache Iceberg / Delta Lake (S3 / MinIO)                        │  │
│  │                                                                   │  │
│  │  Raw Zone:                                                        │  │
│  │    - raw_noaa_storms/                                            │  │
│  │    - raw_permits/                                                │  │
│  │    - raw_census/                                                 │  │
│  │    - raw_imagery/                                                │  │
│  │                                                                   │  │
│  │  Enriched Zone:                                                   │  │
│  │    - enriched_properties/                                        │  │
│  │    - enriched_behavior_events/                                   │  │
│  │    - competitor_activity/                                        │  │
│  │    - psychographic_profiles/                                     │  │
│  │                                                                   │  │
│  │  Feature Store:                                                   │  │
│  │    - property_features/                                          │  │
│  │    - tract_features/                                             │  │
│  │    - temporal_features/                                          │  │
│  │                                                                   │  │
│  │  Model Outputs:                                                   │  │
│  │    - sii_predictions/                                            │  │
│  │    - uplift_scores/                                              │  │
│  │    - churn_risk/                                                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Query Engines                                                    │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                │  │
│  │  │   Trino    │  │   Dremio   │  │   DuckDB   │                │  │
│  │  │ Federated  │  │ Semantic   │  │  Ad-hoc    │                │  │
│  │  │   SQL      │  │   Layer    │  │  Analysis  │                │  │
│  │  └────────────┘  └────────────┘  └────────────┘                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                │ Feature Vectors
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        VECTOR LAYER (Similarity Search)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Milvus / Qdrant / Weaviate                                      │  │
│  │                                                                   │  │
│  │  Collections:                                                     │  │
│  │    - property_embeddings (SES + SII + behavior fingerprint)      │  │
│  │    - neighborhood_embeddings (tract-level characteristics)       │  │
│  │    - script_embeddings (message variants)                        │  │
│  │    - roof_image_embeddings (CLIP/ResNet features)                │  │
│  │                                                                   │  │
│  │  Use Cases:                                                       │  │
│  │    - "Find 200 properties similar to these 50 high-converters"   │  │
│  │    - "Which neighborhoods behave like our pilot ZIP?"            │  │
│  │    - "Recommend best script variant for this persona"            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────┘
                │
                │ Training Data
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ML LAYER (Model Training & Serving)               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  MLflow (Experiment Tracking & Model Registry)                   │  │
│  │  - sii_model_v1.2.3                                              │  │
│  │  - moe_model_v2.0.1                                              │  │
│  │  - uplift_model_v1.5.0                                           │  │
│  │  - psychographic_classifier_v1.0.0                               │  │
│  │  - attribution_model_v1.1.0                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Kedro / ZenML (ML Pipelines)                                    │  │
│  │                                                                   │  │
│  │  Pipelines:                                                       │  │
│  │    1. data_ingestion                                             │  │
│  │    2. feature_engineering                                        │  │
│  │    3. model_training                                             │  │
│  │    4. model_evaluation                                           │  │
│  │    5. model_deployment                                           │  │
│  │    6. batch_scoring                                              │  │
│  │    7. write_to_postgres                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Spark (Heavy Training & Batch Scoring)                          │  │
│  │  - Multi-year hail + permits + claims joins                      │  │
│  │  - Large-scale feature engineering                               │  │
│  │  - Distributed model training (XGBoost, LightGBM)                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                │ Scored Results
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        GRAPH LAYER (Network Analysis)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Neo4j / TigerGraph                                              │  │
│  │                                                                   │  │
│  │  Graphs:                                                          │  │
│  │    - Contractor Competition Network                              │  │
│  │      Nodes: Contractors, ZIPs, Tracts                            │  │
│  │      Edges: OPERATES_IN, COMPETES_WITH                           │  │
│  │                                                                   │  │
│  │    - Neighborhood Influence Network                              │  │
│  │      Nodes: Properties, Households                               │  │
│  │      Edges: NEIGHBOR, REFERRED_BY, SIMILAR_TO                    │  │
│  │                                                                   │  │
│  │    - Word-of-Mouth Diffusion                                     │  │
│  │      Nodes: Customers, Properties                                │  │
│  │      Edges: INFLUENCED, CONVERTED_AFTER                          │  │
│  │                                                                   │  │
│  │  Queries:                                                         │  │
│  │    - "Which blocks are most central in social network?"          │  │
│  │    - "Where do competitors dominate vs ignore?"                  │  │
│  │    - "Predict diffusion path for yard sign campaign"             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────┘
                │
                │ All Layers Orchestrated By
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Airflow / Prefect                                               │  │
│  │                                                                   │  │
│  │  DAGs:                                                            │  │
│  │    - daily_data_ingestion (NOAA, permits, census)               │  │
│  │    - hourly_feature_refresh (rolling metrics)                    │  │
│  │    - weekly_model_retraining (SII, MOE, uplift)                 │  │
│  │    - nightly_batch_scoring (all properties)                      │  │
│  │    - realtime_trigger_evaluation (every 5 min)                   │  │
│  │    - monthly_competitor_analysis                                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Core Lakehouse + Warehouse

#### Apache Iceberg on S3/MinIO
**Purpose**: Durable, versioned storage for all raw + enriched data

**Setup**:
```yaml
# docker-compose.yml
services:
  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password
    command: server /data --console-address ":9001"
    volumes:
      - ./minio_data:/data

  iceberg-rest:
    image: tabulario/iceberg-rest
    ports:
      - "8181:8181"
    environment:
      AWS_ACCESS_KEY_ID: admin
      AWS_SECRET_ACCESS_KEY: password
      AWS_REGION: us-east-1
      CATALOG_WAREHOUSE: s3://stormops-lakehouse/
      CATALOG_IO__IMPL: org.apache.iceberg.aws.s3.S3FileIO
      CATALOG_S3_ENDPOINT: http://minio:9000
```

**Table Structure**:
```python
# Create Iceberg table
from pyiceberg.catalog import load_catalog

catalog = load_catalog("stormops")

schema = Schema(
    NestedField(1, "property_id", StringType(), required=True),
    NestedField(2, "event_id", StringType()),
    NestedField(3, "sii_score", DoubleType()),
    NestedField(4, "moe_usd", IntegerType()),
    NestedField(5, "timestamp", TimestampType()),
    NestedField(6, "census_tract_geoid", StringType()),
    # ... all enriched fields
)

catalog.create_table(
    "stormops.enriched.property_features",
    schema=schema,
    partition_spec=PartitionSpec(
        PartitionField(source_id=6, field_id=1000, transform=IdentityTransform(), name="tract"),
        PartitionField(source_id=5, field_id=1001, transform=DayTransform(), name="day")
    )
)
```

#### Trino for Federated Queries
**Purpose**: Query across Postgres + Iceberg + S3 in single SQL

**Setup**:
```yaml
# docker-compose.yml
  trino:
    image: trinodb/trino
    ports:
      - "8080:8080"
    volumes:
      - ./trino/catalog:/etc/trino/catalog
```

```properties
# trino/catalog/postgres.properties
connector.name=postgresql
connection-url=jdbc:postgresql://postgres:5432/stormops
connection-user=stormops
connection-password=password

# trino/catalog/iceberg.properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://iceberg-rest:8181
```

**Example Query**:
```sql
-- Join operational Postgres with analytical Iceberg
SELECT 
    p.property_id,
    p.address,
    pe.sii_score AS current_sii,
    hist.avg_sii_30d,
    hist.max_sii_90d,
    comp.competitor_pressure_index
FROM postgres.public.properties p
JOIN postgres.public.property_exposure pe ON p.property_id = pe.property_id
JOIN iceberg.enriched.property_features hist ON p.property_id = hist.property_id
JOIN iceberg.analytics.competitor_metrics comp ON p.census_tract_geoid = comp.tract_geoid
WHERE pe.sii_score > 70
  AND comp.competitor_pressure_index < 0.5
ORDER BY pe.sii_score DESC
LIMIT 100;
```

#### DuckDB for Local Analysis
**Purpose**: Fast ad-hoc queries on Parquet/Iceberg without cluster

```python
import duckdb

# Query Iceberg table directly
con = duckdb.connect()
con.execute("""
    INSTALL iceberg;
    LOAD iceberg;
    
    SELECT 
        census_tract_geoid,
        AVG(sii_score) as avg_sii,
        COUNT(*) as property_count
    FROM iceberg_scan('s3://stormops-lakehouse/enriched/property_features')
    WHERE timestamp > CURRENT_DATE - INTERVAL 30 DAYS
    GROUP BY census_tract_geoid
    ORDER BY avg_sii DESC;
""")
```

---

### 2. Vector & Similarity Infrastructure

#### Milvus for Embeddings
**Purpose**: "Find properties/neighborhoods/scripts similar to X"

**Setup**:
```yaml
# docker-compose.yml
  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
      - "9091:9091"
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
```

**Collection Schema**:
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

connections.connect("default", host="localhost", port="19530")

# Property embeddings collection
fields = [
    FieldSchema(name="property_id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128),
    FieldSchema(name="sii_score", dtype=DataType.FLOAT),
    FieldSchema(name="ses_tier", dtype=DataType.VARCHAR, max_length=20),
    FieldSchema(name="conversion_value", dtype=DataType.INT64),
]

schema = CollectionSchema(fields, description="Property behavioral + SII fingerprints")
collection = Collection("property_embeddings", schema)

# Create index for fast similarity search
index_params = {
    "metric_type": "L2",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 1024}
}
collection.create_index("embedding", index_params)
```

**Generate Embeddings**:
```python
import numpy as np
from sklearn.preprocessing import StandardScaler

def create_property_embedding(property_data: dict) -> np.ndarray:
    """Create 128-dim embedding from property features."""
    features = [
        property_data['sii_score'] / 100,
        property_data['moe_usd'] / 50000,
        property_data['roof_age_years'] / 50,
        property_data['median_income'] / 200000,
        property_data['median_home_value'] / 1000000,
        property_data['risk_tolerance'] / 100,
        property_data['price_sensitivity'] / 100,
        property_data['urgency_baseline'] / 100,
        property_data['response_rate'],
        property_data['conversion_rate'],
        # ... 118 more features
    ]
    
    # Normalize and pad to 128 dimensions
    embedding = StandardScaler().fit_transform([features])[0]
    return np.pad(embedding, (0, 128 - len(features)))

# Insert embeddings
property_embeddings = [
    {
        "property_id": prop['id'],
        "embedding": create_property_embedding(prop).tolist(),
        "sii_score": prop['sii_score'],
        "ses_tier": prop['ses_tier'],
        "conversion_value": prop['conversion_value']
    }
    for prop in high_value_conversions
]

collection.insert(property_embeddings)
```

**Similarity Search**:
```python
def find_similar_properties(reference_property_id: str, top_k: int = 200):
    """Find properties similar to high-performing reference."""
    # Get reference embedding
    ref_result = collection.query(
        expr=f"property_id == '{reference_property_id}'",
        output_fields=["embedding"]
    )
    ref_embedding = ref_result[0]['embedding']
    
    # Search for similar
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    results = collection.search(
        data=[ref_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["property_id", "sii_score", "ses_tier"]
    )
    
    return [
        {
            "property_id": hit.entity.get('property_id'),
            "similarity_score": 1 / (1 + hit.distance),  # Convert L2 to similarity
            "sii_score": hit.entity.get('sii_score'),
            "ses_tier": hit.entity.get('ses_tier')
        }
        for hit in results[0]
    ]

# Use case: Clone successful campaign
successful_properties = ['prop_123', 'prop_456', 'prop_789']
expansion_targets = []

for prop_id in successful_properties:
    similar = find_similar_properties(prop_id, top_k=200)
    expansion_targets.extend(similar)

# Deduplicate and rank
expansion_targets = sorted(
    {t['property_id']: t for t in expansion_targets}.values(),
    key=lambda x: x['similarity_score'] * x['sii_score'],
    reverse=True
)[:500]
```

---

## Data Flows

### Flow 1: Operational → Lakehouse (Hourly Sync)

```python
# Airflow DAG: sync_postgres_to_iceberg.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def sync_table_to_iceberg(table_name: str):
    """Sync Postgres table to Iceberg."""
    import pandas as pd
    from sqlalchemy import create_engine
    from pyiceberg.catalog import load_catalog
    
    # Read from Postgres
    pg_engine = create_engine('postgresql://stormops:password@postgres:5432/stormops')
    df = pd.read_sql(f"SELECT * FROM {table_name} WHERE updated_at > NOW() - INTERVAL '1 hour'", pg_engine)
    
    # Write to Iceberg (append mode)
    catalog = load_catalog("stormops")
    table = catalog.load_table(f"stormops.enriched.{table_name}")
    table.append(df)

with DAG(
    'sync_postgres_to_iceberg',
    default_args={'owner': 'stormops'},
    schedule_interval='@hourly',
    start_date=datetime(2026, 1, 1),
    catchup=False
) as dag:
    
    for table in ['properties', 'behavior_events', 'building_permits', 'competitor_activity']:
        PythonOperator(
            task_id=f'sync_{table}',
            python_callable=sync_table_to_iceberg,
            op_kwargs={'table_name': table}
        )
```

### Flow 2: Lakehouse → ML → Postgres (Nightly Scoring)

```python
# Kedro pipeline: batch_scoring_pipeline.py
from kedro.pipeline import Pipeline, node

def load_features_from_iceberg():
    """Load feature table from Iceberg."""
    import duckdb
    con = duckdb.connect()
    return con.execute("""
        SELECT * FROM iceberg_scan('s3://stormops-lakehouse/features/property_features')
        WHERE timestamp > CURRENT_DATE - INTERVAL 90 DAYS
    """).df()

def score_properties(features_df, model):
    """Score all properties with latest model."""
    import mlflow
    
    # Load model from MLflow
    model_uri = f"models:/sii_model/production"
    model = mlflow.pyfunc.load_model(model_uri)
    
    # Score
    features_df['sii_score_v2'] = model.predict(features_df)
    return features_df[['property_id', 'sii_score_v2', 'timestamp']]

def write_scores_to_postgres(scores_df):
    """Write scores back to operational DB."""
    from sqlalchemy import create_engine
    engine = create_engine('postgresql://stormops:password@postgres:5432/stormops')
    
    # Upsert scores
    scores_df.to_sql('property_scores_staging', engine, if_exists='replace', index=False)
    
    with engine.connect() as conn:
        conn.execute("""
            INSERT INTO property_exposure (property_id, sii_score, calculated_at)
            SELECT property_id, sii_score_v2, timestamp
            FROM property_scores_staging
            ON CONFLICT (property_id) DO UPDATE
            SET sii_score = EXCLUDED.sii_score,
                calculated_at = EXCLUDED.calculated_at;
        """)

def create_batch_scoring_pipeline():
    return Pipeline([
        node(
            func=load_features_from_iceberg,
            inputs=None,
            outputs="features_df",
            name="load_features"
        ),
        node(
            func=score_properties,
            inputs=["features_df", "params:model_name"],
            outputs="scores_df",
            name="score_properties"
        ),
        node(
            func=write_scores_to_postgres,
            inputs="scores_df",
            outputs=None,
            name="write_to_postgres"
        )
    ])
```

---

## References

Content was rephrased for compliance with licensing restrictions.

[1] Building Modern Data Lake - https://openmetal.io/resources/blog/building-a-modern-data-lake-using-open-source-tools/
[2] Dremio Data Lakehouse - https://www.dremio.com/blog/open-source-and-the-data-lakehouse-apache-arrow-apache-iceberg-nessie-and-dremio/
[3] Vector DB for Behavior Analysis - https://www.meegle.com/en_us/topics/vector-databases/vector-database-for-user-behavior-analysis
[4] MLOps Tools Landscape - https://neptune.ai/blog/mlops-tools-platforms-landscape
[5] MLOps Platforms - https://www.digitalocean.com/resources/articles/mlops-platforms
[6] Data Lakehouse Tools - https://azumo.com/artificial-intelligence/ai-insights/data-lakehouse-tools


### Flow 3: Streaming Events → Real-Time Features (Seconds)

```python
# Flink job: realtime_features.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

env = StreamExecutionEnvironment.get_execution_environment()
t_env = StreamTableEnvironment.create(env)

# Source: Kafka behavior_events stream
t_env.execute_sql("""
    CREATE TABLE behavior_events (
        event_id STRING,
        property_id STRING,
        customer_id STRING,
        event_type STRING,
        channel STRING,
        event_timestamp TIMESTAMP(3),
        response BOOLEAN,
        conversion BOOLEAN,
        WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'behavior_events',
        'properties.bootstrap.servers' = 'kafka:9092',
        'format' = 'json'
    )
""")

# Sink: Postgres sector_features table
t_env.execute_sql("""
    CREATE TABLE sector_features (
        census_tract_geoid STRING,
        engagement_7d INT,
        response_rate_7d DOUBLE,
        conversion_rate_7d DOUBLE,
        last_updated TIMESTAMP(3),
        PRIMARY KEY (census_tract_geoid) NOT ENFORCED
    ) WITH (
        'connector' = 'jdbc',
        'url' = 'jdbc:postgresql://postgres:5432/stormops',
        'table-name' = 'sector_features',
        'username' = 'stormops',
        'password' = 'password'
    )
""")

# Compute rolling 7-day features
t_env.execute_sql("""
    INSERT INTO sector_features
    SELECT 
        p.census_tract_geoid,
        COUNT(*) as engagement_7d,
        AVG(CAST(be.response AS INT)) as response_rate_7d,
        AVG(CAST(be.conversion AS INT)) as conversion_rate_7d,
        MAX(be.event_timestamp) as last_updated
    FROM behavior_events be
    JOIN properties FOR SYSTEM_TIME AS OF be.event_timestamp AS p
        ON be.property_id = p.property_id
    WHERE be.event_timestamp > CURRENT_TIMESTAMP - INTERVAL '7' DAY
    GROUP BY p.census_tract_geoid
""")
```

---

## 3. ML / MLOps Backbone

### MLflow Setup

```yaml
# docker-compose.yml
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    ports:
      - "5000:5000"
    environment:
      MLFLOW_BACKEND_STORE_URI: postgresql://mlflow:password@postgres:5432/mlflow
      MLFLOW_DEFAULT_ARTIFACT_ROOT: s3://stormops-mlflow/artifacts
      AWS_ACCESS_KEY_ID: admin
      AWS_SECRET_ACCESS_KEY: password
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
    command: mlflow server --host 0.0.0.0 --port 5000
```

### Model Training Pipeline

```python
# kedro/pipelines/model_training/nodes.py
import mlflow
import mlflow.sklearn
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

def train_sii_model(features_df):
    """Train SII prediction model."""
    mlflow.set_experiment("sii_prediction")
    
    with mlflow.start_run(run_name="sii_v1.3.0"):
        # Prepare data
        X = features_df[[
            'hail_size_inches', 'wind_speed_mph', 'roof_age_years',
            'roof_material_encoded', 'roof_pitch', 'building_sqft',
            'prior_damage_count', 'days_since_last_storm'
        ]]
        y = features_df['actual_damage_score']  # From claims/inspections
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train
        params = {
            'n_estimators': 200,
            'max_depth': 8,
            'learning_rate': 0.05,
            'subsample': 0.8
        }
        mlflow.log_params(params)
        
        model = GradientBoostingRegressor(**params)
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        mlflow.log_metrics({
            'mae': mae,
            'r2': r2,
            'test_samples': len(y_test)
        })
        
        # Log model
        mlflow.sklearn.log_model(
            model,
            "model",
            registered_model_name="sii_model"
        )
        
        return model, {'mae': mae, 'r2': r2}

def promote_model_to_production(model_name: str, run_id: str):
    """Promote model to production stage."""
    client = mlflow.tracking.MlflowClient()
    
    # Get model version
    model_version = client.search_model_versions(f"name='{model_name}'")[0].version
    
    # Transition to production
    client.transition_model_version_stage(
        name=model_name,
        version=model_version,
        stage="Production",
        archive_existing_versions=True
    )
```

### Kedro Pipeline Definition

```python
# kedro/pipelines/model_training/pipeline.py
from kedro.pipeline import Pipeline, node

def create_pipeline(**kwargs):
    return Pipeline([
        node(
            func=load_training_data,
            inputs="params:training_data_path",
            outputs="raw_training_data",
            name="load_data"
        ),
        node(
            func=engineer_features,
            inputs="raw_training_data",
            outputs="features_df",
            name="feature_engineering"
        ),
        node(
            func=train_sii_model,
            inputs="features_df",
            outputs=["sii_model", "metrics"],
            name="train_model"
        ),
        node(
            func=evaluate_model,
            inputs=["sii_model", "features_df"],
            outputs="evaluation_report",
            name="evaluate"
        ),
        node(
            func=promote_model_to_production,
            inputs=["params:model_name", "params:run_id"],
            outputs=None,
            name="promote_to_prod"
        )
    ])
```

---

## 4. Streaming + Triggers

### Kafka Setup

```yaml
# docker-compose.yml
  kafka:
    image: confluentinc/cp-kafka:latest
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
```

### CDC from Postgres to Kafka (Debezium)

```yaml
# docker-compose.yml
  debezium:
    image: debezium/connect:latest
    ports:
      - "8083:8083"
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
      GROUP_ID: 1
      CONFIG_STORAGE_TOPIC: debezium_configs
      OFFSET_STORAGE_TOPIC: debezium_offsets
      STATUS_STORAGE_TOPIC: debezium_statuses
```

```bash
# Register Postgres connector
curl -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d '{
  "name": "stormops-postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "stormops",
    "database.password": "password",
    "database.dbname": "stormops",
    "database.server.name": "stormops",
    "table.include.list": "public.behavior_events,public.property_exposure,public.building_permits",
    "plugin.name": "pgoutput"
  }
}'
```

### Real-Time Trigger Service

```python
# trigger_service_streaming.py
from kafka import KafkaConsumer
import json
from datetime import datetime

consumer = KafkaConsumer(
    'stormops.public.property_exposure',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

def evaluate_trigger_conditions(property_update):
    """Check if property update triggers any actions."""
    property_id = property_update['property_id']
    new_sii = property_update['sii_score']
    
    # Load property context
    context = get_property_context(property_id)
    
    # Trigger conditions
    triggers = []
    
    # High SII + recent storm + no recent contact
    if (new_sii > 75 and 
        context['days_since_storm'] < 14 and 
        context['days_since_last_contact'] > 7):
        triggers.append({
            'type': 'urgent_outreach',
            'priority': 1,
            'reason': f'High SII ({new_sii}) + recent storm'
        })
    
    # SII spike (>20 point increase)
    if new_sii - context.get('previous_sii', 0) > 20:
        triggers.append({
            'type': 'sii_spike_alert',
            'priority': 2,
            'reason': f'SII increased from {context["previous_sii"]} to {new_sii}'
        })
    
    return triggers

# Consume stream
for message in consumer:
    property_update = message.value
    
    triggers = evaluate_trigger_conditions(property_update)
    
    for trigger in triggers:
        # Create Proposal in Postgres
        create_proposal(
            property_id=property_update['property_id'],
            trigger_type=trigger['type'],
            priority=trigger['priority'],
            rationale=trigger['reason']
        )
        
        print(f"[{datetime.now()}] Triggered {trigger['type']} for {property_update['property_id']}")
```

---

## 5. Advanced Analytics & Graph Layer

### Neo4j Setup

```yaml
# docker-compose.yml
  neo4j:
    image: neo4j:latest
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
    volumes:
      - ./neo4j_data:/data
```

### Build Contractor Competition Graph

```python
# build_competition_graph.py
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def build_contractor_network():
    """Build contractor competition graph from permit data."""
    with driver.session() as session:
        # Create contractor nodes
        session.run("""
            LOAD CSV WITH HEADERS FROM 'file:///contractors.csv' AS row
            CREATE (c:Contractor {
                id: row.contractor_id,
                name: row.contractor_name,
                tier: row.tier,
                total_permits: toInteger(row.total_permits)
            })
        """)
        
        # Create ZIP nodes
        session.run("""
            LOAD CSV WITH HEADERS FROM 'file:///zips.csv' AS row
            CREATE (z:ZIP {
                code: row.zip_code,
                median_income: toInteger(row.median_income),
                property_count: toInteger(row.property_count)
            })
        """)
        
        # Create OPERATES_IN relationships
        session.run("""
            LOAD CSV WITH HEADERS FROM 'file:///contractor_activity.csv' AS row
            MATCH (c:Contractor {id: row.contractor_id})
            MATCH (z:ZIP {code: row.zip_code})
            CREATE (c)-[:OPERATES_IN {
                permit_count: toInteger(row.permit_count),
                market_share: toFloat(row.market_share),
                avg_ticket: toInteger(row.avg_ticket)
            }]->(z)
        """)
        
        # Create COMPETES_WITH relationships (contractors in same ZIP)
        session.run("""
            MATCH (c1:Contractor)-[r1:OPERATES_IN]->(z:ZIP)<-[r2:OPERATES_IN]-(c2:Contractor)
            WHERE c1.id < c2.id
            CREATE (c1)-[:COMPETES_WITH {
                zip_code: z.code,
                c1_share: r1.market_share,
                c2_share: r2.market_share,
                intensity: abs(r1.market_share - r2.market_share)
            }]->(c2)
        """)

def find_underserved_zips():
    """Find ZIPs with high value but low competition."""
    with driver.session() as session:
        result = session.run("""
            MATCH (z:ZIP)
            OPTIONAL MATCH (c:Contractor)-[r:OPERATES_IN]->(z)
            WITH z, COUNT(c) as contractor_count, SUM(r.permit_count) as total_permits
            WHERE contractor_count < 3 AND z.median_income > 75000
            RETURN z.code as zip_code,
                   z.median_income as income,
                   z.property_count as properties,
                   contractor_count,
                   total_permits
            ORDER BY z.median_income DESC
            LIMIT 20
        """)
        
        return [dict(record) for record in result]

def find_competitor_weak_spots(competitor_id: str):
    """Find where competitor is weak vs. you."""
    with driver.session() as session:
        result = session.run("""
            MATCH (them:Contractor {id: $competitor_id})-[r1:OPERATES_IN]->(z:ZIP)
            MATCH (us:Contractor {id: $your_id})-[r2:OPERATES_IN]->(z)
            WHERE r2.market_share > r1.market_share
            RETURN z.code as zip_code,
                   r2.market_share as our_share,
                   r1.market_share as their_share,
                   (r2.market_share - r1.market_share) as advantage
            ORDER BY advantage DESC
        """, competitor_id=competitor_id, your_id=YOUR_CONTRACTOR_ID)
        
        return [dict(record) for record in result]
```

### Neighborhood Influence Network

```python
def build_influence_network():
    """Build word-of-mouth diffusion graph."""
    with driver.session() as session:
        # Create property nodes
        session.run("""
            MATCH (p:Property)
            SET p.converted = EXISTS((p)<-[:CONVERTED])
        """)
        
        # Create NEIGHBOR relationships (within 500m)
        session.run("""
            MATCH (p1:Property), (p2:Property)
            WHERE p1.property_id < p2.property_id
              AND distance(p1.location, p2.location) < 500
            CREATE (p1)-[:NEIGHBOR {distance_m: distance(p1.location, p2.location)}]->(p2)
        """)
        
        # Identify influence patterns
        session.run("""
            MATCH (p1:Property {converted: true})-[:NEIGHBOR]-(p2:Property)
            WHERE p2.conversion_date > p1.conversion_date
              AND duration.between(p1.conversion_date, p2.conversion_date).days < 30
            CREATE (p1)-[:INFLUENCED {days_apart: duration.between(p1.conversion_date, p2.conversion_date).days}]->(p2)
        """)

def predict_diffusion_path(seed_property_id: str):
    """Predict which neighbors likely to convert next."""
    with driver.session() as session:
        result = session.run("""
            MATCH path = (seed:Property {property_id: $seed_id})-[:NEIGHBOR*1..2]-(target:Property)
            WHERE NOT target.converted
              AND target.sii_score > 60
            WITH target, 
                 length(path) as hops,
                 COUNT(DISTINCT seed) as converted_neighbors
            RETURN target.property_id as property_id,
                   target.address as address,
                   hops,
                   converted_neighbors,
                   target.sii_score as sii_score,
                   (converted_neighbors * 10 + target.sii_score) as diffusion_score
            ORDER BY diffusion_score DESC
            LIMIT 50
        """, seed_id=seed_property_id)
        
        return [dict(record) for record in result]
```

---

## 6. Orchestration

### Airflow DAGs

```python
# dags/stormops_master_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'stormops',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['alerts@stormops.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

# Daily data ingestion
with DAG(
    'daily_data_ingestion',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # 2 AM daily
    start_date=datetime(2026, 1, 1),
    catchup=False
) as ingestion_dag:
    
    ingest_noaa = PythonOperator(
        task_id='ingest_noaa_storms',
        python_callable=ingest_noaa_data
    )
    
    ingest_permits = PythonOperator(
        task_id='ingest_building_permits',
        python_callable=ingest_permit_data
    )
    
    ingest_census = PythonOperator(
        task_id='ingest_census_updates',
        python_callable=ingest_census_data
    )
    
    sync_to_iceberg = BashOperator(
        task_id='sync_to_lakehouse',
        bash_command='python /opt/stormops/sync_to_iceberg.py'
    )
    
    [ingest_noaa, ingest_permits, ingest_census] >> sync_to_iceberg

# Weekly model retraining
with DAG(
    'weekly_model_retraining',
    default_args=default_args,
    schedule_interval='0 3 * * 0',  # 3 AM Sunday
    start_date=datetime(2026, 1, 1),
    catchup=False
) as training_dag:
    
    prepare_training_data = BashOperator(
        task_id='prepare_data',
        bash_command='kedro run --pipeline data_preparation'
    )
    
    train_sii_model = BashOperator(
        task_id='train_sii',
        bash_command='kedro run --pipeline sii_training'
    )
    
    train_uplift_model = BashOperator(
        task_id='train_uplift',
        bash_command='kedro run --pipeline uplift_training'
    )
    
    evaluate_models = BashOperator(
        task_id='evaluate',
        bash_command='kedro run --pipeline model_evaluation'
    )
    
    prepare_training_data >> [train_sii_model, train_uplift_model] >> evaluate_models

# Nightly batch scoring
with DAG(
    'nightly_batch_scoring',
    default_args=default_args,
    schedule_interval='0 1 * * *',  # 1 AM daily
    start_date=datetime(2026, 1, 1),
    catchup=False
) as scoring_dag:
    
    score_all_properties = BashOperator(
        task_id='score_properties',
        bash_command='kedro run --pipeline batch_scoring'
    )
    
    update_embeddings = PythonOperator(
        task_id='update_vector_db',
        python_callable=update_milvus_embeddings
    )
    
    refresh_competitor_metrics = PythonOperator(
        task_id='refresh_competitor_intel',
        python_callable=calculate_competitor_metrics
    )
    
    score_all_properties >> [update_embeddings, refresh_competitor_metrics]
```

---

## Complete System Integration

### Write-Back to Postgres

```python
# write_enriched_to_postgres.py
def write_ml_outputs_to_postgres():
    """Write ML model outputs back to operational DB."""
    from sqlalchemy import create_engine
    import duckdb
    
    # Load from Iceberg
    con = duckdb.connect()
    ml_outputs = con.execute("""
        SELECT 
            property_id,
            sii_score_v2,
            uplift_score,
            churn_risk_score,
            psychographic_segment,
            competitor_pressure_index,
            calculated_at
        FROM iceberg_scan('s3://stormops-lakehouse/model_outputs/latest')
    """).df()
    
    # Write to Postgres
    pg_engine = create_engine('postgresql://stormops:password@postgres:5432/stormops')
    
    # Upsert to property_ml_scores table
    ml_outputs.to_sql('property_ml_scores_staging', pg_engine, if_exists='replace', index=False)
    
    with pg_engine.connect() as conn:
        conn.execute("""
            INSERT INTO property_ml_scores (
                property_id, sii_score, uplift_score, churn_risk, 
                psychographic_segment, competitor_pressure, updated_at
            )
            SELECT 
                property_id, sii_score_v2, uplift_score, churn_risk_score,
                psychographic_segment, competitor_pressure_index, calculated_at
            FROM property_ml_scores_staging
            ON CONFLICT (property_id) DO UPDATE SET
                sii_score = EXCLUDED.sii_score,
                uplift_score = EXCLUDED.uplift_score,
                churn_risk = EXCLUDED.churn_risk,
                psychographic_segment = EXCLUDED.psychographic_segment,
                competitor_pressure = EXCLUDED.competitor_pressure,
                updated_at = EXCLUDED.updated_at;
        """)
        conn.commit()
```

---

## Deployment

### Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Operational DB
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: stormops
      POSTGRES_USER: stormops
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Object Storage
  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  # Lakehouse
  iceberg-rest:
    image: tabulario/iceberg-rest
    ports:
      - "8181:8181"
    environment:
      AWS_ACCESS_KEY_ID: admin
      AWS_SECRET_ACCESS_KEY: password
      CATALOG_WAREHOUSE: s3://stormops-lakehouse/

  # Query Engine
  trino:
    image: trinodb/trino
    ports:
      - "8080:8080"
    volumes:
      - ./trino/catalog:/etc/trino/catalog

  # Streaming
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:latest
    ports:
      - "9092:9092"
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092

  # Vector DB
  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"

  # Graph DB
  neo4j:
    image: neo4j:latest
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password

  # MLflow
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    ports:
      - "5000:5000"
    environment:
      MLFLOW_BACKEND_STORE_URI: postgresql://mlflow:password@postgres:5432/mlflow
      MLFLOW_DEFAULT_ARTIFACT_ROOT: s3://stormops-mlflow/

  # Airflow
  airflow-webserver:
    image: apache/airflow:latest
    ports:
      - "8081:8080"
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql://airflow:password@postgres:5432/airflow
    volumes:
      - ./dags:/opt/airflow/dags

volumes:
  postgres_data:
  minio_data:
```

### Start Full Stack

```bash
# Initialize
docker-compose up -d

# Wait for services
sleep 30

# Initialize Airflow
docker-compose exec airflow-webserver airflow db init
docker-compose exec airflow-webserver airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@stormops.com

# Create Iceberg catalog
python scripts/init_iceberg_catalog.py

# Load initial data
python scripts/bootstrap_data.py

# Start Streamlit control plane
streamlit run control_plane.py --server.port 8501
```

---

## Summary: What Each Layer Does

| Layer | Components | Purpose | Writes To |
|-------|-----------|---------|-----------|
| **Operational** | Postgres/PostGIS | Source of truth for live ops | - |
| **Streaming** | Kafka + Flink | Real-time features (seconds) | Postgres sector_features |
| **Lakehouse** | Iceberg + Trino | Historical analytics, big joins | - |
| **Vector** | Milvus | Similarity search | - |
| **ML** | MLflow + Kedro + Spark | Model training & scoring | Postgres property_ml_scores |
| **Graph** | Neo4j | Network analysis | - |
| **Orchestration** | Airflow | Schedule all pipelines | All layers |

**Data Flow**:
1. Postgres → Kafka (CDC) → Flink → Postgres (real-time)
2. Postgres → Iceberg (hourly sync) → Spark/Trino (batch analytics)
3. Iceberg → ML training → MLflow → Batch scoring → Postgres
4. Postgres → Milvus (embeddings) → Similarity API
5. Postgres → Neo4j (graph) → Network insights

**Control Plane Queries**:
- Operational: Postgres directly
- Analytics: Trino (federated Postgres + Iceberg)
- Similarity: Milvus API
- Network: Neo4j Cypher

This stack gives StormOps production-grade analytics while keeping Postgres as the operational source of truth.
