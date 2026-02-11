# SII ML Pipeline v1.0

## Overview
End-to-end ML pipeline for Storm Impact Index (SII) prediction using Kedro + MLflow + Spark, with batch scoring that writes back to Postgres for the control plane.

**Flow**: Iceberg (training data) → Kedro (pipeline) → MLflow (versioning) → Spark (scoring) → Postgres (serving) → Proposals (usage)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Training Data (Iceberg)                                        │
│  - storm_events + property_features + roof_attributes           │
│  - Labels: claims_filed, damage_severity, permit_filed         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  Kedro Pipeline                                                 │
│  1. load_features → 2. engineer → 3. train → 4. evaluate       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  MLflow Registry                                                │
│  - Experiment tracking (metrics, params, artifacts)             │
│  - Model versioning (SII_v1.0, SII_v1.1, ...)                  │
│  - Production promotion                                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  Batch Scoring (Spark)                                          │
│  - Load production model from MLflow                            │
│  - Score all active properties                                  │
│  - Write sii_score to Postgres                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  Postgres (Operational DB)                                      │
│  - property_exposure.sii_score                                  │
│  - Used by: Proposals, Routing, Impact Reports                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup

### 1. Install Dependencies

```bash
pip install kedro kedro-datasets mlflow pyspark xgboost scikit-learn pyiceberg trino-python-client
```

### 2. Initialize Kedro Project

```bash
kedro new --name sii_pipeline --starter pandas-iris
cd sii_pipeline
```

### 3. Configure Catalogs

**conf/base/catalog.yml**:
```yaml
# Training data from Iceberg
training_features:
  type: pandas.ParquetDataset
  filepath: s3://stormops-lakehouse/features/sii_training_features.parquet
  credentials: aws_credentials

training_labels:
  type: pandas.ParquetDataset
  filepath: s3://stormops-lakehouse/features/sii_training_labels.parquet
  credentials: aws_credentials

# Model artifacts
sii_model:
  type: pickle.PickleDataset
  filepath: data/06_models/sii_model.pkl

# Scoring input
scoring_features:
  type: pandas.ParquetDataset
  filepath: s3://stormops-lakehouse/features/active_properties.parquet
  credentials: aws_credentials
```

**conf/base/parameters.yml**:
```yaml
model:
  name: "sii_model"
  version: "1.0.0"
  
features:
  - hail_size_inches
  - wind_speed_mph
  - roof_age_years
  - roof_material_encoded
  - roof_pitch
  - building_sqft
  - prior_damage_count
  - days_since_last_storm
  - median_home_value
  - tract_permit_velocity

xgboost_params:
  n_estimators: 200
  max_depth: 8
  learning_rate: 0.05
  subsample: 0.8
  colsample_bytree: 0.8
  objective: "reg:squarederror"
  random_state: 42

mlflow:
  tracking_uri: "http://localhost:5000"
  experiment_name: "sii_prediction"
```

---

## Pipeline Implementation

### Node 1: Load Features

