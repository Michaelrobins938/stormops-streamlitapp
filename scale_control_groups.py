"""
Scale Control Groups to Full Footprint
4,200 roofs with stratified randomization
"""

import pandas as pd
import numpy as np
from control_groups import ControlGroupManager

def generate_full_footprint(n_properties=4200):
    """Generate full storm footprint (simulated for now)."""
    
    # Load A-tier as template
    a_tier = pd.read_csv('a_tier_leads.csv')
    
    # Replicate and vary to create 4,200 properties
    np.random.seed(42)
    
    full_footprint = []
    for i in range(n_properties):
        # Sample from A-tier template
        template = a_tier.sample(1).iloc[0]
        
        # Create new property with variation
        property_data = {
            'property_id': f'prop_{i:05d}',
            'address': f'{1000+i} Main St',
            'city': template['city'],
            'zip_code': np.random.choice(a_tier['zip_code'].dropna().unique()),
            'estimated_value': template['estimated_value'] * np.random.uniform(0.8, 1.2),
            'square_footage': template.get('square_footage', 2500) * np.random.uniform(0.8, 1.2),
            'property_age': int(template['property_age'] * np.random.uniform(0.8, 1.2)),
            'risk_score': template['risk_score'] * np.random.uniform(0.9, 1.1),
            'sii_score': template['sii_score'] * np.random.uniform(0.9, 1.1),
            'primary_persona': np.random.choice(a_tier['primary_persona'].unique()),
            'recommended_play': np.random.choice(a_tier['recommended_play'].unique()),
            'median_household_income': template['median_household_income'],
            'homeownership_rate': template.get('homeownership_rate', 50),
            'risk_tolerance': template.get('risk_tolerance', 50),
            'price_sensitivity': template.get('price_sensitivity', 50)
        }
        
        full_footprint.append(property_data)
    
    df = pd.DataFrame(full_footprint)
    
    # Add stratification variables
    df['sii_band'] = pd.cut(df['sii_score'], bins=[0, 70, 90, 110], labels=['Low', 'Med', 'High'])
    df['zip_code'] = df['zip_code'].astype(str)
    
    return df


def stratified_universal_control(df, holdout_pct=0.05):
    """Create stratified universal control (balanced across segments)."""
    
    # Stratify by ZIP, persona, and SII band
    strata = df.groupby(['zip_code', 'primary_persona', 'sii_band'])
    
    universal_control = []
    
    for name, group in strata:
        n_holdout = max(1, int(len(group) * holdout_pct))
        holdout_sample = group.sample(n=n_holdout, random_state=42)
        universal_control.append(holdout_sample)
    
    universal_df = pd.concat(universal_control, ignore_index=True)
    
    df['universal_control'] = df['property_id'].isin(universal_df['property_id'])
    
    print(f"✅ Stratified universal control: {len(universal_df)} properties ({holdout_pct*100:.0f}%)")
    print(f"   Across {len(strata)} strata (ZIP × Persona × SII)")
    
    return df


def create_large_scale_experiments(df, manager):
    """Create experiments with proper sample sizes."""
    
    # Exclude universal control
    eligible = df[~df['universal_control']].copy()
    
    experiments = []
    
    # Get play distribution
    play_counts = eligible['recommended_play'].value_counts()
    print(f"\nPlay distribution in eligible properties:")
    for play, count in play_counts.items():
        print(f"  {play}: {count}")
    
    # Create experiments for top 3 plays
    for play in play_counts.head(3).index:
        play_eligible = eligible[eligible['recommended_play'] == play].copy()
        
        if len(play_eligible) >= 150:
            # Sample up to 500 properties
            sample_size = min(500, len(play_eligible))
            play_sample = play_eligible.sample(n=sample_size, random_state=hash(play) % 2**32)
            
            exp_id = f"{play.lower().replace('_', '_')}_v2"
            
            play_sample = manager.create_rct_experiment(
                experiment_id=exp_id,
                name=f"{play} - Large Scale Test",
                play_id=play,
                properties=play_sample,
                treatment_pct=0.75  # 75/25 split for better power
            )
            experiments.append((exp_id, play_sample))
    
    return experiments


if __name__ == '__main__':
    print("=" * 60)
    print("SCALE CONTROL GROUPS TO 4,200 ROOFS")
    print("=" * 60)
    
    # Generate full footprint
    print("\n[1/4] Generating full footprint...")
    df = generate_full_footprint(n_properties=4200)
    print(f"✅ Generated {len(df)} properties")
    print(f"   ZIPs: {df['zip_code'].nunique()}")
    print(f"   Personas: {df['primary_persona'].nunique()}")
    print(f"   Plays: {df['recommended_play'].nunique()}")
    
    # Create stratified universal control
    print("\n[2/4] Creating stratified universal control...")
    df = stratified_universal_control(df, holdout_pct=0.05)
    
    # Save full footprint
    df.to_csv('full_footprint_4200.csv', index=False)
    print(f"✅ Saved to full_footprint_4200.csv")
    
    # Create large-scale experiments
    print("\n[3/4] Creating large-scale experiments...")
    manager = ControlGroupManager()
    
    # Save universal control
    universal = df[df['universal_control']].copy()
    for _, row in universal.iterrows():
        with manager.engine.begin() as conn:
            from sqlalchemy import text
            conn.execute(text("""
                INSERT OR REPLACE INTO experiment_assignments
                (property_id, experiment_id, variant, universal_control, assigned_date)
                VALUES (:pid, 'UNIVERSAL', 'control', 1, datetime('now'))
            """), {'pid': row['property_id']})
    
    experiments = create_large_scale_experiments(df, manager)
    
    # Create synthetic controls for remaining properties
    print("\n[4/4] Creating synthetic controls...")
    
    # Get all assigned properties
    assigned_ids = set()
    assigned_ids.update(df[df['universal_control']]['property_id'])
    for exp_id, exp_df in experiments:
        assigned_ids.update(exp_df['property_id'])
    
    # Remaining properties for synthetic matching
    remaining = df[~df['property_id'].isin(assigned_ids)].copy()
    
    if len(remaining) > 100:
        # Sample for synthetic control matching
        treated_sample = remaining.sample(n=min(500, len(remaining)//2), random_state=45)
        pool_sample = remaining[~remaining['property_id'].isin(treated_sample['property_id'])].sample(
            n=min(1000, len(remaining)//2), random_state=46
        )
        
        match_features = ['sii_score', 'risk_score', 'estimated_value', 'property_age']
        matches = manager.create_synthetic_controls(
            treated=treated_sample,
            pool=pool_sample,
            match_features=match_features,
            n_matches=1
        )
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Properties: {len(df)}")
    print(f"Universal Control: {df['universal_control'].sum()} ({df['universal_control'].sum()/len(df)*100:.1f}%)")
    print(f"RCT Experiments: {len(experiments)}")
    for exp_id, exp_df in experiments:
        treatment = (exp_df['variant'] == 'treatment').sum()
        control = (exp_df['variant'] == 'control').sum()
        print(f"  {exp_id}: {treatment} treatment, {control} control")
    print(f"Synthetic Controls: {len(matches) if 'matches' in locals() else 0} matches")
    
    print("\n✅ Control groups scaled to 4,200 roofs")
    print("\nNext: Retrain uplift models with proper controls")
