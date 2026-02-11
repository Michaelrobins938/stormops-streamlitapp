
import os
import sys
import json

# Try imports and guide user if missing
try:
    from dotenv import load_dotenv
    import boto3
    import requests
except ImportError as e:
    print(f"\n❌ Dependency Missing: {e}")
    print("Please run: pip install boto3 requests python-dotenv")
    sys.exit(1)

# Load Env
load_dotenv()

# Ensure we can import roofing_ai
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.earth2_service import Earth2Service
from services.property_service import PropertyService
from services.crm_service import CRMService
from services.lead_scoring_service import ScoredLead

def run_smoke_test():
    print("🚀 Starting StormOps Lean Pilot Smoke Test...\n")

    # 1. Earth-2 Service (Open NWP Mode)
    print("--- 1. Testing Earth2Service (Open NWP) ---")
    try:
        e2 = Earth2Service(mode="open_nwp")
        storm_data = e2.get_storm_footprint(region="DFW", lookback="72h")
        print(f"✅ Earth-2 returned Storm Event: {storm_data.event_id}")
        print(f"   Target Zips: {storm_data.zips}")
        print(f"   Max Hail: {storm_data.max_hail} in")
    except Exception as e:
        print(f"❌ Earth-2 Failed: {e}")
        # Continue to test other services even if this one fails (e.g. AWS creds missing)
    
    # 2. Property Service (Live ATTOM)
    # Check for Key first
    attom_key = os.getenv("ATTOM_API_KEY")
    if not attom_key or "insert" in attom_key:
        print("\n⚠️ ATTOM_API_KEY not set or is generic. Skipping Property Service test.")
    else:
        print(f"\n--- 2. Testing PropertyService (Live ATTOM) ---")
        try:
            prop_svc = PropertyService(mode="live")
            # Use a SINGLE zip to save quota
            test_zips = ["76201"] 
            print(f"   Querying properties for: {test_zips}")
            
            properties = prop_svc.query_target_properties(test_zips, min_age_years=5)
            print(f"✅ PropertyService returned {len(properties)} records.")
            if properties:
                 print(f"   Sample: {properties[0]['address']} (Age: {properties[0]['roof_age']}yr)")
        except Exception as e:
            print(f"❌ PropertyService Failed: {e}")

    # 3. CRM Service (JobNimbus Integration)
    print("\n--- 3. Testing CRMService (JobNimbus Push) ---")
    try:
        crm = CRMService()
        if 'properties' not in locals() or not properties:
            print("⚠️ No leads available to push. Skipping CRM test.")
        else:
            # Create a ScoredLead
            p = properties[0]
            lead = ScoredLead(
                address=p["address"],
                zip_code=p["zip"],
                roof_age=p["roof_age"],
                score=0.95,
                tags=["SMOKE_TEST", "HIGH_VALUE"],
                confidence=0.99
            )
            print(f"   Pushing Lead: {lead.address}...")
            crm.push_lead(lead)
            print("✅ CRM Sequence Complete.")
            
    except Exception as e:
        print(f"❌ CRM Service Failed: {e}")

    print("\n🏁 Smoke Test Finished.")

if __name__ == "__main__":
    run_smoke_test()