**src/sii_pipeline/pipelines/data_engineering/nodes.py**:
```python
import duckdb
import pandas as pd

def load_training_features() -> pd.DataFrame:
    """Load training features from Iceberg via DuckDB."""
    con = duckdb.connect()
    
    query = """
    SELECT 
        p.property_id,
        se.magnitude as hail_size_inches,
        se.wind_speed_mph,
        r.roof_age_years,
        r.roof_material,
        r.roof_pitch,
        p.building_sqft,
        COUNT(DISTINCT pe_hist.event_id) as prior_damage_count,
        DATEDIFF('day', MAX(se_hist.begin_datetime), se.begin_datetime) as days_since_last_storm,
        ct.median_home_value,
        tm.roofing_permit_count_12mo / NULLIF(ct.total_housing_units, 0) * 1000 as tract_permit_velocity
    FROM iceberg_scan('s3://stormops-lakehouse/enriched/properties') p
    JOIN iceberg_scan('s3://stormops-lakehouse/enriched/roofs') r 
        ON p.property_id = r.property_id
    JOIN iceberg_scan('s3://stormops-lakehouse/raw/storm_events') se 
        ON ST_DWithin(p.geometry, se.event_path, 5000)
    JOIN iceberg_scan('s3://stormops-lakehouse/enriched/census_tracts') ct 
        ON p.census_tract_geoid = ct.tract_geoid
    JOIN iceberg_scan('s3://stormops-lakehouse/enriched/tract_metrics') tm 
        ON p.census_tract_geoid = tm.tract_geoid
    LEFT JOIN iceberg_scan('s3://stormops-lakehouse/enriched/property_exposure') pe_hist 
        ON p.property_id = pe_hist.property_id 
        AND pe_hist.calculated_at < se.begin_datetime
    LEFT JOIN iceberg_scan('s3://stormops-lakehouse/raw/storm_events') se_hist 
        ON pe_hist.event_id = se_hist.event_id
    WHERE se.begin_datetime BETWEEN '2020-01-01' AND '2025-12-31'
    GROUP BY p.property_id, se.event_id, se.magnitude, se.wind_speed_mph, 
             r.roof_age_years, r.roof_material, r.roof_pitch, p.building_sqft,
             ct.median_home_value, tm.roofing_permit_count_12mo, ct.total_housing_units
    """
    
    df = con.execute(query).df()
    return df

def load_training_labels() -> pd.DataFrame:
    """Load labels from claims and permits."""
    con = duckdb.connect()
    
    query = """
    SELECT 
        p.property_id,
        se.event_id,
        COALESCE(ic.roof_damage::int, 0) as claim_filed,
        COALESCE(ic.claim_amount / 50000.0, 0) as damage_severity,
        CASE WHEN bp.permit_id IS NOT NULL THEN 1 ELSE 0 END as permit_filed,
        -- Composite label: 0-100 scale
        LEAST(100, 
            COALESCE(ic.roof_damage::int, 0) * 30 +
            COALESCE(ic.claim_amount / 1000.0, 0) +
            CASE WHEN bp.permit_id IS NOT NULL THEN 20 ELSE 0 END
        ) as sii_label
    FROM iceberg_scan('s3://stormops-lakehouse/enriched/properties') p
    JOIN iceberg_scan('s3://stormops-lakehouse/raw/storm_events') se 
        ON ST_DWithin(p.geometry, se.event_path, 5000)
    LEFT JOIN iceberg_scan('s3://stormops-lakehouse/enriched/insurance_claims') ic 
        ON p.property_id = ic.property_id 
        AND ic.event_id = se.event_id
    LEFT JOIN iceberg_scan('s3://stormops-lakehouse/enriched/building_permits') bp 
        ON p.property_id = bp.property_id 
        AND bp.issue_date BETWEEN se.begin_datetime AND se.begin_datetime + INTERVAL 90 DAYS
        AND bp.permit_type ILIKE '%roof%'
    WHERE se.begin_datetime BETWEEN '2020-01-01' AND '2025-12-31'
    """
    
    df = con.execute(query).df()
    return df
```

### Node 2: Feature Engineering

```python
from sklearn.preprocessing import LabelEncoder, StandardScaler
import numpy as np

def engineer_features(features_df: pd.DataFrame, labels_df: pd.DataFrame) -> pd.DataFrame:
    """Engineer and encode features."""
    # Join features with labels
    df = features_df.merge(labels_df[['property_id', 'event_id', 'sii_label']], 
                           on=['property_id', 'event_id'], how='inner')
    
    # Encode categorical
    le = LabelEncoder()
    df['roof_material_encoded'] = le.fit_transform(df['roof_material'].fillna('Unknown'))
    
    # Handle missing values
    df['roof_pitch'] = df['roof_pitch'].fillna(df['roof_pitch'].median())
    df['days_since_last_storm'] = df['days_since_last_storm'].fillna(9999)
    df['prior_damage_count'] = df['prior_damage_count'].fillna(0)
    
    # Create interaction features
    df['hail_x_roof_age'] = df['hail_size_inches'] * df['roof_age_years']
    df['wind_x_building_size'] = df['wind_speed_mph'] * np.log1p(df['building_sqft'])
    
    return df
```

