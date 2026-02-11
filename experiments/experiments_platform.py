"""
Experiments Platform - First-class experiments with templates
Geo-split, holdout, creative/policy tests, model A/B
"""

from sqlalchemy import create_engine, text
from typing import Dict, List, Tuple
import uuid
from datetime import datetime
import numpy as np
from scipy import stats

EXPERIMENT_TEMPLATES = {
    'geo_split': {
        'description': 'Geographic holdout test',
        'assignment': 'by_zip',
        'variants': ['treatment', 'control']
    },
    'policy_test': {
        'description': 'Test treatment policy',
        'assignment': 'by_uplift_band',
        'variants': ['aggressive', 'moderate', 'conservative']
    },
    'model_ab': {
        'description': 'A/B test model versions',
        'assignment': 'random',
        'variants': ['model_a', 'model_b']
    },
    'creative_test': {
        'description': 'Test messaging/creative',
        'assignment': 'by_persona',
        'variants': ['creative_a', 'creative_b', 'creative_c']
    }
}

class ExperimentsPlatform:
    """First-class experiments platform."""
    
    def __init__(self, tenant_id: uuid.UUID, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.tenant_id = tenant_id
        self.engine = create_engine(db_url)
    
    def create_experiment(self, storm_id: uuid.UUID, template: str, config: Dict) -> uuid.UUID:
        """Create experiment from template."""
        
        if template not in EXPERIMENT_TEMPLATES:
            raise ValueError(f"Unknown template: {template}")
        
        template_config = EXPERIMENT_TEMPLATES[template]
        experiment_id = uuid.uuid4()
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO experiments 
                (experiment_id, tenant_id, storm_id, name, hypothesis, status)
                VALUES (:eid, :tid, :sid, :name, :hyp, 'running')
            """), {
                'eid': experiment_id,
                'tid': self.tenant_id,
                'sid': storm_id,
                'name': config.get('name', f"{template}_{datetime.now().strftime('%Y%m%d')}"),
                'hyp': template_config['description']
            })
        
        return experiment_id
    
    def assign_properties(self, experiment_id: uuid.UUID, properties: List[uuid.UUID], 
                         assignment_method: str = 'random'):
        """Assign properties to experiment variants."""
        
        with self.engine.begin() as conn:
            # Get experiment details
            exp = conn.execute(text("""
                SELECT name FROM experiments WHERE experiment_id = :eid
            """), {'eid': experiment_id}).fetchone()
            
            if not exp:
                raise ValueError(f"Experiment not found: {experiment_id}")
            
            # Assign based on method
            if assignment_method == 'random':
                # 50/50 split
                for prop_id in properties:
                    variant = 'treatment' if np.random.random() < 0.5 else 'control'
                    conn.execute(text("""
                        INSERT INTO experiment_assignments 
                        (tenant_id, experiment_id, property_id, variant)
                        VALUES (:tid, :eid, :pid, :variant)
                        ON CONFLICT (tenant_id, experiment_id, property_id) DO NOTHING
                    """), {
                        'tid': self.tenant_id,
                        'eid': experiment_id,
                        'pid': prop_id,
                        'variant': variant
                    })
            
            elif assignment_method == 'by_zip':
                # Assign entire ZIPs to treatment/control
                # (Would need ZIP data from properties table)
                pass
    
    def measure_lift(self, experiment_id: uuid.UUID) -> Dict:
        """Measure lift for experiment."""
        
        with self.engine.connect() as conn:
            # Get outcomes by variant
            results = conn.execute(text("""
                SELECT 
                    ea.variant,
                    COUNT(*) as n,
                    SUM(CASE WHEN po.actual_converted THEN 1 ELSE 0 END) as conversions,
                    AVG(CASE WHEN po.actual_converted THEN 1.0 ELSE 0.0 END) as rate
                FROM experiment_assignments ea
                LEFT JOIN policy_outcomes po ON ea.property_id = po.property_id
                WHERE ea.experiment_id = :eid
                GROUP BY ea.variant
            """), {'eid': experiment_id}).fetchall()
        
        metrics = {}
        for r in results:
            metrics[r[0]] = {
                'n': r[1],
                'conversions': r[2] or 0,
                'rate': float(r[3]) if r[3] else 0.0
            }
        
        # Calculate lift
        if 'treatment' in metrics and 'control' in metrics:
            treat_rate = metrics['treatment']['rate']
            control_rate = metrics['control']['rate']
            
            lift = {
                'absolute': treat_rate - control_rate,
                'relative': ((treat_rate - control_rate) / control_rate * 100) if control_rate > 0 else 0
            }
            
            # Confidence interval
            ci = self.get_confidence_interval(
                metrics['treatment']['n'],
                metrics['treatment']['conversions'],
                metrics['control']['n'],
                metrics['control']['conversions']
            )
            
            return {
                'treatment': metrics['treatment'],
                'control': metrics['control'],
                'lift': lift,
                'confidence_interval': ci
            }
        
        return {'error': 'Insufficient data'}
    
    def get_confidence_interval(self, n_treat: int, conv_treat: int, 
                               n_control: int, conv_control: int, 
                               confidence: float = 0.95) -> Dict:
        """Calculate confidence interval for lift."""
        
        if n_treat == 0 or n_control == 0:
            return {'error': 'Insufficient data'}
        
        p_treat = conv_treat / n_treat
        p_control = conv_control / n_control
        
        # Standard error of difference
        se = np.sqrt(p_treat * (1 - p_treat) / n_treat + p_control * (1 - p_control) / n_control)
        
        # Z-score for confidence level
        z = stats.norm.ppf((1 + confidence) / 2)
        
        # Confidence interval
        lift = p_treat - p_control
        margin = z * se
        
        return {
            'lift': lift,
            'lower': lift - margin,
            'upper': lift + margin,
            'confidence': confidence,
            'significant': (lift - margin) > 0  # Lower bound > 0
        }


if __name__ == '__main__':
    print("=" * 60)
    print("EXPERIMENTS PLATFORM - SETUP & TEST")
    print("=" * 60)
    
    tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
    platform = ExperimentsPlatform(tenant_id)
    
    # Create experiment
    print("\nCreating experiment...")
    storm_id = uuid.uuid4()
    experiment_id = platform.create_experiment(
        storm_id,
        'policy_test',
        {'name': 'Moderate vs Aggressive Policy Test'}
    )
    print(f"✅ Created: {experiment_id}")
    
    # Assign properties (simulated)
    print("\nAssigning properties...")
    properties = [uuid.uuid4() for _ in range(100)]
    platform.assign_properties(experiment_id, properties, 'random')
    print(f"✅ Assigned {len(properties)} properties")
    
    # Calculate confidence interval (example)
    print("\nConfidence interval example:")
    ci = platform.get_confidence_interval(
        n_treat=50, conv_treat=23,
        n_control=50, conv_control=12
    )
    print(f"  Lift: {ci['lift']*100:+.1f} pts")
    print(f"  95% CI: [{ci['lower']*100:.1f}, {ci['upper']*100:.1f}] pts")
    print(f"  Significant: {ci['significant']}")
    
    print("\n✅ Experiments platform ready")
