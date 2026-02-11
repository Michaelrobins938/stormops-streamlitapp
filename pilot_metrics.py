"""
Pilot Metrics - Track success criteria for each pilot tenant
"""

from sqlalchemy import create_engine, text
from typing import Dict, List
import uuid
from datetime import datetime, timedelta

class PilotMetrics:
    """Track and report pilot success metrics."""
    
    def __init__(self, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.engine = create_engine(db_url)
        self._init_schema()
    
    def _init_schema(self):
        """Create pilot metrics tables."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pilot_goals (
                    goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    metric_name TEXT NOT NULL,
                    target_value FLOAT NOT NULL,
                    current_value FLOAT DEFAULT 0,
                    status TEXT DEFAULT 'in_progress',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
    
    def set_pilot_goals(self, tenant_id: uuid.UUID, goals: Dict[str, float]):
        """Set success criteria for pilot."""
        
        with self.engine.begin() as conn:
            for metric, target in goals.items():
                conn.execute(text("""
                    INSERT INTO pilot_goals (tenant_id, metric_name, target_value)
                    VALUES (:tid, :metric, :target)
                """), {'tid': tenant_id, 'metric': metric, 'target': target})
    
    def get_pilot_health(self, tenant_id: uuid.UUID) -> Dict:
        """Get comprehensive pilot health metrics."""
        
        with self.engine.connect() as conn:
            # Tenant info
            tenant = conn.execute(text("""
                SELECT org_name, pilot_start_date, tier
                FROM tenants WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()
            
            if not tenant:
                return {}
            
            # Days in pilot
            start_date = tenant[1]
            days_in_pilot = (datetime.now() - start_date).days if start_date else 0
            
            # Storms
            storms = conn.execute(text("""
                SELECT COUNT(*) FROM storms WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()[0]
            
            # Routes
            routes = conn.execute(text("""
                SELECT COUNT(*) FROM routes WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()[0]
            
            # Jobs
            total_jobs = conn.execute(text("""
                SELECT COUNT(*) FROM jobs WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()[0]
            
            completed_jobs = conn.execute(text("""
                SELECT COUNT(*) FROM jobs 
                WHERE tenant_id = :tid AND status = 'completed'
            """), {'tid': tenant_id}).fetchone()[0]
            
            # Outcomes
            outcomes = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) as converted,
                    AVG(conversion_value) as avg_value
                FROM policy_outcomes
                WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()
            
            conversion_rate = (outcomes[1] / outcomes[0] * 100) if outcomes[0] > 0 else 0
            avg_value = outcomes[2] or 0
            
            # Activity (last 7 days)
            recent_activity = conn.execute(text("""
                SELECT COUNT(*) FROM tenant_usage
                WHERE tenant_id = :tid 
                  AND created_at > NOW() - INTERVAL '7 days'
            """), {'tid': tenant_id}).fetchone()[0]
            
            # Goals
            goals = conn.execute(text("""
                SELECT metric_name, target_value, current_value, status
                FROM pilot_goals
                WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchall()
        
        return {
            'org_name': tenant[0],
            'days_in_pilot': days_in_pilot,
            'tier': tenant[2],
            'storms': storms,
            'routes': routes,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'completion_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            'conversion_rate': conversion_rate,
            'avg_claim_value': avg_value,
            'recent_activity': recent_activity,
            'goals': [{
                'metric': g[0],
                'target': g[1],
                'current': g[2],
                'status': g[3]
            } for g in goals],
            'health_score': self._calculate_health_score(
                days_in_pilot, storms, routes, completed_jobs, recent_activity
            )
        }
    
    def _calculate_health_score(self, days: int, storms: int, routes: int, 
                                completed_jobs: int, recent_activity: int) -> float:
        """Calculate overall pilot health score (0-100)."""
        
        score = 0
        
        # Activity score (40 points)
        if recent_activity > 10:
            score += 40
        elif recent_activity > 5:
            score += 25
        elif recent_activity > 0:
            score += 10
        
        # Usage score (40 points)
        if storms > 0:
            score += 10
        if routes > 0:
            score += 15
        if completed_jobs > 5:
            score += 15
        elif completed_jobs > 0:
            score += 10
        
        # Momentum score (20 points)
        if days > 0:
            jobs_per_day = completed_jobs / days
            if jobs_per_day > 2:
                score += 20
            elif jobs_per_day > 1:
                score += 15
            elif jobs_per_day > 0.5:
                score += 10
        
        return min(score, 100)
    
    def get_all_pilots(self) -> List[Dict]:
        """Get health metrics for all pilot tenants."""
        
        with self.engine.connect() as conn:
            tenants = conn.execute(text("""
                SELECT tenant_id FROM tenants 
                WHERE tier = 'pilot' AND status = 'active'
            """)).fetchall()
        
        return [self.get_pilot_health(uuid.UUID(str(t[0]))) for t in tenants]
    
    def update_goal_progress(self, tenant_id: uuid.UUID):
        """Update current values for all goals."""
        
        with self.engine.begin() as conn:
            goals = conn.execute(text("""
                SELECT goal_id, metric_name, target_value
                FROM pilot_goals WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchall()
            
            for goal in goals:
                goal_id, metric, target = goal
                current = self._get_metric_value(tenant_id, metric)
                
                status = 'achieved' if current >= target else 'in_progress'
                
                conn.execute(text("""
                    UPDATE pilot_goals
                    SET current_value = :current, status = :status
                    WHERE goal_id = :gid
                """), {'current': current, 'status': status, 'gid': goal_id})
    
    def _get_metric_value(self, tenant_id: uuid.UUID, metric: str) -> float:
        """Get current value for a metric."""
        
        with self.engine.connect() as conn:
            if metric == 'routes_per_storm':
                result = conn.execute(text("""
                    SELECT 
                        CAST(COUNT(r.route_id) AS FLOAT) / NULLIF(COUNT(DISTINCT r.storm_id), 0)
                    FROM routes r
                    WHERE r.tenant_id = :tid
                """), {'tid': tenant_id}).fetchone()
                return result[0] or 0
            
            elif metric == 'jobs_completed':
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM jobs
                    WHERE tenant_id = :tid AND status = 'completed'
                """), {'tid': tenant_id}).fetchone()
                return float(result[0])
            
            elif metric == 'conversion_rate':
                result = conn.execute(text("""
                    SELECT 
                        CAST(SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) AS FLOAT) / 
                        NULLIF(COUNT(*), 0) * 100
                    FROM policy_outcomes
                    WHERE tenant_id = :tid
                """), {'tid': tenant_id}).fetchone()
                return result[0] or 0
            
            elif metric == 'avg_claim_value':
                result = conn.execute(text("""
                    SELECT AVG(conversion_value)
                    FROM policy_outcomes
                    WHERE tenant_id = :tid AND actual_converted = true
                """), {'tid': tenant_id}).fetchone()
                return result[0] or 0
        
        return 0