### Node 3: Train Model

```python
import mlflow
import mlflow.xgboost
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def train_sii_model(df: pd.DataFrame, params: dict) -> XGBRegressor:
    """Train SII prediction model with MLflow tracking."""
    mlflow.set_tracking_uri(params['mlflow']['tracking_uri'])
    mlflow.set_experiment(params['mlflow']['experiment_name'])
    
    with mlflow.start_run(run_name=f"sii_{params['model']['version']}"):
        # Prepare data
        feature_cols = params['features'] + ['hail_x_roof_age', 'wind_x_building_size']
        X = df[feature_cols]
        y = df['sii_label']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Log parameters
        mlflow.log_params(params['xgboost_params'])
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_param("n_train", len(X_train))
        mlflow.log_param("n_test", len(X_test))
        
        # Train
        model = XGBRegressor(**params['xgboost_params'])
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        train_mae = mean_absolute_error(y_train, y_pred_train)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)
        
        # Log metrics
        mlflow.log_metrics({
            'train_mae': train_mae,
            'test_mae': test_mae,
            'train_rmse': train_rmse,
            'test_rmse': test_rmse,
            'train_r2': train_r2,
            'test_r2': test_r2
        })
        
        # Log feature importance
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        mlflow.log_text(importance_df.to_csv(index=False), "feature_importance.csv")
        
        # Log model
        mlflow.xgboost.log_model(
            model,
            "model",
            registered_model_name=params['model']['name']
        )
        
        print(f"Model trained: MAE={test_mae:.2f}, RMSE={test_rmse:.2f}, R²={test_r2:.3f}")
        
        return model
```

### Node 4: Evaluate & Promote

```python
def evaluate_model(model: XGBRegressor, df: pd.DataFrame, params: dict) -> dict:
    """Evaluate model and generate report."""
    feature_cols = params['features'] + ['hail_x_roof_age', 'wind_x_building_size']
    X = df[feature_cols]
    y = df['sii_label']
    
    y_pred = model.predict(X)
    
    # Error analysis by bins
    df['sii_pred'] = y_pred
    df['error'] = np.abs(y - y_pred)
    
    error_by_hail = df.groupby(pd.cut(df['hail_size_inches'], bins=5))['error'].mean()
    error_by_age = df.groupby(pd.cut(df['roof_age_years'], bins=5))['error'].mean()
    
    report = {
        'overall_mae': mean_absolute_error(y, y_pred),
        'overall_r2': r2_score(y, y_pred),
        'error_by_hail_size': error_by_hail.to_dict(),
        'error_by_roof_age': error_by_age.to_dict()
    }
    
    return report

def promote_to_production(model_name: str, version: str):
    """Promote model to production stage."""
    client = mlflow.tracking.MlflowClient()
    
    # Get latest version
    latest_versions = client.get_latest_versions(model_name, stages=["None"])
    if not latest_versions:
        raise ValueError(f"No model versions found for {model_name}")
    
    model_version = latest_versions[0].version
    
    # Transition to production
    client.transition_model_version_stage(
        name=model_name,
        version=model_version,
        stage="Production",
        archive_existing_versions=True
    )
    
    print(f"Model {model_name} v{model_version} promoted to Production")
```

### Pipeline Definition

