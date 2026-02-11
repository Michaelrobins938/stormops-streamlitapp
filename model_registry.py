"""
Model Registry and Versioning
Track model versions, enable safe rollout, and A/B testing
"""

from sqlalchemy import create_engine, text
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import json

class ModelRegistry:
    """Registry for ML model versions."""
    
    def __init__(self, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.engine = create_engine(db_url)
        self._init_tables()
    
    def _init_tables(self):
        """Create model registry tables."""
        with self.engine.begin() as conn:
            # Model versions
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    model_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    training_date TIMESTAMPTZ NOT NULL,
                    metrics JSONB NOT NULL,
                    artifacts JSONB,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(model_name, version)
                )
            """))
            
            # Model deployments
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS model_deployments (
                    deployment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    version_id UUID NOT NULL REFERENCES model_versions(version_id),
                    environment TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'live',
                    traffic_pct FLOAT NOT NULL DEFAULT 100.0,
                    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    retired_at TIMESTAMPTZ
                )
            """))
            
            # Model predictions (for auditing)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS model_predictions (
                    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    version_id UUID NOT NULL REFERENCES model_versions(version_id),
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    storm_id UUID NOT NULL REFERENCES storms(storm_id),
                    property_id UUID NOT NULL REFERENCES properties(property_id),
                    prediction FLOAT NOT NULL,
                    features JSONB,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_model_predictions_version 
                ON model_predictions(version_id, timestamp)
            """))
    
    def register_model(self, model_name: str, version: str, model_type: str, 
                      training_date: datetime, metrics: Dict, artifacts: Dict = None) -> uuid.UUID:
        """Register a new model version."""
        
        version_id = uuid.uuid4()
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO model_versions 
                (version_id, model_name, version, model_type, training_date, metrics, artifacts, status)
                VALUES (:vid, :name, :version, :type, :train_date, :metrics, :artifacts, 'candidate')
            """), {
                'vid': version_id,
                'name': model_name,
                'version': version,
                'type': model_type,
                'train_date': training_date,
                'metrics': json.dumps(metrics),
                'artifacts': json.dumps(artifacts) if artifacts else None
            })
        
        return version_id
    
    def deploy_model(self, version_id: uuid.UUID, environment: str = 'production', 
                    mode: str = 'live', traffic_pct: float = 100.0) -> uuid.UUID:
        """Deploy a model version."""
        
        deployment_id = uuid.uuid4()
        
        with self.engine.begin() as conn:
            # Retire existing deployments for this model in this environment
            conn.execute(text("""
                UPDATE model_deployments
                SET retired_at = NOW()
                WHERE version_id IN (
                    SELECT version_id FROM model_versions 
                    WHERE model_name = (
                        SELECT model_name FROM model_versions WHERE version_id = :vid
                    )
                )
                AND environment = :env
                AND retired_at IS NULL
            """), {'vid': version_id, 'env': environment})
            
            # Create new deployment
            conn.execute(text("""
                INSERT INTO model_deployments 
                (deployment_id, version_id, environment, mode, traffic_pct)
                VALUES (:did, :vid, :env, :mode, :traffic)
            """), {
                'did': deployment_id,
                'vid': version_id,
                'env': environment,
                'mode': mode,
                'traffic': traffic_pct
            })
            
            # Update model status
            conn.execute(text("""
                UPDATE model_versions
                SET status = :status
                WHERE version_id = :vid
            """), {
                'vid': version_id,
                'status': 'production' if mode == 'live' else 'shadow'
            })
        
        return deployment_id
    
    def log_prediction(self, version_id: uuid.UUID, tenant_id: uuid.UUID, 
                      storm_id: uuid.UUID, property_id: uuid.UUID, 
                      prediction: float, features: Dict = None):
        """Log a model prediction for auditing."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO model_predictions 
                (version_id, tenant_id, storm_id, property_id, prediction, features)
                VALUES (:vid, :tid, :sid, :pid, :pred, :features)
            """), {
                'vid': version_id,
                'tid': tenant_id,
                'sid': storm_id,
                'pid': property_id,
                'pred': prediction,
                'features': json.dumps(features) if features else None
            })
    
    def get_active_model(self, model_name: str, environment: str = 'production') -> Optional[Dict]:
        """Get currently active model version."""
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    mv.version_id,
                    mv.model_name,
                    mv.version,
                    mv.model_type,
                    mv.metrics,
                    md.mode,
                    md.traffic_pct,
                    md.deployed_at
                FROM model_versions mv
                JOIN model_deployments md ON mv.version_id = md.version_id
                WHERE mv.model_name = :name
                  AND md.environment = :env
                  AND md.retired_at IS NULL
                ORDER BY md.deployed_at DESC
                LIMIT 1
            """), {'name': model_name, 'env': environment}).fetchone()
            
            if result:
                return {
                    'version_id': str(result[0]),
                    'model_name': result[1],
                    'version': result[2],
                    'model_type': result[3],
                    'metrics': json.loads(result[4]) if result[4] else {},
                    'mode': result[5],
                    'traffic_pct': result[6],
                    'deployed_at': result[7].isoformat()
                }
        
        return None
    
    def compare_models(self, version_id_a: uuid.UUID, version_id_b: uuid.UUID) -> Dict:
        """Compare two model versions."""
        
        with self.engine.connect() as conn:
            models = conn.execute(text("""
                SELECT version_id, model_name, version, metrics
                FROM model_versions
                WHERE version_id IN (:vid_a, :vid_b)
            """), {'vid_a': version_id_a, 'vid_b': version_id_b}).fetchall()
        
        if len(models) != 2:
            return {'error': 'One or both models not found'}
        
        model_a = {
            'version_id': str(models[0][0]),
            'version': models[0][2],
            'metrics': json.loads(models[0][3]) if models[0][3] else {}
        }
        
        model_b = {
            'version_id': str(models[1][0]),
            'version': models[1][2],
            'metrics': json.loads(models[1][3]) if models[1][3] else {}
        }
        
        # Compare metrics
        comparison = {}
        for metric in set(list(model_a['metrics'].keys()) + list(model_b['metrics'].keys())):
            val_a = model_a['metrics'].get(metric)
            val_b = model_b['metrics'].get(metric)
            
            if val_a is not None and val_b is not None:
                diff = val_b - val_a
                comparison[metric] = {
                    'model_a': val_a,
                    'model_b': val_b,
                    'diff': diff,
                    'pct_change': (diff / val_a * 100) if val_a != 0 else 0
                }
        
        return {
            'model_a': model_a,
            'model_b': model_b,
            'comparison': comparison
        }
    
    def get_model_performance(self, version_id: uuid.UUID, days: int = 7) -> Dict:
        """Get model performance metrics."""
        
        with self.engine.connect() as conn:
            # Get prediction count
            pred_count = conn.execute(text("""
                SELECT COUNT(*) 
                FROM model_predictions
                WHERE version_id = :vid
                  AND timestamp > NOW() - INTERVAL ':days days'
            """), {'vid': version_id, 'days': days}).scalar()
            
            # Get prediction distribution
            dist = conn.execute(text("""
                SELECT 
                    AVG(prediction) as mean,
                    STDDEV(prediction) as stddev,
                    MIN(prediction) as min,
                    MAX(prediction) as max
                FROM model_predictions
                WHERE version_id = :vid
                  AND timestamp > NOW() - INTERVAL ':days days'
            """), {'vid': version_id, 'days': days}).fetchone()
        
        return {
            'version_id': str(version_id),
            'period_days': days,
            'prediction_count': pred_count,
            'distribution': {
                'mean': float(dist[0]) if dist[0] else None,
                'stddev': float(dist[1]) if dist[1] else None,
                'min': float(dist[2]) if dist[2] else None,
                'max': float(dist[3]) if dist[3] else None
            }
        }


if __name__ == '__main__':
    print("=" * 60)
    print("MODEL REGISTRY - SETUP & TEST")
    print("=" * 60)
    
    registry = ModelRegistry()
    
    # Register models
    print("\nRegistering models...")
    
    v1_id = registry.register_model(
        model_name='uplift',
        version='v1',
        model_type='xgboost',
        training_date=datetime(2026, 1, 1),
        metrics={'auc': 0.75, 'uplift_mean': 0.18},
        artifacts={'path': 's3://models/uplift_v1.pkl'}
    )
    print(f"✅ Registered uplift v1: {v1_id}")
    
    v2_id = registry.register_model(
        model_name='uplift',
        version='v2',
        model_type='xgboost',
        training_date=datetime(2026, 2, 1),
        metrics={'auc': 0.78, 'uplift_mean': 0.20},
        artifacts={'path': 's3://models/uplift_v2.pkl'}
    )
    print(f"✅ Registered uplift v2: {v2_id}")
    
    # Deploy v1 to production
    print("\nDeploying v1 to production...")
    deployment_id = registry.deploy_model(v1_id, environment='production', mode='live')
    print(f"✅ Deployed: {deployment_id}")
    
    # Deploy v2 in shadow mode
    print("\nDeploying v2 in shadow mode...")
    shadow_id = registry.deploy_model(v2_id, environment='production', mode='shadow', traffic_pct=0)
    print(f"✅ Shadow deployed: {shadow_id}")
    
    # Get active model
    print("\nActive model:")
    active = registry.get_active_model('uplift', 'production')
    print(f"  Version: {active['version']}")
    print(f"  Mode: {active['mode']}")
    print(f"  Metrics: {active['metrics']}")
    
    # Compare models
    print("\nComparing v1 vs v2:")
    comparison = registry.compare_models(v1_id, v2_id)
    for metric, values in comparison['comparison'].items():
        print(f"  {metric}:")
        print(f"    v1: {values['model_a']:.3f}")
        print(f"    v2: {values['model_b']:.3f}")
        print(f"    Change: {values['pct_change']:+.1f}%")
    
    print("\n✅ Model registry ready")
