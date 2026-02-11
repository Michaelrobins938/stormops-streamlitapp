"""
Control Group Management
RCT holdouts + synthetic controls for proper causal inference
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sqlalchemy import create_engine, text
from datetime import datetime

class ControlGroupManager:
    """Manage treatment/control assignments for experiments."""
    
    def __init__(self):
        self.engine = create_engine('sqlite:///stormops_attribution.db')
        self._create_tables()
    
    def _create_tables(self):
        """Create control group tables."""
        with self.engine.begin() as conn:
            # Experiment definitions
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    name TEXT,
                    play_id TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    treatment_pct FLOAT,
                    status TEXT
                )
            """))
            
            # Property assignments
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS experiment_assignments (
                    property_id TEXT,
                    experiment_id TEXT,
                    variant TEXT,  -- 'treatment' or 'control'
                    assigned_date TIMESTAMP,
                    universal_control BOOLEAN DEFAULT 0,
                    propensity_score FLOAT,
                    matched_property_id TEXT,
                    PRIMARY KEY (property_id, experiment_id)
                )
            """))
    
    def create_rct_experiment(self, experiment_id: str, name: str, play_id: str, 
                             properties: pd.DataFrame, treatment_pct: float = 0.8):
        """Create RCT experiment with random treatment/control split."""
        
        # Random assignment
        np.random.seed(hash(experiment_id) % 2**32)
        properties['variant'] = np.random.choice(
            ['treatment', 'control'],
            size=len(properties),
            p=[treatment_pct, 1 - treatment_pct]
        )
        
        # Save experiment
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO experiments 
                (experiment_id, name, play_id, start_date, treatment_pct, status)
                VALUES (:eid, :name, :play, :start, :pct, 'active')
            """), {
                'eid': experiment_id,
                'name': name,
                'play': play_id,
                'start': datetime.now(),
                'pct': treatment_pct
            })
            
            # Save assignments
            for _, row in properties.iterrows():
                conn.execute(text("""
                    INSERT OR REPLACE INTO experiment_assignments
                    (property_id, experiment_id, variant, assigned_date)
                    VALUES (:pid, :eid, :variant, :date)
                """), {
                    'pid': row['property_id'],
                    'eid': experiment_id,
                    'variant': row['variant'],
                    'date': datetime.now()
                })
        
        treatment_count = (properties['variant'] == 'treatment').sum()
        control_count = (properties['variant'] == 'control').sum()
        
        print(f"✅ Created RCT experiment: {experiment_id}")
        print(f"   Treatment: {treatment_count} ({treatment_pct*100:.0f}%)")
        print(f"   Control: {control_count} ({(1-treatment_pct)*100:.0f}%)")
        
        return properties
    
    def create_universal_control(self, properties: pd.DataFrame, holdout_pct: float = 0.05):
        """Create universal control group (held out from all experiments)."""
        
        np.random.seed(42)
        properties['universal_control'] = np.random.random(len(properties)) < holdout_pct
        
        with self.engine.begin() as conn:
            for _, row in properties[properties['universal_control']].iterrows():
                conn.execute(text("""
                    INSERT OR REPLACE INTO experiment_assignments
                    (property_id, experiment_id, variant, universal_control, assigned_date)
                    VALUES (:pid, 'UNIVERSAL', 'control', 1, :date)
                """), {
                    'pid': row['property_id'],
                    'date': datetime.now()
                })
        
        universal_count = properties['universal_control'].sum()
        print(f"✅ Created universal control: {universal_count} properties ({holdout_pct*100:.0f}%)")
        
        return properties
    
    def create_synthetic_controls(self, treated: pd.DataFrame, pool: pd.DataFrame,
                                  match_features: list, n_matches: int = 1):
        """Create synthetic controls via propensity score matching."""
        
        # Combine treated and pool
        treated['_treated'] = 1
        pool['_treated'] = 0
        combined = pd.concat([treated, pool], ignore_index=True)
        
        # Calculate propensity scores
        X = combined[match_features].fillna(0)
        y = combined['_treated']
        
        model = LogisticRegression(random_state=42, max_iter=1000)
        model.fit(X, y)
        
        propensity_scores = model.predict_proba(X)[:, 1]
        combined['propensity_score'] = propensity_scores
        
        # Match treated to controls
        treated_df = combined[combined['_treated'] == 1].copy()
        control_df = combined[combined['_treated'] == 0].copy()
        
        # Nearest neighbor matching on propensity score
        nn = NearestNeighbors(n_neighbors=n_matches, metric='euclidean')
        nn.fit(control_df[['propensity_score']])
        
        matches = []
        for _, treated_row in treated_df.iterrows():
            distances, indices = nn.kneighbors([[treated_row['propensity_score']]])
            for idx in indices[0]:
                control_row = control_df.iloc[idx]
                matches.append({
                    'treated_property_id': treated_row['property_id'],
                    'control_property_id': control_row['property_id'],
                    'propensity_score': treated_row['propensity_score'],
                    'distance': distances[0][0]
                })
        
        matches_df = pd.DataFrame(matches)
        
        print(f"✅ Created synthetic controls: {len(matches)} matches")
        print(f"   Avg propensity score: {matches_df['propensity_score'].mean():.3f}")
        print(f"   Avg match distance: {matches_df['distance'].mean():.3f}")
        
        return matches_df
    
    def get_experiment_results(self, experiment_id: str):
        """Calculate treatment vs control results."""
        
        with self.engine.connect() as conn:
            # Get assignments
            assignments = pd.read_sql(text("""
                SELECT ea.property_id, ea.variant
                FROM experiment_assignments ea
                WHERE ea.experiment_id = :eid
            """), conn, params={'eid': experiment_id})
            
            # Get conversions from journeys
            engine_journeys = create_engine('sqlite:///stormops_journeys.db')
            with engine_journeys.connect() as jconn:
                conversions = pd.read_sql(text("""
                    SELECT property_id, MAX(CAST(converted AS INTEGER)) as converted
                    FROM customer_journeys
                    GROUP BY property_id
                """), jconn)
            
            # Merge
            results = assignments.merge(conversions, on='property_id', how='left')
            results['converted'] = results['converted'].fillna(0)
            
            # Calculate metrics
            treatment = results[results['variant'] == 'treatment']
            control = results[results['variant'] == 'control']
            
            treatment_rate = treatment['converted'].mean()
            control_rate = control['converted'].mean()
            uplift = treatment_rate - control_rate
            
            return {
                'experiment_id': experiment_id,
                'treatment_n': len(treatment),
                'control_n': len(control),
                'treatment_rate': treatment_rate,
                'control_rate': control_rate,
                'uplift': uplift,
                'uplift_pct': (uplift / control_rate * 100) if control_rate > 0 else 0
            }


