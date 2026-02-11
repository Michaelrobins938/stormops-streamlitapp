"""
Policy Control Plane - Live Treatment Decision Engine
Wires moderate policy (uplift ≥ 15%) into control plane with full logging
"""

import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from typing import Dict
import json

class PolicyControlPlane:
    """Live policy engine with decision logging."""
    
    def __init__(self, policy_mode='moderate'):
        self.engine = create_engine('sqlite:///stormops_attribution.db')
        self.journeys_engine = create_engine('sqlite:///stormops_journeys.db')
        self.policy_mode = policy_mode
        
        # Policy thresholds
        self.thresholds = {
            'aggressive': 0.10,
            'moderate': 0.15,
            'conservative': 0.20
        }
        
        self.uplift_threshold = self.thresholds[policy_mode]
        self._init_logging_tables()
    
    def _init_logging_tables(self):
        """Create logging tables."""
        with self.engine.begin() as conn:
            # Policy decisions log
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS policy_decisions_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id TEXT,
                    event_id TEXT,
                    decision TEXT,
                    reason TEXT,
                    expected_uplift FLOAT,
                    uplift_band TEXT,
                    policy_mode TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Policy execution log
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS policy_executions (
                    execution_id TEXT PRIMARY KEY,
                    event_id TEXT,
                    policy_mode TEXT,
                    uplift_threshold FLOAT,
                    total_properties INTEGER,
                    treat_count INTEGER,
                    hold_count INTEGER,
                    avg_uplift_treated FLOAT,
                    avg_uplift_held FLOAT,
                    started_at DATETIME,
                    completed_at DATETIME
                )
            """))
            
            # Outcome tracking
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS policy_outcomes (
                    property_id TEXT,
                    event_id TEXT,
                    decision TEXT,
                    expected_uplift FLOAT,
                    actual_converted BOOLEAN,
                    conversion_value FLOAT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (property_id, event_id)
                )
            """))
    
    def apply_policy(self, event_id: str) -> Dict:
        """Apply policy to event and log all decisions."""
        
        execution_id = f"{event_id}_{self.policy_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now()
        
        # Load properties with uplift
        with self.engine.connect() as conn:
            properties = pd.read_sql(text("""
                SELECT 
                    lu.property_id,
                    lu.expected_uplift,
                    lu.next_best_action,
                    ea.experiment_id,
                    ea.variant,
                    ea.universal_control
                FROM lead_uplift lu
                LEFT JOIN experiment_assignments ea ON lu.property_id = ea.property_id
            """), conn)
        
        # Add ZIP from journeys DB
        with self.journeys_engine.connect() as conn:
            zips = pd.read_sql(text("""
                SELECT DISTINCT property_id, zip_code
                FROM customer_journeys
                WHERE event_id = :event_id
            """), conn, params={'event_id': event_id})
        
        properties = properties.merge(zips, on='property_id', how='inner')
        
        # Apply decision logic
        properties['decision'] = 'hold'
        properties['reason'] = 'default'
        properties['uplift_band'] = pd.cut(
            properties['expected_uplift'],
            bins=[0, 0.10, 0.15, 0.20, 1.0],
            labels=['<10%', '10-15%', '15-20%', '20%+']
        )
        
        # Rule 1: Universal control
        universal_mask = properties['universal_control'] == 1
        properties.loc[universal_mask, 'decision'] = 'hold'
        properties.loc[universal_mask, 'reason'] = 'universal_control'
        
        # Rule 2: RCT assignments
        experiment_mask = properties['experiment_id'].notna() & (properties['experiment_id'] != 'UNIVERSAL')
        properties.loc[experiment_mask & (properties['variant'] == 'treatment'), 'decision'] = 'treat'
        properties.loc[experiment_mask & (properties['variant'] == 'treatment'), 'reason'] = 'rct_treatment'
        properties.loc[experiment_mask & (properties['variant'] == 'control'), 'decision'] = 'hold'
        properties.loc[experiment_mask & (properties['variant'] == 'control'), 'reason'] = 'rct_control'
        
        # Rule 3: Uplift threshold
        unassigned_mask = ~universal_mask & ~experiment_mask
        high_uplift_mask = unassigned_mask & (properties['expected_uplift'] >= self.uplift_threshold)
        properties.loc[high_uplift_mask, 'decision'] = 'treat'
        properties.loc[high_uplift_mask, 'reason'] = f'uplift>={self.uplift_threshold}'
        
        # Log all decisions
        with self.engine.begin() as conn:
            for _, row in properties.iterrows():
                conn.execute(text("""
                    INSERT INTO policy_decisions_log
                    (property_id, event_id, decision, reason, expected_uplift, uplift_band, policy_mode)
                    VALUES (:pid, :eid, :decision, :reason, :uplift, :band, :mode)
                """), {
                    'pid': row['property_id'],
                    'eid': event_id,
                    'decision': row['decision'],
                    'reason': row['reason'],
                    'uplift': row['expected_uplift'],
                    'band': str(row['uplift_band']),
                    'mode': self.policy_mode
                })
            
            # Log execution summary
            treat_count = (properties['decision'] == 'treat').sum()
            hold_count = (properties['decision'] == 'hold').sum()
            
            conn.execute(text("""
                INSERT INTO policy_executions
                (execution_id, event_id, policy_mode, uplift_threshold, 
                 total_properties, treat_count, hold_count, 
                 avg_uplift_treated, avg_uplift_held, started_at, completed_at)
                VALUES (:eid, :event, :mode, :threshold, :total, :treat, :hold, 
                        :avg_treat, :avg_hold, :started, :completed)
            """), {
                'eid': execution_id,
                'event': event_id,
                'mode': self.policy_mode,
                'threshold': self.uplift_threshold,
                'total': len(properties),
                'treat': treat_count,
                'hold': hold_count,
                'avg_treat': properties[properties['decision']=='treat']['expected_uplift'].mean(),
                'avg_hold': properties[properties['decision']=='hold']['expected_uplift'].mean(),
                'started': started_at,
                'completed': datetime.now()
            })
        
        return {
            'execution_id': execution_id,
            'event_id': event_id,
            'policy_mode': self.policy_mode,
            'total': len(properties),
            'treat': treat_count,
            'hold': hold_count,
            'treat_pct': treat_count / len(properties) * 100,
            'decisions': properties
        }
    
    def log_outcome(self, property_id: str, event_id: str, converted: bool, value: float = 0):
        """Log actual outcome for a property."""
        
        with self.engine.begin() as conn:
            # Get original decision
            decision_row = conn.execute(text("""
                SELECT decision, expected_uplift
                FROM policy_decisions_log
                WHERE property_id = :pid AND event_id = :eid
                ORDER BY timestamp DESC
                LIMIT 1
            """), {'pid': property_id, 'eid': event_id}).fetchone()
            
            if decision_row:
                conn.execute(text("""
                    INSERT OR REPLACE INTO policy_outcomes
                    (property_id, event_id, decision, expected_uplift, 
                     actual_converted, conversion_value)
                    VALUES (:pid, :eid, :decision, :uplift, :converted, :value)
                """), {
                    'pid': property_id,
                    'eid': event_id,
                    'decision': decision_row[0],
                    'uplift': decision_row[1],
                    'converted': converted,
                    'value': value
                })
    
    def get_policy_performance(self, event_id: str) -> Dict:
        """Calculate actual vs predicted performance."""
        
        with self.engine.connect() as conn:
            outcomes = pd.read_sql(text("""
                SELECT 
                    decision,
                    COUNT(*) as n,
                    SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) as conversions,
                    AVG(CASE WHEN actual_converted THEN 1.0 ELSE 0.0 END) as conversion_rate,
                    AVG(expected_uplift) as avg_expected_uplift,
                    SUM(conversion_value) as total_value
                FROM policy_outcomes
                WHERE event_id = :eid
                GROUP BY decision
            """), conn, params={'eid': event_id})
        
        if len(outcomes) == 0:
            return {'error': 'No outcomes logged yet'}
        
        treat = outcomes[outcomes['decision'] == 'treat'].iloc[0] if 'treat' in outcomes['decision'].values else None
        hold = outcomes[outcomes['decision'] == 'hold'].iloc[0] if 'hold' in outcomes['decision'].values else None
        
        result = {
            'event_id': event_id,
            'policy_mode': self.policy_mode
        }
        
        if treat is not None:
            result['treatment'] = {
                'n': int(treat['n']),
                'conversions': int(treat['conversions']),
                'rate': float(treat['conversion_rate']),
                'expected_uplift': float(treat['avg_expected_uplift']),
                'total_value': float(treat['total_value'])
            }
        
        if hold is not None:
            result['control'] = {
                'n': int(hold['n']),
                'conversions': int(hold['conversions']),
                'rate': float(hold['conversion_rate']),
                'total_value': float(hold['total_value'])
            }
        
        if treat is not None and hold is not None:
            actual_lift = treat['conversion_rate'] - hold['conversion_rate']
            predicted_lift = treat['avg_expected_uplift']
            
            result['lift'] = {
                'actual_absolute': float(actual_lift),
                'actual_relative': float(actual_lift / hold['conversion_rate'] * 100) if hold['conversion_rate'] > 0 else 0,
                'predicted': float(predicted_lift),
                'prediction_error': float(actual_lift - predicted_lift)
            }
        
        return result


