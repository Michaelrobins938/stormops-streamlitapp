#!/usr/bin/env python3
"""
Pilot Onboarding Script
Usage: python onboard_pilot.py "Company Name" "email@company.com" "Contact Name"
"""

import sys
from sqlalchemy import create_engine, text
import uuid

def onboard_pilot(org_name: str, email: str, contact_name: str):
    """Onboard a new pilot tenant with sample data."""
    
    engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')
    
    tenant_id = uuid.uuid4()
    storm_id = uuid.uuid4()
    
    print(f"\n🚀 Onboarding {org_name}...")
    
    with engine.begin() as conn:
        # 1. Create tenant
        conn.execute(text("""
            INSERT INTO tenants 
            (tenant_id, org_name, contact_email, contact_name, status, tier, pilot_start_date)
            VALUES (:tid, :org, :email, :name, 'active', 'pilot', NOW())
        """), {
            'tid': tenant_id,
            'org': org_name,
            'email': email,
            'name': contact_name
        })
        print(f"✓ Created tenant: {tenant_id}")
        
        # 2. Create admin user
        user_id = uuid.uuid4()
        conn.execute(text("""
            INSERT INTO users 
            (user_id, tenant_id, email, role)
            VALUES (:uid, :tid, :email, 'admin')
        """), {
            'uid': user_id,
            'tid': tenant_id,
            'email': email
        })
        print(f"✓ Created admin user: {email}")
        
        # 3. Set tenant context
        conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': tenant_id})
        
        # 4. Create sample storm
        conn.execute(text("""
            INSERT INTO storms 
            (storm_id, tenant_id, event_id, name, status, begin_datetime)
            VALUES (:sid, :tid, :eid, :name, 'active', NOW())
        """), {
            'sid': storm_id,
            'tid': tenant_id,
            'eid': 'PILOT-001',
            'name': f'{org_name} - Sample Storm'
        })
        print(f"✓ Created sample storm: {storm_id}")
        
        # 5. Create 10 sample properties with treatment decisions
        print("✓ Creating sample properties...")
        for i in range(10):
            prop_id = uuid.uuid4()
            
            conn.execute(text("""
                INSERT INTO properties 
                (property_id, tenant_id, address, zip_code, latitude, longitude, external_id)
                VALUES (:pid, :tid, :addr, :zip, :lat, :lon, :eid)
            """), {
                'pid': prop_id,
                'tid': tenant_id,
                'addr': f'{100+i} Sample Street',
                'zip': '75001' if i < 5 else '75002',
                'lat': 33.0 + i*0.01,
                'lon': -96.0 + i*0.01,
                'eid': f'PROP-{i+1:03d}'
            })
            
            # Add treatment decision
            conn.execute(text("""
                INSERT INTO policy_decisions_log 
                (tenant_id, storm_id, property_id, decision, reason, expected_uplift, uplift_band, policy_mode)
                VALUES (:tid, :sid, :pid, 'treat', 'High potential', :uplift, 'high', 'moderate')
            """), {
                'tid': tenant_id,
                'sid': storm_id,
                'pid': prop_id,
                'uplift': 0.15 + i*0.02
            })
        
        print(f"✓ Created 10 sample properties")
        
        # 6. Log onboarding event
        conn.execute(text("""
            INSERT INTO tenant_usage 
            (tenant_id, metric_name, metric_value)
            VALUES (:tid, 'pilot_onboarded', 1)
        """), {
            'tid': tenant_id
        })
    
    print(f"\n✅ Onboarding complete!")
    print(f"\nNext steps:")
    print(f"1. Send login link to {email}")
    print(f"2. Tenant ID: {tenant_id}")
    print(f"3. Sample Storm ID: {storm_id}")
    print(f"4. They can now generate routes and track jobs")
    print(f"\nView pilot dashboard: streamlit run pilot_dashboard.py")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python onboard_pilot.py 'Company Name' 'email@company.com' 'Contact Name'")
        sys.exit(1)
    
    onboard_pilot(sys.argv[1], sys.argv[2], sys.argv[3])
