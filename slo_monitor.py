"""
SLO Definitions and Alert Manager
Service Level Objectives with automated alerting
"""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from typing import Dict, List
import json

# SLO Definitions
SLOS = {
    'journey_ingestion_latency': {
        'target': 5.0,  # seconds
        'threshold': 10.0,  # alert if > 10s
        'description': 'Time from event to journey record'
    },
    'attribution_freshness': {
        'target': 60.0,  # seconds
        'threshold': 300.0,  # alert if > 5 min
        'description': 'Time from journey to attribution update'
    },
    'model_scoring_latency': {
        'target': 1.0,  # seconds per property
        'threshold': 5.0,  # alert if > 5s
        'description': 'Uplift model scoring time'
    },
    'ui_error_rate': {
        'target': 0.001,  # 0.1%
        'threshold': 0.01,  # alert if > 1%
        'description': 'UI error rate'
    },
    'query_latency_p99': {
        'target': 5.0,  # seconds
        'threshold': 10.0,  # alert if > 10s
        'description': 'P99 query latency'
    },
    'data_quality_score': {
        'target': 0.99,  # 99%
        'threshold': 0.95,  # alert if < 95%
        'description': 'Data quality score'
    }
}

class SLOMonitor:
    """Monitor SLOs and trigger alerts."""
    
    def __init__(self, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.engine = create_engine(db_url)
        self._init_tables()
    
    def _init_tables(self):
        """Create SLO tracking tables."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS slo_measurements (
                    measurement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    slo_name TEXT NOT NULL,
                    value FLOAT NOT NULL,
                    target FLOAT NOT NULL,
                    threshold FLOAT NOT NULL,
                    breached BOOLEAN NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details JSONB,
                    resolved BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_slo_measurements_time 
                ON slo_measurements(timestamp)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_alerts_unresolved 
                ON alerts(resolved, created_at) WHERE NOT resolved
            """))
    
    def measure_slo(self, slo_name: str, value: float) -> Dict:
        """Measure an SLO and check for breach."""
        
        if slo_name not in SLOS:
            raise ValueError(f"Unknown SLO: {slo_name}")
        
        slo = SLOS[slo_name]
        breached = value > slo['threshold']
        
        # Log measurement
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO slo_measurements (slo_name, value, target, threshold, breached)
                VALUES (:name, :value, :target, :threshold, :breached)
            """), {
                'name': slo_name,
                'value': value,
                'target': slo['target'],
                'threshold': slo['threshold'],
                'breached': breached
            })
        
        # Trigger alert if breached
        if breached:
            self._trigger_alert(
                alert_type='slo_breach',
                severity='high' if value > slo['threshold'] * 2 else 'medium',
                message=f"SLO breach: {slo_name}",
                details={
                    'slo_name': slo_name,
                    'value': value,
                    'target': slo['target'],
                    'threshold': slo['threshold'],
                    'description': slo['description']
                }
            )
        
        return {
            'slo_name': slo_name,
            'value': value,
            'target': slo['target'],
            'threshold': slo['threshold'],
            'breached': breached
        }
    
    def _trigger_alert(self, alert_type: str, severity: str, message: str, details: Dict):
        """Trigger an alert."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO alerts (alert_type, severity, message, details)
                VALUES (:type, :severity, :message, :details)
            """), {
                'type': alert_type,
                'severity': severity,
                'message': message,
                'details': json.dumps(details)
            })
        
        print(f"🚨 ALERT [{severity.upper()}]: {message}")
        print(f"   Details: {json.dumps(details, indent=2)}")
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all unresolved alerts."""
        
        with self.engine.connect() as conn:
            alerts = conn.execute(text("""
                SELECT alert_id, alert_type, severity, message, details, created_at
                FROM alerts
                WHERE NOT resolved
                ORDER BY created_at DESC
            """)).fetchall()
        
        return [{
            'alert_id': str(a[0]),
            'alert_type': a[1],
            'severity': a[2],
            'message': a[3],
            'details': json.loads(a[4]) if a[4] else {},
            'created_at': a[5].isoformat()
        } for a in alerts]
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                UPDATE alerts
                SET resolved = TRUE, resolved_at = NOW()
                WHERE alert_id = :aid
            """), {'aid': alert_id})
    
    def get_slo_dashboard(self, hours: int = 24) -> Dict:
        """Get SLO dashboard for last N hours."""
        
        with self.engine.connect() as conn:
            measurements = conn.execute(text("""
                SELECT 
                    slo_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN breached THEN 1 ELSE 0 END) as breaches,
                    AVG(value) as avg_value,
                    MAX(value) as max_value
                FROM slo_measurements
                WHERE timestamp > NOW() - INTERVAL ':hours hours'
                GROUP BY slo_name
            """), {'hours': hours}).fetchall()
        
        dashboard = {}
        for m in measurements:
            slo = SLOS.get(m[0], {})
            dashboard[m[0]] = {
                'total_measurements': m[1],
                'breaches': m[2],
                'breach_rate': m[2] / m[1] if m[1] > 0 else 0,
                'avg_value': float(m[3]),
                'max_value': float(m[4]),
                'target': slo.get('target'),
                'threshold': slo.get('threshold'),
                'status': 'healthy' if m[2] == 0 else 'degraded'
            }
        
        return dashboard


# Runbooks for common alerts
RUNBOOKS = {
    'slo_breach_journey_ingestion_latency': {
        'title': 'Journey Ingestion Latency High',
        'steps': [
            '1. Check Kafka consumer lag',
            '2. Check database connection pool',
            '3. Check for slow queries (pg_stat_statements)',
            '4. Scale up ingestion workers if needed'
        ]
    },
    'slo_breach_model_scoring_latency': {
        'title': 'Model Scoring Latency High',
        'steps': [
            '1. Check model server CPU/memory',
            '2. Check batch size (reduce if needed)',
            '3. Check for model version issues',
            '4. Consider caching recent scores'
        ]
    },
    'uplift_drift': {
        'title': 'Uplift Distribution Drift',
        'steps': [
            '1. Check storm characteristics vs training data',
            '2. Verify feature engineering pipeline',
            '3. Check for data quality issues',
            '4. Consider retraining model',
            '5. Switch to shadow mode if drift severe'
        ]
    },
    'low_conversion_lift': {
        'title': 'Conversion Lift Below Target',
        'steps': [
            '1. Verify treatment policy is being followed',
            '2. Check for control group contamination',
            '3. Review experiment assignments',
            '4. Analyze by segment (ZIP, persona)',
            '5. Consider adjusting policy threshold'
        ]
    },
    'high_error_rate': {
        'title': 'High Error Rate',
        'steps': [
            '1. Check application logs',
            '2. Check database connectivity',
            '3. Check for recent deployments',
            '4. Roll back if needed',
            '5. Scale up if load-related'
        ]
    }
}


def get_runbook(alert_type: str) -> Dict:
    """Get runbook for alert type."""
    return RUNBOOKS.get(f"slo_breach_{alert_type}", RUNBOOKS.get(alert_type, {
        'title': 'Unknown Alert',
        'steps': ['1. Check logs', '2. Contact on-call engineer']
    }))


if __name__ == '__main__':
    print("=" * 60)
    print("SLO MONITOR - SETUP & TEST")
    print("=" * 60)
    
    monitor = SLOMonitor()
    
    # Test measurements
    print("\nTesting SLO measurements...")
    
    # Good measurement
    result = monitor.measure_slo('journey_ingestion_latency', 3.5)
    print(f"✅ {result['slo_name']}: {result['value']}s (target: {result['target']}s)")
    
    # Breach
    result = monitor.measure_slo('model_scoring_latency', 12.0)
    print(f"⚠️ {result['slo_name']}: {result['value']}s (threshold: {result['threshold']}s)")
    
    # Get active alerts
    print("\nActive alerts:")
    alerts = monitor.get_active_alerts()
    for alert in alerts:
        print(f"  [{alert['severity'].upper()}] {alert['message']}")
        runbook = get_runbook(alert['details'].get('slo_name', ''))
        print(f"  Runbook: {runbook['title']}")
    
    # Get dashboard
    print("\nSLO Dashboard (last 24h):")
    dashboard = monitor.get_slo_dashboard(hours=24)
    for slo_name, metrics in dashboard.items():
        print(f"  {slo_name}:")
        print(f"    Status: {metrics['status']}")
        print(f"    Breaches: {metrics['breaches']}/{metrics['total_measurements']}")
        print(f"    Avg: {metrics['avg_value']:.2f} (target: {metrics['target']})")
    
    print("\n✅ SLO monitoring ready")
