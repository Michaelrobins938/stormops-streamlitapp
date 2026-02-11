"""
Tenant Lifecycle Manager
Handles provisioning, deactivation, and tenant context
"""

from sqlalchemy import create_engine, text
from typing import Dict, Optional
import uuid
from datetime import datetime
import os

class TenantManager:
    """Manages tenant lifecycle and context."""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv('DATABASE_URL', 'postgresql://stormops:password@localhost:5432/stormops')
        self.engine = create_engine(self.db_url)
    
    def provision_tenant(self, org_name: str, tier: str = 'standard', admin_email: str = None) -> Dict:
        """Provision a new tenant with defaults."""
        
        tenant_id = uuid.uuid4()
        
        with self.engine.begin() as conn:
            # Create tenant
            conn.execute(text("""
                INSERT INTO tenants (tenant_id, org_name, tier, status)
                VALUES (:tid, :org, :tier, 'active')
            """), {'tid': tenant_id, 'org': org_name, 'tier': tier})
            
            # Create admin user if provided
            if admin_email:
                conn.execute(text("""
                    INSERT INTO users (tenant_id, email, role, status)
                    VALUES (:tid, :email, 'admin', 'active')
                """), {'tid': tenant_id, 'email': admin_email})
            
            # Log provisioning
            conn.execute(text("""
                INSERT INTO tenant_usage (tenant_id, metric_name, metric_value, dimensions)
                VALUES (:tid, 'tenant_provisioned', 1, :dims)
            """), {
                'tid': tenant_id,
                'dims': {'org_name': org_name, 'tier': tier}
            })
        
        return {
            'tenant_id': str(tenant_id),
            'org_name': org_name,
            'tier': tier,
            'admin_email': admin_email,
            'status': 'active'
        }
    
    def set_context(self, tenant_id: uuid.UUID):
        """Set tenant context for RLS."""
        with self.engine.connect() as conn:
            conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': tenant_id})
            conn.commit()
    
    def get_tenant(self, tenant_id: uuid.UUID) -> Optional[Dict]:
        """Get tenant details."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tenant_id, org_name, status, tier, created_at
                FROM tenants
                WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchone()
            
            if result:
                return {
                    'tenant_id': str(result[0]),
                    'org_name': result[1],
                    'status': result[2],
                    'tier': result[3],
                    'created_at': result[4]
                }
        return None
    
    def suspend_tenant(self, tenant_id: uuid.UUID, reason: str = None):
        """Suspend a tenant."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                UPDATE tenants
                SET status = 'suspended', updated_at = NOW()
                WHERE tenant_id = :tid
            """), {'tid': tenant_id})
            
            conn.execute(text("""
                INSERT INTO tenant_usage (tenant_id, metric_name, metric_value, dimensions)
                VALUES (:tid, 'tenant_suspended', 1, :dims)
            """), {
                'tid': tenant_id,
                'dims': {'reason': reason}
            })
    
    def reactivate_tenant(self, tenant_id: uuid.UUID):
        """Reactivate a suspended tenant."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                UPDATE tenants
                SET status = 'active', updated_at = NOW()
                WHERE tenant_id = :tid
            """), {'tid': tenant_id})
    
    def export_tenant_data(self, tenant_id: uuid.UUID) -> Dict:
        """Export all tenant data for offboarding."""
        
        with self.engine.connect() as conn:
            # Set context
            conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': tenant_id})
            
            export = {
                'tenant_id': str(tenant_id),
                'exported_at': datetime.now().isoformat()
            }
            
            # Export storms
            storms = conn.execute(text("""
                SELECT storm_id, event_id, name, begin_datetime
                FROM storms
                WHERE tenant_id = :tid
            """), {'tid': tenant_id}).fetchall()
            export['storms'] = [dict(s._mapping) for s in storms]
            
            # Export properties count
            prop_count = conn.execute(text("""
                SELECT COUNT(*) FROM properties WHERE tenant_id = :tid
            """), {'tid': tenant_id}).scalar()
            export['properties_count'] = prop_count
            
            # Export journeys count
            journey_count = conn.execute(text("""
                SELECT COUNT(*) FROM customer_journeys WHERE tenant_id = :tid
            """), {'tid': tenant_id}).scalar()
            export['journeys_count'] = journey_count
            
            return export
    
    def get_tenant_usage(self, tenant_id: uuid.UUID, days: int = 30) -> Dict:
        """Get tenant usage metrics."""
        
        with self.engine.connect() as conn:
            metrics = conn.execute(text("""
                SELECT 
                    metric_name,
                    SUM(metric_value) as total,
                    COUNT(*) as count
                FROM tenant_usage
                WHERE tenant_id = :tid
                  AND timestamp > NOW() - INTERVAL ':days days'
                GROUP BY metric_name
            """), {'tid': tenant_id, 'days': days}).fetchall()
            
            return {m[0]: {'total': m[1], 'count': m[2]} for m in metrics}
    
    def list_tenants(self, status: Optional[str] = None) -> list:
        """List all tenants."""
        
        query = "SELECT tenant_id, org_name, status, tier, created_at FROM tenants"
        params = {}
        
        if status:
            query += " WHERE status = :status"
            params['status'] = status
        
        query += " ORDER BY created_at DESC"
        
        with self.engine.connect() as conn:
            results = conn.execute(text(query), params).fetchall()
            
            return [{
                'tenant_id': str(r[0]),
                'org_name': r[1],
                'status': r[2],
                'tier': r[3],
                'created_at': r[4]
            } for r in results]


class TenantContext:
    """Context manager for tenant-scoped operations."""
    
    def __init__(self, tenant_id: uuid.UUID, db_url: Optional[str] = None):
        self.tenant_id = tenant_id
        self.db_url = db_url or os.getenv('DATABASE_URL', 'postgresql://stormops:password@localhost:5432/stormops')
        self.engine = create_engine(self.db_url)
        self.conn = None
    
    def __enter__(self):
        self.conn = self.engine.connect()
        self.conn.execute(text("SELECT set_tenant_context(:tid)"), {'tid': self.tenant_id})
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("TENANT MANAGER - PROVISIONING TEST")
    print("=" * 60)
    
    manager = TenantManager()
    
    # Provision test tenant
    print("\nProvisioning tenant...")
    tenant = manager.provision_tenant(
        org_name='DFW Elite Roofing',
        tier='standard',
        admin_email='admin@dfwelite.com'
    )
    
    print(f"✅ Tenant provisioned:")
    print(f"   ID: {tenant['tenant_id']}")
    print(f"   Org: {tenant['org_name']}")
    print(f"   Tier: {tenant['tier']}")
    
    # Test context
    print("\nTesting tenant context...")
    tenant_id = uuid.UUID(tenant['tenant_id'])
    
    with TenantContext(tenant_id) as conn:
        result = conn.execute(text("SELECT current_tenant()")).scalar()
        print(f"✅ Context set: {result}")
    
    # List tenants
    print("\nListing all tenants...")
    tenants = manager.list_tenants()
    for t in tenants:
        print(f"   {t['org_name']} ({t['status']}) - {t['tenant_id']}")
    
    print("\n✅ Tenant manager ready")
