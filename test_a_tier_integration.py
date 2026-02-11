"""
Test A-tier leads integration
Validates that leads are correctly loaded and queryable
"""

import pickle
import os

BASE_DIR = os.path.dirname(__file__)
a_tier_path = os.path.join(BASE_DIR, 'outputs', 'a_tier_zones.pkl')

if os.path.exists(a_tier_path):
    with open(a_tier_path, 'rb') as f:
        zones = pickle.load(f)
    
    print(f"✅ Loaded {len(zones)} zones with A-tier leads\n")
    
    # Test query: Show A-tier leads with SII ≥ 90 in 75034
    target_zip = '75034.0'
    if target_zip in zones:
        zone = zones[target_zip]
        high_sii_leads = [l for l in zone.leads if l['sii_score'] >= 90]
        
        print(f"📍 ZIP {target_zip}:")
        print(f"  Total leads: {len(zone.leads)}")
        print(f"  SII ≥ 90: {len(high_sii_leads)}")
        print(f"  Avg impact index: {zone.impact_index:.1f}\n")
        
        if high_sii_leads:
            print("Top 3 leads:")
            for lead in sorted(high_sii_leads, key=lambda x: x['sii_score'], reverse=True)[:3]:
                print(f"  • {lead['address']}")
                print(f"    SII: {lead['sii_score']}, Persona: {lead['persona']}, Play: {lead['play']}")
    else:
        print(f"❌ No leads found for ZIP {target_zip}")
        print(f"Available ZIPs: {', '.join(sorted(zones.keys())[:10])}")
    
    # Persona distribution
    print("\n📊 Persona Distribution (all A-tier):")
    personas = {}
    for zone in zones.values():
        for lead in zone.leads:
            p = lead['persona']
            personas[p] = personas.get(p, 0) + 1
    
    for persona, count in sorted(personas.items(), key=lambda x: x[1], reverse=True):
        print(f"  {persona}: {count}")
    
    # Recommended plays
    print("\n🎯 Recommended Plays:")
    plays = {}
    for zone in zones.values():
        for lead in zone.leads:
            p = lead['play']
            plays[p] = plays.get(p, 0) + 1
    
    for play, count in sorted(plays.items(), key=lambda x: x[1], reverse=True):
        print(f"  {play}: {count}")
    
else:
    print(f"❌ A-tier zones file not found at {a_tier_path}")
    print("Run: python /home/forsythe/kirocli/kirocli/load_a_tier_to_ui.py")
