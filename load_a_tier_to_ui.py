"""
Load A-tier leads into StormOps UI
Minimal adapter: CSV → app state
"""

import pandas as pd
import sys
sys.path.append('/home/forsythe/earth2-forecast-wsl/hotspot_tool')

from state import Zone

def load_a_tier_to_zones(csv_path='/home/forsythe/kirocli/kirocli/a_tier_leads.csv'):
    """Convert A-tier CSV to Zone objects for StormOps UI."""
    
    df = pd.read_csv(csv_path)
    zones = {}
    
    # Group by ZIP
    for zip_code, group in df.groupby('zip_code'):
        zone = Zone(
            zip_code=str(zip_code),
            impact_index=group['sii_score'].mean(),
            roof_count=len(group),
            risk_level="High" if group['risk_score'].mean() >= 85 else "Medium"
        )
        
        # Add leads to zone
        zone.leads = []
        for _, row in group.iterrows():
            lead = {
                'property_id': row['property_id'],
                'address': row['address'],
                'city': row['city'],
                'zip_code': str(row['zip_code']),
                'estimated_value': row['estimated_value'],
                'sii_score': row['sii_score'],
                'risk_score': row['risk_score'],
                'persona': row['primary_persona'],
                'play': row['recommended_play'],
                'play_message': row['play_message'],
                'sla_hours': row['follow_up_sla_hours'],
                'tier': 'A'
            }
            zone.leads.append(lead)
        
        zones[str(zip_code)] = zone
    
    print(f"✅ Loaded {len(df)} A-tier leads across {len(zones)} ZIPs")
    for zip_code, zone in sorted(zones.items(), key=lambda x: x[1].impact_index, reverse=True)[:5]:
        print(f"  {zip_code}: {zone.roof_count} leads, avg SII={zone.impact_index:.1f}")
    
    return zones

if __name__ == '__main__':
    zones = load_a_tier_to_zones()
    
    # Save to pickle for app to load
    import pickle
    with open('/home/forsythe/earth2-forecast-wsl/hotspot_tool/outputs/a_tier_zones.pkl', 'wb') as f:
        pickle.dump(zones, f)
    
    print("\n✅ Saved to outputs/a_tier_zones.pkl")
    print("Add this to app.py to load on startup:")
    print("""
    # In app.py, after get_app_state():
    import pickle
    if os.path.exists('outputs/a_tier_zones.pkl'):
        with open('outputs/a_tier_zones.pkl', 'rb') as f:
            state.zones = pickle.load(f)
            state.mission.leads_generated = True
    """)