**src/sii_pipeline/pipelines/training/pipeline.py**:
```python
from kedro.pipeline import Pipeline, node
from .nodes import (
    load_training_features,
    load_training_labels,
    engineer_features,
    train_sii_model,
    evaluate_model,
    promote_to_production
)

def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        node(
            func=load_training_features,
            inputs=None,
            outputs="raw_features",
            name="load_features"
        ),
        node(
            func=load_training_labels,
            inputs=None,
            outputs="raw_labels",
            name="load_labels"
        ),
        node(
            func=engineer_features,
            inputs=["raw_features", "raw_labels"],
            outputs="engineered_features",
            name="engineer_features"
        ),
        node(
            func=train_sii_model,
            inputs=["engineered_features", "params:model"],
            outputs="sii_model",
            name="train_model"
        ),
        node(
            func=evaluate_model,
            inputs=["sii_model", "engineered_features", "params:model"],
            outputs="evaluation_report",
            name="evaluate_model"
        )
    ])
```

---

## Batch Scoring Pipeline

**src/sii_pipeline/pipelines/scoring/nodes.py**:
```python
import mlflow
from sqlalchemy import create_engine

def load_active_properties() -> pd.DataFrame:
    """Load all active properties for scoring."""
    con = duckdb.connect()
    
    query = """
    SELECT 
        p.property_id,
        COALESCE(se.magnitude, 0) as hail_size_inches,
        COALESCE(se.wind_speed_mph, 0) as wind_speed_mph,
        r.roof_age_years,
        r.roof_material,
        r.roof_pitch,
        p.building_sqft,
        COUNT(DISTINCT pe_hist.event_id) as prior_damage_count,
        COALESCE(DATEDIFF('day', MAX(se_hist.begin_datetime), CURRENT_DATE), 9999) as days_since_last_storm,
        ct.median_home_value,
        tm.roofing_permit_count_12mo / NULLIF(ct.total_housing_units, 0) * 1000 as tract_permit_velocity
    FROM iceberg_scan('s3://stormops-lakehouse/enriched/properties') p
    JOIN iceberg_scan('s3://stormops-lakehouse/enriched/roofs') r 
        ON p.property_id = r.property_id
    JOIN iceberg_scan('s3://stormops-lakehouse/enriched/census_tracts') ct 
        ON p.census_tract_geoid = ct.tract_geoid
    JOIN iceberg_scan('s3://stormops-lakehouse/enriched/tract_metrics') tm 
        ON p.census_tract_geoid = tm.tract_geoid
    LEFT JOIN iceberg_scan('s3://stormops-lakehouse/raw/storm_events') se 
        ON ST_DWithin(p.geometry, se.event_path, 5000)
        AND se.begin_datetime > CURRENT_DATE - INTERVAL 90 DAYS
    LEFT JOIN iceberg_scan('s3://stormops-lakehouse/enriched/property_exposure') pe_hist 
        ON p.property_id = pe_hist.property_id
    LEFT JOIN iceberg_scan('s3://stormops-lakehouse/raw/storm_events') se_hist 
        ON pe_hist.event_id = se_hist.event_id
    WHERE p.status = 'active'
    GROUP BY p.property_id, se.magnitude, se.wind_speed_mph, r.roof_age_years, 
             r.roof_material, r.roof_pitch, p.building_sqft, ct.median_home_value,
             tm.roofing_permit_count_12mo, ct.total_housing_units
    """
    
    df = con.execute(query).df()
    return df

def score_properties(df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Score all properties with production model."""
    # Load production model
    model_uri = f"models:/{model_name}/Production"
    model = mlflow.xgboost.load_model(model_uri)
    
    # Engineer features (same as training)
    le = LabelEncoder()
    df['roof_material_encoded'] = le.fit_transform(df['roof_material'].fillna('Unknown'))
    df['roof_pitch'] = df['roof_pitch'].fillna(df['roof_pitch'].median())
    df['hail_x_roof_age'] = df['hail_size_inches'] * df['roof_age_years']
    df['wind_x_building_size'] = df['wind_speed_mph'] * np.log1p(df['building_sqft'])
    
    # Score
    feature_cols = [
        'hail_size_inches', 'wind_speed_mph', 'roof_age_years', 'roof_material_encoded',
        'roof_pitch', 'building_sqft', 'prior_damage_count', 'days_since_last_storm',
        'median_home_value', 'tract_permit_velocity', 'hail_x_roof_age', 'wind_x_building_size'
    ]
    
    df['sii_score'] = model.predict(df[feature_cols])
    df['sii_score'] = df['sii_score'].clip(0, 100)  # Clamp to 0-100
    
    return df[['property_id', 'sii_score']]

def write_scores_to_postgres(scores_df: pd.DataFrame):
    """Write SII scores back to Postgres."""
    engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')
    
    # Write to staging table
    scores_df['calculated_at'] = pd.Timestamp.now()
    scores_df.to_sql('sii_scores_staging', engine, if_exists='replace', index=False)
    
    # Upsert to property_exposure
    with engine.connect() as conn:
        conn.execute("""
            INSERT INTO property_exposure (property_id, sii_score, calculated_at)
            SELECT property_id, sii_score, calculated_at
            FROM sii_scores_staging
            ON CONFLICT (property_id) DO UPDATE
            SET sii_score = EXCLUDED.sii_score,
                calculated_at = EXCLUDED.calculated_at;
        """)
        conn.commit()
    
    print(f"Wrote {len(scores_df)} SII scores to Postgres")
```