def switch_policy(new_mode: str, event_id: str):
    """Switch policy mode and re-apply."""
    
    plane = PolicyControlPlane(policy_mode=new_mode)
    result = plane.apply_policy(event_id)
    
    print(f"✅ Switched to {new_mode} policy")
    print(f"   Treat: {result['treat']} ({result['treat_pct']:.1f}%)")
    print(f"   Hold: {result['hold']}")
    
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("POLICY CONTROL PLANE - LIVE DEPLOYMENT")
    print("=" * 60)
    
    # Apply moderate policy (default)
    plane = PolicyControlPlane(policy_mode='moderate')
    result = plane.apply_policy('DFW_STORM_24')
    
    print(f"\n✅ Applied {result['policy_mode']} policy to {result['event_id']}")
    print(f"   Total: {result['total']}")
    print(f"   Treat: {result['treat']} ({result['treat_pct']:.1f}%)")
    print(f"   Hold: {result['hold']}")
    
    # Show decision breakdown
    decisions = result['decisions']
    print(f"\nDecision Breakdown:")
    for reason, count in decisions['reason'].value_counts().items():
        print(f"   {reason}: {count}")
    
    print(f"\nUplift Band Distribution:")
    for band, count in decisions['uplift_band'].value_counts().items():
        print(f"   {band}: {count}")
    
    # Simulate logging outcomes
    print(f"\n{'='*60}")
    print("SIMULATING OUTCOMES")
    print("=" * 60)
    
    import numpy as np
    np.random.seed(42)
    
    for _, row in decisions.head(100).iterrows():
        # Simulate conversion based on decision
        if row['decision'] == 'treat':
            converted = np.random.random() < 0.45
        else:
            converted = np.random.random() < 0.25
        
        value = 15000 if converted else 0
        plane.log_outcome(row['property_id'], 'DFW_STORM_24', converted, value)
    
    print("✅ Logged 100 outcomes")
    
    # Calculate performance
    perf = plane.get_policy_performance('DFW_STORM_24')
    
    print(f"\n{'='*60}")
    print("POLICY PERFORMANCE")
    print("=" * 60)
    
    if 'treatment' in perf:
        print(f"\nTreatment:")
        print(f"   N: {perf['treatment']['n']}")
        print(f"   Conversions: {perf['treatment']['conversions']}")
        print(f"   Rate: {perf['treatment']['rate']*100:.1f}%")
        print(f"   Value: ${perf['treatment']['total_value']:,.0f}")
    
    if 'control' in perf:
        print(f"\nControl:")
        print(f"   N: {perf['control']['n']}")
        print(f"   Conversions: {perf['control']['conversions']}")
        print(f"   Rate: {perf['control']['rate']*100:.1f}%")
        print(f"   Value: ${perf['control']['total_value']:,.0f}")
    
    if 'lift' in perf:
        print(f"\nLift:")
        print(f"   Actual: {perf['lift']['actual_absolute']*100:+.1f} pts ({perf['lift']['actual_relative']:+.1f}%)")
        print(f"   Predicted: {perf['lift']['predicted']*100:.1f}%")
        print(f"   Error: {perf['lift']['prediction_error']*100:+.1f} pts")
    
    print(f"\n✅ Policy control plane ready for live storm")
