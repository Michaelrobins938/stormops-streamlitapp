"""
Data Observability & Monitoring
Tracks data quality, drift, and system health
"""

from sqlalchemy import create_engine, text
from typing import Dict, List, Optional
import pandas as pd
import uuid
from datetime import datetime, timedelta
import json

class DataObservability:
    """Monitor data quality and drift."""
    
    def __init__(self, tenant_id: uuid.UUID, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.tenant_id = tenant_id
        self.engine = create_engine(db_url)
        
        # Set tenant context
        with self.engine.connect() as conn:
            conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': tenant_id})
            conn.commit()
    
    def check_table_health(self, table_name: str) -> Dict:
        """Check basic health metrics for a table."""
        
        with self.engine.connect() as conn:
            # Row count
            count = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE tenant_id = :tid
            """), {'tid': self.tenant_id}).scalar()
            
            # Recent rows (last 24h)
            recent = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE tenant_id = :tid
                  AND created_at > NOW() - INTERVAL '24 hours'
            """), {'tid': self.tenant_id}).scalar()
            
            # Null checks (if applicable)
            nulls = {}
            if table_name == 'lead_uplift':
                null_uplift = conn.execute(text("""
                    SELECT COUNT(*) FROM lead_uplift
                    WHERE tenant_id = :tid AND expected_uplift IS NULL
                """), {'tid': self.tenant_id}).scalar()
                nulls['expected_uplift'] = null_uplift
            
            return {
                'table': table_name,
                'total_rows': count,
                'recent_rows_24h': recent,
                'nulls': nulls,
                'checked_at': datetime.now().isoformat()
            }
    
    def check_uplift_distribution(self, storm_id: uuid.UUID) -> Dict:
        """Check uplift score distribution for drift."""
        
        with self.engine.connect() as conn:
            stats = conn.execute(text("""
                SELECT 
                    COUNT(*) as count,
                    AVG(expected_uplift) as mean,
                    STDDEV(expected_uplift) as stddev,
                    MIN(expected_uplift) as min,
                    MAX(expected_uplift) as max,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY expected_uplift) as p25,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY expected_uplift) as p50,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY expected_uplift) as p75
                FROM lead_uplift
                WHERE tenant_id = :tid AND storm_id = :sid
            """), {'tid': self.tenant_id, 'sid': storm_id}).fetchone()
            
            result = {
                'count': stats[0],
                'mean': float(stats[1]) if stats[1] else None,
                'stddev': float(stats[2]) if stats[2] else None,
                'min': float(stats[3]) if stats[3] else None,
                'max': float(stats[4]) if stats[4] else None,
                'p25': float(stats[5]) if stats[5] else None,
                'p50': float(stats[6]) if stats[6] else None,
                'p75': float(stats[7]) if stats[7] else None
            }
            
            # Check for drift (expected: mean ~0.20, stddev ~0.10)
            drift_detected = False
            if result['mean'] and (result['mean'] < 0.10 or result['mean'] > 0.30):
                drift_detected = True
            
            result['drift_detected'] = drift_detected
            result['checked_at'] = datetime.now().isoformat()
            
            return result
    
    def check_conversion_rates(self, storm_id: uuid.UUID) -> Dict:
        """Check conversion rates by decision."""
        
        with self.engine.connect() as conn:
            rates = conn.execute(text("""
                SELECT 
                    po.decision,
                    COUNT(*) as n,
                    SUM(CASE WHEN po.actual_converted THEN 1 ELSE 0 END) as conversions,
                    AVG(CASE WHEN po.actual_converted THEN 1.0 ELSE 0.0 END) as rate
                FROM policy_outcomes po
                WHERE po.tenant_id = :tid AND po.storm_id = :sid
                GROUP BY po.decision
            """), {'tid': self.tenant_id, 'sid': storm_id}).fetchall()
            
            result = {}
            for row in rates:
                result[row[0]] = {
                    'n': row[1],
                    'conversions': row[2],
                    'rate': float(row[3])
                }
            
            # Check for anomalies
            if 'treat' in result and 'hold' in result:
                lift = result['treat']['rate'] - result['hold']['rate']
                result['lift'] = lift
                result['anomaly'] = lift < 0.05  # Lift too low
            
            result['checked_at'] = datetime.now().isoformat()
            
            return result
    
    def log_metric(self, metric_name: str, metric_value: float, dimensions: Optional[Dict] = None):
        """Log a data quality metric."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO data_quality_metrics 
                (tenant_id, table_name, metric_type, metric_value, threshold_breached)
                VALUES (:tid, :table, :metric, :value, :breach)
            """), {
                'tid': self.tenant_id,
                'table': dimensions.get('table', 'unknown') if dimensions else 'unknown',
                'metric': metric_name,
                'value': metric_value,
                'breach': dimensions.get('breach', False) if dimensions else False
            })
    
    def get_health_dashboard(self, storm_id: uuid.UUID) -> Dict:
        """Get complete health dashboard."""
        
        dashboard = {
            'tenant_id': str(self.tenant_id),
            'storm_id': str(storm_id),
            'checked_at': datetime.now().isoformat()
        }
        
        # Table health
        dashboard['tables'] = {
            'properties': self.check_table_health('properties'),
            'journeys': self.check_table_health('customer_journeys'),
            'uplift': self.check_table_health('lead_uplift'),
            'policy_decisions': self.check_table_health('policy_decisions_log')
        }
        
        # Uplift distribution
        dashboard['uplift_distribution'] = self.check_uplift_distribution(storm_id)
        
        # Conversion rates
        dashboard['conversion_rates'] = self.check_conversion_rates(storm_id)
        
        # Overall health
        issues = []
        if dashboard['uplift_distribution'].get('drift_detected'):
            issues.append('Uplift distribution drift detected')
        if dashboard['conversion_rates'].get('anomaly'):
            issues.append('Conversion lift anomaly detected')
        
        dashboard['health_status'] = 'healthy' if len(issues) == 0 else 'degraded'
        dashboard['issues'] = issues
        
        return dashboard