---

## Airflow DAG

**dags/sii_pipeline_dag.py**:
```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'stormops',
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

# Weekly training
with DAG(
    'sii_model_training',
    default_args=default_args,
    schedule_interval='0 3 * * 0',  # 3 AM Sunday
    start_date=datetime(2026, 1, 1),
    catchup=False
) as training_dag:
    
    train = BashOperator(
        task_id='train_sii_model',
        bash_command='cd /opt/sii_pipeline && kedro run --pipeline training'
    )

# Nightly scoring
with DAG(
    'sii_batch_scoring',
    default_args=default_args,
    schedule_interval='0 1 * * *',  # 1 AM daily
    start_date=datetime(2026, 1, 1),
    catchup=False
) as scoring_dag:
    
    score = BashOperator(
        task_id='score_properties',
        bash_command='cd /opt/sii_pipeline && kedro run --pipeline scoring'
    )
```

---

## Usage

### Train Model
```bash
kedro run --pipeline training
```

### Score Properties
```bash
kedro run --pipeline scoring
```

### View MLflow UI
```bash
mlflow ui --host 0.0.0.0 --port 5000
```

Navigate to http://localhost:5000 to see experiments, compare runs, and manage models.

---

## Integration with Control Plane

### Query SII Scores (Streamlit)
```python
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

# Load properties with SII scores
df = pd.read_sql("""
    SELECT 
        p.property_id,
        p.address,
        pe.sii_score,
        pe.calculated_at,
        r.roof_age_years,
        ct.median_household_income
    FROM properties p
    JOIN property_exposure pe ON p.property_id = pe.property_id
    JOIN roofs r ON p.property_id = r.property_id
    JOIN census_tracts ct ON p.census_tract_geoid = ct.tract_geoid
    WHERE pe.sii_score > 70
    ORDER BY pe.sii_score DESC
    LIMIT 100
""", engine)

st.dataframe(df)
```

### Use in Proposals
```python
def generate_proposals_from_sii():
    """Generate proposals for high-SII properties."""
    high_sii_properties = pd.read_sql("""
        SELECT property_id, sii_score
        FROM property_exposure
        WHERE sii_score > 75
          AND calculated_at > NOW() - INTERVAL '24 hours'
    """, engine)
    
    for _, row in high_sii_properties.iterrows():
        create_proposal(
            property_id=row['property_id'],
            trigger_type='high_sii',
            priority=1 if row['sii_score'] > 85 else 2,
            rationale=f"SII score: {row['sii_score']:.1f}"
        )
```

---

## Next Steps

1. ✅ Train initial SII model
2. ✅ Promote to production in MLflow
3. ✅ Run batch scoring → Postgres
4. ✅ Update control plane to use `sii_score`
5. → Add GA4 integration (next document)
6. → Build vector similarity API
7. → Create playbook execution engine
