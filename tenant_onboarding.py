"""
Tenant Onboarding - Self-service pilot signup
"""

from sqlalchemy import create_engine, text
import uuid
from datetime import datetime
from typing import Dict

class TenantOnboarding:
    """Handle new tenant signup and activation."""
    
    def __init__(self, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.engine = create_engine(db_url)
    
    def create_tenant(self, org_name: str, contact_email: str, contact_name: str, 
                     pilot_start_date: str = None) -> Dict:
        """Create new tenant for pilot."""
        
        tenant_id = uuid.uuid4()
        
        with self.engine.begin() as conn:
            # Create tenant
            conn.execute(text("""
                INSERT INTO tenants 
                (tenant_id, org_name, contact_email, contact_name, status, tier, pilot_start_date)
                VALUES (:tid, :org, :email, :name, 'active', 'pilot', :start_date)
            """), {
                'tid': tenant_id,
                'org': org_name,
                'email': contact_email,
                'name': contact_name,
                'start_date': pilot_start_date or datetime.now().isoformat()
            })
            
            # Create default user
            user_id = uuid.uuid4()
            conn.execute(text("""
                INSERT INTO users 
                (user_id, tenant_id, email, name, role)
                VALUES (:uid, :tid, :email, :name, 'admin')
            """), {
                'uid': user_id,
                'tid': tenant_id,
                'email': contact_email,
                'name': contact_name
            })
            
            # Log activation event
            conn.execute(text("""
                INSERT INTO tenant_usage 
                (tenant_id, event_type, event_data)
                VALUES (:tid, 'tenant_created', :data)
            """), {
                'tid': tenant_id,
                'data': f'{{"org": "{org_name}", "pilot": true}}'
            })
        
        return {
            'tenant_id': str(tenant_id),
            'org_name': org_name,
            'user_id': str(user_id),
            'status': 'active'
        }
    
    def import_sample_storm(self, tenant_id: uuid.UUID) -> Dict:
        """Import a sample storm for onboarding."""
        
        storm_id = uuid.uuid4()
        
        with self.engine.begin() as conn:
            conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': tenant_id})
            
            # Create sample storm
            conn.execute(text("""
                INSERT INTO storms 
                (storm_id, tenant_id, event_id, name, status, begin_datetime)
                VALUES (:sid, :tid, :eid, :name, 'active', NOW())
            """), {
                'sid': storm_id,
                'tid': tenant_id,
                'eid': 'ONBOARD-001',
                'name': 'Sample Storm - Onboarding'
            })
            
            # Create 5 sample properties
            for i in range(5):
                prop_id = uuid.uuid4()
                
                conn.execute(text("""
                    INSERT INTO properties 
                    (property_id, tenant_id, address, zip_code, latitude, longitude, external_id)
                    VALUES (:pid, :tid, :addr, :zip, :lat, :lon, :eid)
                """), {
                    'pid': prop_id,
                    'tid': tenant_id,
                    'addr': f'{100+i} Sample St',
                    'zip': '75001',
                    'lat': 33.0 + i*0.01,
                    'lon': -96.0 + i*0.01,
                    'eid': f'SAMPLE-{i+1}'
                })
                
                # Add treatment decision
                conn.execute(text("""
                    INSERT INTO policy_decisions_log 
                    (tenant_id, storm_id, property_id, decision, reason, expected_uplift, uplift_band, policy_mode)
                    VALUES (:tid, :sid, :pid, 'treat', 'Sample property', :uplift, 'medium', 'moderate')
                """), {
                    'tid': tenant_id,
                    'sid': storm_id,
                    'pid': prop_id,
                    'uplift': 0.15 + i*0.02
                })
            
            # Log activation
            conn.execute(text("""
                INSERT INTO tenant_usage 
                (tenant_id, event_type, event_data)
                VALUES (:tid, 'storm_imported', :data)
            """), {
                'tid': tenant_id,
                'data': f'{{"storm_id": "{storm_id}", "sample": true}}'
            })
        
        return {
            'storm_id': str(storm_id),
            'name': 'Sample Storm - Onboarding',
            'properties': 5
        }
    
    def get_activation_status(self, tenant_id: uuid.UUID) -> Dict:
        """Check tenant activation progress."""
        
        with self.engine.connect() as conn:
            # Check what they've done
            events = conn.execute(text("""
                SELECT event_type, created_at 
                FROM tenant_usage 
                WHERE tenant_id = :tid 
                ORDER BY created_at
            """), {'tid': tenant_id}).fetchall()
            
            event_types = {e[0] for e in events}
            
            # Check storms
            storms = conn.execute(text("""
                SELECT COUNT(*) FROM storms WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()[0]
            
            # Check routes
            routes = conn.execute(text("""
                SELECT COUNT(*) FROM routes WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()[0]
            
            # Check jobs
            jobs = conn.execute(text("""
                SELECT COUNT(*) FROM jobs WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()[0]
            
            completed_jobs = conn.execute(text("""
                SELECT COUNT(*) FROM jobs 
                WHERE tenant_id = :tid AND status = 'completed'
            """), {'tid': tenant_id}).fetchone()[0]
        
        return {
            'tenant_created': 'tenant_created' in event_types,
            'storm_imported': storms > 0,
            'routes_generated': routes > 0,
            'jobs_tracked': jobs > 0,
            'jobs_completed': completed_jobs > 0,
            'activation_score': sum([
                'tenant_created' in event_types,
                storms > 0,
                routes > 0,
                jobs > 0,
                completed_jobs > 0
            ]) / 5 * 100
        }
