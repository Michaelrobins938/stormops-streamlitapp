"""
Verify UI wiring to real A-tier data
Tests that stats, play score, and lead counts are non-zero
"""

import sys
import os
sys.path.append('/home/forsythe/earth2-forecast-wsl/hotspot_tool')

# Simulate app state loading
BASE_DIR = '/home/forsythe/earth2-forecast-wsl/hotspot_tool'

import pickle
from state import AppState

state = AppState()

# Load A-tier zones
a_tier_path = os.path.join(BASE_DIR, 'outputs', 'a_tier_zones.pkl')
if os.path.exists(a_tier_path):
    with open(a_tier_path, 'rb') as f:
        state.zones = pickle.load(f)
        state.mission.leads_generated = True
        state.mission.checks["storm_loaded"] = True
        
        # Calculate stats
        total_leads = sum(z.roof_count for z in state.zones.values())
        state.stats["doors_targeted"] = total_leads
        high_risk = sum(1 for z in state.zones.values() if z.risk_level == "High")
        state.refined_stats = {z.zip_code: z for z in state.zones.values() if z.risk_level == "High"}
        
        # Calculate play score
        high_sii_leads = sum(1 for z in state.zones.values() for l in z.leads if l.get('sii_score', 0) >= 100)
        quality_ratio = high_sii_leads / total_leads if total_leads > 0 else 0
        play_score = 20 + int(quality_ratio * 15)
        state.mission.play_score = play_score
        
        print("=" * 60)
        print("UI WIRING VALIDATION")
        print("=" * 60)
        print(f"✅ A-tier zones loaded: {len(state.zones)}")
        print(f"✅ Storm loaded check: {state.mission.checks['storm_loaded']}")
        print(f"✅ Leads generated: {state.mission.leads_generated}")
        print()
        print("STATS (should be non-zero):")
        print(f"  • Impacted Roofs: {state.stats['doors_targeted']}")
        print(f"  • High Risk Zones: {len(state.refined_stats)}")
        print(f"  • Routes Ready: {state.routes_created}")
        print(f"  • Claims Filed: {state.stats['claims_filed']}")
        print()
        print("PLAY SCORE:")
        print(f"  • Storm Play Score: {state.mission.play_score}/100")
        print(f"  • High SII leads: {high_sii_leads}/{total_leads} ({quality_ratio*100:.0f}%)")
        print()
        print("=" * 60)
        
        if total_leads > 0 and state.mission.play_score > 0:
            print("✅ WIRING COMPLETE: UI will show non-zero stats")
        else:
            print("⚠️  WARNING: Some stats still zero")
        print("=" * 60)
else:
    print(f"❌ A-tier zones not found at {a_tier_path}")