if __name__ == '__main__':
    print("=" * 60)
    print("CONTROL GROUP SETUP")
    print("=" * 60)
    
    # Load A-tier leads
    leads = pd.read_csv('a_tier_leads.csv')
    
    manager = ControlGroupManager()
    
    # 1. Create universal control (5% holdout)
    print("\n[1/3] Creating Universal Control Group...")
    leads = manager.create_universal_control(leads, holdout_pct=0.05)
    
    # 2. Create RCT experiment for Financing_Aggressive play
    print("\n[2/3] Creating RCT Experiment...")
    eligible = leads[~leads['universal_control']].copy()
    financing_leads = eligible[eligible['recommended_play'] == 'Financing_Aggressive'].copy()
    
    if len(financing_leads) > 0:
        financing_leads = manager.create_rct_experiment(
            experiment_id='financing_aggressive_v1',
            name='Financing Aggressive Play Test',
            play_id='Financing_Aggressive',
            properties=financing_leads,
            treatment_pct=0.8
        )
    
    # 3. Create synthetic controls for past data
    print("\n[3/3] Creating Synthetic Controls...")
    
    # Simulate: treated = properties that got door_knock, pool = rest
    engine_journeys = create_engine('sqlite:///stormops_journeys.db')
    with engine_journeys.connect() as conn:
        door_knocks = pd.read_sql(text("""
            SELECT DISTINCT property_id
            FROM customer_journeys
            WHERE channel = 'door_knock'
        """), conn)
    
    treated = leads[leads['property_id'].isin(door_knocks['property_id'])].copy()
    pool = leads[~leads['property_id'].isin(door_knocks['property_id'])].copy()
    
    if len(treated) > 0 and len(pool) > 0:
        match_features = ['sii_score', 'risk_score', 'estimated_value', 'property_age']
        matches = manager.create_synthetic_controls(treated, pool, match_features, n_matches=1)
    
    # 4. Show experiment results
    print("\n" + "=" * 60)
    print("EXPERIMENT RESULTS")
    print("=" * 60)
    
    if len(financing_leads) > 0:
        results = manager.get_experiment_results('financing_aggressive_v1')
        print(f"\nExperiment: {results['experiment_id']}")
        print(f"  Treatment: {results['treatment_n']} properties, {results['treatment_rate']*100:.1f}% conversion")
        print(f"  Control: {results['control_n']} properties, {results['control_rate']*100:.1f}% conversion")
        print(f"  Uplift: {results['uplift']*100:.1f} pts ({results['uplift_pct']:+.1f}%)")
    
    print("\n" + "=" * 60)
    print("✅ Control groups configured")
    print("\nNext: Wire into uplift models and UI")
    print("=" * 60)