class SystemMonitoring:
    """Monitor system-level metrics."""
    
    def __init__(self, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.engine = create_engine(db_url)
    
    def get_tenant_metrics(self, tenant_id: uuid.UUID, days: int = 7) -> Dict:
        """Get tenant usage metrics."""
        
        with self.engine.connect() as conn:
            # Total events
            events = conn.execute(text("""
                SELECT 
                    metric_name,
                    COUNT(*) as count,
                    SUM(metric_value) as total
                FROM tenant_usage
                WHERE tenant_id = :tid
                  AND timestamp > NOW() - INTERVAL ':days days'
                GROUP BY metric_name
            """), {'tid': tenant_id, 'days': days}).fetchall()
            
            # Storage
            storage = conn.execute(text("""
                SELECT 
                    'properties' as table_name,
                    COUNT(*) as row_count
                FROM properties
                WHERE tenant_id = :tid
                UNION ALL
                SELECT 'journeys', COUNT(*) FROM customer_journeys WHERE tenant_id = :tid
                UNION ALL
                SELECT 'uplift', COUNT(*) FROM lead_uplift WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchall()
            
            return {
                'tenant_id': str(tenant_id),
                'period_days': days,
                'events': {e[0]: {'count': e[1], 'total': e[2]} for e in events},
                'storage': {s[0]: s[1] for s in storage}
            }
    
    def get_system_health(self) -> Dict:
        """Get overall system health."""
        
        with self.engine.connect() as conn:
            # Active tenants
            active_tenants = conn.execute(text("""
                SELECT COUNT(*) FROM tenants WHERE status = 'active'
            """)).scalar()
            
            # Recent errors (would come from logs)
            recent_errors = 0  # Placeholder
            
            # DB size
            db_size = conn.execute(text("""
                SELECT pg_database_size(current_database())
            """)).scalar()
            
            return {
                'active_tenants': active_tenants,
                'recent_errors': recent_errors,
                'db_size_bytes': db_size,
                'status': 'healthy',
                'checked_at': datetime.now().isoformat()
            }


# Runbook for common issues
RUNBOOK = {
    'uplift_drift': {
        'symptom': 'Uplift mean < 0.10 or > 0.30',
        'actions': [
            '1. Check if new storm has different characteristics',
            '2. Verify feature engineering pipeline',
            '3. Check for data quality issues in input features',
            '4. Consider retraining model if drift persists'
        ]
    },
    'low_lift': {
        'symptom': 'Treatment vs control lift < 5 pts',
        'actions': [
            '1. Verify treatment policy is being followed',
            '2. Check for control contamination',
            '3. Review experiment assignments',
            '4. Analyze by segment (ZIP, persona) for heterogeneity'
        ]
    },
    'volume_drop': {
        'symptom': 'Recent rows < 10% of total',
        'actions': [
            '1. Check data ingestion pipeline',
            '2. Verify Kafka/Flink jobs are running',
            '3. Check for upstream data source issues',
            '4. Review error logs'
        ]
    }
}


if __name__ == '__main__':
    print("=" * 60)
    print("DATA OBSERVABILITY - HEALTH CHECK")
    print("=" * 60)
    
    # Test with a tenant
    tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')  # System tenant
    storm_id = uuid.uuid4()  # Would be real storm ID
    
    obs = DataObservability(tenant_id)
    
    # Check table health
    print("\nTable Health:")
    for table in ['properties', 'customer_journeys', 'lead_uplift']:
        health = obs.check_table_health(table)
        print(f"  {table}: {health['total_rows']} rows, {health['recent_rows_24h']} recent")
    
    # System monitoring
    print("\nSystem Health:")
    monitor = SystemMonitoring()
    system = monitor.get_system_health()
    print(f"  Active tenants: {system['active_tenants']}")
    print(f"  DB size: {system['db_size_bytes'] / 1024 / 1024:.1f} MB")
    print(f"  Status: {system['status']}")
    
    print("\n✅ Observability ready")
    print("\nRunbook available for:")
    for issue in RUNBOOK.keys():
        print(f"  - {issue}")
