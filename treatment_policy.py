"""
Control Plane Policy: Treat vs Hold-Out Decision Engine
Uses uplift, capacity constraints, and experiment assignments
"""

import pandas as pd
from sqlalchemy import create_engine, text
from typing import Dict, List

class TreatmentPolicy:
    """Decides which properties to treat based on uplift and constraints."""
    
    def __init__(self, uplift_threshold=0.15, capacity_limit=None):
        self.uplift_threshold = uplift_threshold
        self.capacity_limit = capacity_limit
        self.engine = create_engine('sqlite:///stormops_attribution.db')
    
    def get_treatment_decisions(self, event_id='DFW_STORM_24') -> pd.DataFrame:
        """Generate treatment decisions for all properties."""
        
        # Load properties with uplift scores
        with self.engine.connect() as conn:
            properties = pd.read_sql(text("""
                SELECT 
                    lu.property_id,
                    lu.next_best_action,
                    lu.expected_uplift,
                    ea.experiment_id,
                    ea.variant,
                    ea.universal_control
                FROM lead_uplift lu
                LEFT JOIN experiment_assignments ea ON lu.property_id = ea.property_id
            """), conn)
        
        # Decision logic
        properties['decision'] = 'hold'  # Default: hold out
        properties['reason'] = 'default'
        
        # Rule 1: Universal control always held out
        universal_mask = properties['universal_control'] == 1
        properties.loc[universal_mask, 'decision'] = 'hold'
        properties.loc[universal_mask, 'reason'] = 'universal_control'
        
        # Rule 2: Experiment assignments override (RCT)
        experiment_mask = properties['experiment_id'].notna() & (properties['experiment_id'] != 'UNIVERSAL')
        properties.loc[experiment_mask & (properties['variant'] == 'treatment'), 'decision'] = 'treat'
        properties.loc[experiment_mask & (properties['variant'] == 'treatment'), 'reason'] = 'rct_treatment'
        properties.loc[experiment_mask & (properties['variant'] == 'control'), 'decision'] = 'hold'
        properties.loc[experiment_mask & (properties['variant'] == 'control'), 'reason'] = 'rct_control'
        
        # Rule 3: For unassigned properties, treat if uplift > threshold
        unassigned_mask = ~universal_mask & ~experiment_mask
        high_uplift_mask = unassigned_mask & (properties['expected_uplift'] >= self.uplift_threshold)
        properties.loc[high_uplift_mask, 'decision'] = 'treat'
        properties.loc[high_uplift_mask, 'reason'] = f'uplift>={self.uplift_threshold}'
        
        # Rule 4: Capacity constraints (if specified)
        if self.capacity_limit:
            treat_candidates = properties[properties['decision'] == 'treat'].copy()
            
            if len(treat_candidates) > self.capacity_limit:
                # Sort by uplift, take top N
                treat_candidates = treat_candidates.nlargest(self.capacity_limit, 'expected_uplift')
                
                # Mark excess as capacity-limited
                properties.loc[
                    (properties['decision'] == 'treat') & 
                    (~properties['property_id'].isin(treat_candidates['property_id'])),
                    'decision'
                ] = 'hold'
                properties.loc[
                    (properties['reason'].str.contains('uplift')) & 
                    (properties['decision'] == 'hold'),
                    'reason'
                ] = 'capacity_limit'
        
        return properties
    
    def get_policy_summary(self, decisions: pd.DataFrame) -> Dict:
        """Summarize treatment policy decisions."""
        
        summary = {
            'total_properties': len(decisions),
            'treat': (decisions['decision'] == 'treat').sum(),
            'hold': (decisions['decision'] == 'hold').sum(),
            'treat_pct': (decisions['decision'] == 'treat').sum() / len(decisions) * 100,
            'reasons': decisions.groupby('reason')['decision'].value_counts().to_dict(),
            'avg_uplift_treated': decisions[decisions['decision'] == 'treat']['expected_uplift'].mean(),
            'avg_uplift_held': decisions[decisions['decision'] == 'hold']['expected_uplift'].mean()
        }
        
        return summary
    
    def apply_policy(self, decisions: pd.DataFrame):
        """Write policy decisions to database."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS treatment_decisions (
                    property_id TEXT PRIMARY KEY,
                    decision TEXT,
                    reason TEXT,
                    expected_uplift FLOAT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            for _, row in decisions.iterrows():
                conn.execute(text("""
                    INSERT OR REPLACE INTO treatment_decisions
                    (property_id, decision, reason, expected_uplift)
                    VALUES (:pid, :decision, :reason, :uplift)
                """), {
                    'pid': row['property_id'],
                    'decision': row['decision'],
                    'reason': row['reason'],
                    'uplift': row['expected_uplift']
                })
        
        print(f"✅ Applied policy to {len(decisions)} properties")


def simulate_storm_execution(decisions: pd.DataFrame) -> Dict:
    """Simulate storm execution with treatment decisions."""
    
    # Simulate conversions based on treatment
    import numpy as np
    np.random.seed(42)
    
    results = decisions.copy()
    
    # Treatment group: 45% conversion
    treat_mask = results['decision'] == 'treat'
    results.loc[treat_mask, 'converted'] = np.random.binomial(1, 0.45, treat_mask.sum())
    
    # Hold group: 25% conversion (baseline)
    hold_mask = results['decision'] == 'hold'
    results.loc[hold_mask, 'converted'] = np.random.binomial(1, 0.25, hold_mask.sum())
    
    # Calculate metrics
    treat_rate = results[treat_mask]['converted'].mean() if treat_mask.sum() > 0 else 0
    hold_rate = results[hold_mask]['converted'].mean() if hold_mask.sum() > 0 else 0
    
    # Revenue (assume $15k per conversion)
    treat_revenue = results[treat_mask]['converted'].sum() * 15000
    hold_revenue = results[hold_mask]['converted'].sum() * 15000
    
    # Costs (assume $50/property treated)
    treat_cost = treat_mask.sum() * 50
    
    return {
        'treatment': {
            'n': treat_mask.sum(),
            'conversions': results[treat_mask]['converted'].sum(),
            'rate': treat_rate,
            'revenue': treat_revenue,
            'cost': treat_cost,
            'roi': (treat_revenue - treat_cost) / treat_cost if treat_cost > 0 else 0
        },
        'control': {
            'n': hold_mask.sum(),
            'conversions': results[hold_mask]['converted'].sum(),
            'rate': hold_rate,
            'revenue': hold_revenue
        },
        'lift': {
            'absolute': treat_rate - hold_rate,
            'relative': (treat_rate - hold_rate) / hold_rate * 100 if hold_rate > 0 else 0,
            'incremental_revenue': treat_revenue - (treat_mask.sum() * hold_rate * 15000),
            'incremental_roi': ((treat_revenue - treat_cost) - (treat_mask.sum() * hold_rate * 15000)) / treat_cost if treat_cost > 0 else 0
        }
    }


if __name__ == '__main__':
    print("=" * 60)
    print("CONTROL PLANE POLICY: TREAT VS HOLD-OUT")
    print("=" * 60)
    
    # Test different policy configurations
    configs = [
        {'uplift_threshold': 0.10, 'capacity_limit': None, 'name': 'Aggressive (uplift ≥ 10%)'},
        {'uplift_threshold': 0.15, 'capacity_limit': None, 'name': 'Moderate (uplift ≥ 15%)'},
        {'uplift_threshold': 0.20, 'capacity_limit': None, 'name': 'Conservative (uplift ≥ 20%)'},
        {'uplift_threshold': 0.15, 'capacity_limit': 2000, 'name': 'Capacity-Limited (2000 max)'}
    ]
    
    for config in configs:
        print(f"\n{'='*60}")
        print(f"POLICY: {config['name']}")
        print("=" * 60)
        
        policy = TreatmentPolicy(
            uplift_threshold=config['uplift_threshold'],
            capacity_limit=config['capacity_limit']
        )
        
        # Get decisions
        decisions = policy.get_treatment_decisions()
        
        # Summary
        summary = policy.get_policy_summary(decisions)
        
        print(f"\nDecisions:")
        print(f"  Treat: {summary['treat']} ({summary['treat_pct']:.1f}%)")
        print(f"  Hold: {summary['hold']} ({100-summary['treat_pct']:.1f}%)")
        
        print(f"\nReasons:")
        for reason, count in sorted(decisions['reason'].value_counts().items()):
            print(f"  {reason}: {count}")
        
        print(f"\nUplift:")
        print(f"  Avg treated: {summary['avg_uplift_treated']:.3f}")
        print(f"  Avg held: {summary['avg_uplift_held']:.3f}")
        
        # Simulate execution
        results = simulate_storm_execution(decisions)
        
        print(f"\nSimulated Results:")
        print(f"  Treatment: {results['treatment']['rate']*100:.1f}% conversion ({results['treatment']['conversions']}/{results['treatment']['n']})")
        print(f"  Control: {results['control']['rate']*100:.1f}% conversion ({results['control']['conversions']}/{results['control']['n']})")
        print(f"  Lift: {results['lift']['absolute']*100:+.1f} pts ({results['lift']['relative']:+.1f}%)")
        print(f"  Incremental Revenue: ${results['lift']['incremental_revenue']:,.0f}")
        print(f"  Incremental ROI: {results['lift']['incremental_roi']*100:.1f}%")
    
    # Apply recommended policy
    print("\n" + "=" * 60)
    print("APPLYING RECOMMENDED POLICY")
    print("=" * 60)
    
    recommended = TreatmentPolicy(uplift_threshold=0.15, capacity_limit=None)
    decisions = recommended.get_treatment_decisions()
    recommended.apply_policy(decisions)
    
    print("\n✅ Policy applied to database")
    print("\nNext: Deploy on live storm and measure real lift")
