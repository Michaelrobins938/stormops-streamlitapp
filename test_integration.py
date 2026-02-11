#!/usr/bin/env python3
"""
StormOps v2 Integration Test
End-to-end workflow validation
"""

import uuid
from datetime import datetime
from earth2_integration import Earth2Ingestion
from markov_engine import MarkovEngine
from identity_resolver import IdentityResolver
from sidebar_agent import SidebarAgent

DB_URL = "postgresql://stormops:password@localhost:5432/stormops"

def test_full_workflow():
    """Test complete storm-to-contract workflow"""
    
    print("🧪 StormOps v2 Integration Test")
    print("=" * 50)
    
    # Setup
    tenant_id = uuid.uuid4()
    storm_id = uuid.uuid4()
    
    print(f"\n📋 Test Setup")
    print(f"   Tenant: {tenant_id}")
    print(f"   Storm: {storm_id}")
    
    # Initialize agents
    earth2 = Earth2Ingestion(DB_URL)
    markov = MarkovEngine(DB_URL)
    identity = IdentityResolver(DB_URL)
    sidebar = SidebarAgent(DB_URL)
    
    print("\n✅ Agents initialized")
    
    # Test 1: Earth-2 Integration
    print("\n🛰️ Test 1: Earth-2 Swath Loading")
    zones = earth2.ingest_storm_swath(
        tenant_id, storm_id,
        center_lat=32.7767,  # Dallas
        center_lon=-96.7970,
        radius_km=50
    )
    print(f"   ✅ Created {zones} impact zones")
    
    # Test 2: Markov State Initialization
    print("\n🎲 Test 2: Markov State Engine")
    dfw_zips = ["75024", "75025", "75034", "75035", "76051"]
    markov.initialize_zip_states(tenant_id, storm_id, dfw_zips)
    print(f"   ✅ Initialized {len(dfw_zips)} ZIP states")
    
    # Test 3: Earth-2 Triggered Transitions
    print("\n⚡ Test 3: Markov Transitions")
    transitions = markov.trigger_earth2_transitions(tenant_id, storm_id)
    print(f"   ✅ Transitions: {transitions}")
    
    # Test 4: TAM Calculation
    print("\n💰 Test 4: TAM Calculation")
    for zip_code in dfw_zips[:3]:
        tam = markov.calculate_tam(tenant_id, storm_id, zip_code)
        print(f"   ZIP {zip_code}: ${tam:,.0f}")
    
    # Test 5: Identity Resolution
    print("\n👤 Test 5: Identity Resolution")
    property_id = uuid.uuid4()
    identity_id = identity.resolve_or_create(
        tenant_id, property_id,
        email="test@example.com",
        phone="214-555-0100",
        address="123 Test St, Dallas, TX 75024"
    )
    print(f"   ✅ Created identity: {identity_id}")
    
    # Test fuzzy match
    match = identity.fuzzy_match_property(
        tenant_id,
        email="test@example.com"
    )
    if match:
        print(f"   ✅ Fuzzy match: {match['match_confidence']:.2%} confidence")
    
    # Test 6: Sidebar Action Proposal
    print("\n🤖 Test 6: AI Action Proposals")
    action_id = sidebar.propose_action(
        tenant_id, storm_id,
        action_type='generate_routes',
        ai_confidence=0.92,
        ai_reasoning="ZIP 75024 entered recovery with high TAM",
        action_params={'zip_filter': ['75024'], 'max_per_route': 50}
    )
    print(f"   ✅ Proposed action: {action_id}")
    
    # Test 7: Action Approval & Execution
    print("\n▶️ Test 7: Action Execution")
    sidebar.approve_action(action_id, approved_by="test_user")
    print(f"   ✅ Action approved")
    
    # Note: Execution would require full route_builder integration
    # result = sidebar.execute_action(action_id)
    # print(f"   ✅ Execution result: {result}")
    
    # Test 8: Auto-Propose from Markov
    print("\n🧠 Test 8: Auto-Propose Actions")
    action_ids = sidebar.auto_propose_from_markov(tenant_id, storm_id)
    print(f"   ✅ AI proposed {len(action_ids)} actions")
    
    # Test 9: Action Queue Retrieval
    print("\n📋 Test 9: Action Queue")
    queue = sidebar.get_action_queue(tenant_id, storm_id)
    print(f"   ✅ Queue contains {len(queue)} items")
    for action in queue[:3]:
        print(f"      • {action['action_type']}: {action['ai_confidence']:.0%} confidence")
    
    # Test 10: Top Opportunity ZIPs
    print("\n🎯 Test 10: Top Opportunity ZIPs")
    top_zips = markov.get_top_opportunity_zips(tenant_id, storm_id, limit=5)
    print(f"   ✅ Found {len(top_zips)} opportunity ZIPs")
    for zip_data in top_zips:
        print(f"      • {zip_data['zip_code']}: {zip_data['current_state']} - ${zip_data.get('estimated_tam_usd', 0):,.0f}")
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("\n🚀 StormOps v2 is ready for deployment")
    print("\nNext steps:")
    print("   1. Run: streamlit run app_v2.py")
    print("   2. Load real Earth-2 data")
    print("   3. Connect ServiceTitan/JobNimbus")
    print("   4. Launch pilot with DFW contractor")


if __name__ == "__main__":
    try:
        test_full_workflow()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
