"""
E2E Test Suite for Multi-Tenant StormOps
Runs full storm cycle with tenant isolation
"""

import pytest
import uuid
from sqlalchemy import create_engine, text
from tenant_manager import TenantManager, TenantContext
from migrate_to_postgres import StormOpsMigration
from observability import DataObservability
import os

# Test DB URL
TEST_DB_URL = os.getenv('TEST_DATABASE_URL', 'postgresql://stormops:password@localhost:5432/stormops_test')

class TestMultiTenantStormOps:
    """E2E tests for multi-tenant storm operations."""
    
    @pytest.fixture(scope='class')
    def setup_test_db(self):
        """Setup test database."""
        engine = create_engine(TEST_DB_URL)
        
        # Run schema
        with open('schema_postgres.sql', 'r') as f:
            schema = f.read()
        
        with engine.begin() as conn:
            conn.execute(text(schema))
        
        yield engine
        
        # Cleanup
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    
    @pytest.fixture
    def tenant_a(self, setup_test_db):
        """Create tenant A."""
        manager = TenantManager(TEST_DB_URL)
        tenant = manager.provision_tenant(
            org_name='Tenant A Roofing',
            tier='standard',
            admin_email='admin@tenanta.com'
        )
        return uuid.UUID(tenant['tenant_id'])
    
    @pytest.fixture
    def tenant_b(self, setup_test_db):
        """Create tenant B."""
        manager = TenantManager(TEST_DB_URL)
        tenant = manager.provision_tenant(
            org_name='Tenant B Roofing',
            tier='standard',
            admin_email='admin@tenantb.com'
        )
        return uuid.UUID(tenant['tenant_id'])
    
    def test_tenant_isolation(self, tenant_a, tenant_b):
        """Test that tenants cannot see each other's data."""
        
        engine = create_engine(TEST_DB_URL)
        
        # Create storm for tenant A
        storm_a_id = uuid.uuid4()
        with TenantContext(tenant_a, TEST_DB_URL) as conn:
            conn.execute(text("""
                INSERT INTO storms (storm_id, tenant_id, event_id, name)
                VALUES (:sid, :tid, 'STORM_A', 'Storm A')
            """), {'sid': storm_a_id, 'tid': tenant_a})
            conn.commit()
        
        # Create storm for tenant B
        storm_b_id = uuid.uuid4()
        with TenantContext(tenant_b, TEST_DB_URL) as conn:
            conn.execute(text("""
                INSERT INTO storms (storm_id, tenant_id, event_id, name)
                VALUES (:sid, :tid, 'STORM_B', 'Storm B')
            """), {'sid': storm_b_id, 'tid': tenant_b})
            conn.commit()
        
        # Tenant A should only see their storm
        with TenantContext(tenant_a, TEST_DB_URL) as conn:
            storms = conn.execute(text("SELECT COUNT(*) FROM storms")).scalar()
            assert storms == 1, "Tenant A should only see 1 storm"
        
        # Tenant B should only see their storm
        with TenantContext(tenant_b, TEST_DB_URL) as conn:
            storms = conn.execute(text("SELECT COUNT(*) FROM storms")).scalar()
            assert storms == 1, "Tenant B should only see 1 storm"
    
    def test_full_storm_cycle(self, tenant_a):
        """Test complete storm workflow for one tenant."""
        
        engine = create_engine(TEST_DB_URL)
        
        with TenantContext(tenant_a, TEST_DB_URL) as conn:
            # Create storm
            storm_id = uuid.uuid4()
            conn.execute(text("""
                INSERT INTO storms (storm_id, tenant_id, event_id, name, status)
                VALUES (:sid, :tid, 'TEST_STORM', 'Test Storm', 'active')
            """), {'sid': storm_id, 'tid': tenant_a})
            
            # Create properties
            prop_ids = []
            for i in range(10):
                prop_id = uuid.uuid4()
                prop_ids.append(prop_id)
                conn.execute(text("""
                    INSERT INTO properties (property_id, tenant_id, external_id, zip_code)
                    VALUES (:pid, :tid, :ext, '75034')
                """), {'pid': prop_id, 'tid': tenant_a, 'ext': f'PROP_{i}'})
            
            # Create uplift scores
            for prop_id in prop_ids:
                conn.execute(text("""
                    INSERT INTO lead_uplift 
                    (tenant_id, storm_id, property_id, expected_uplift, model_version)
                    VALUES (:tid, :sid, :pid, :uplift, 'v1')
                """), {
                    'tid': tenant_a,
                    'sid': storm_id,
                    'pid': prop_id,
                    'uplift': 0.20
                })
            
            # Create journeys
            for prop_id in prop_ids:
                conn.execute(text("""
                    INSERT INTO customer_journeys 
                    (tenant_id, storm_id, property_id, channel, timestamp, converted)
                    VALUES (:tid, :sid, :pid, 'door_knock', NOW(), FALSE)
                """), {
                    'tid': tenant_a,
                    'sid': storm_id,
                    'pid': prop_id
                })
            
            conn.commit()
            
            # Verify
            prop_count = conn.execute(text("SELECT COUNT(*) FROM properties")).scalar()
            assert prop_count == 10, "Should have 10 properties"
            
            uplift_count = conn.execute(text("SELECT COUNT(*) FROM lead_uplift")).scalar()
            assert uplift_count == 10, "Should have 10 uplift scores"
            
            journey_count = conn.execute(text("SELECT COUNT(*) FROM customer_journeys")).scalar()
            assert journey_count == 10, "Should have 10 journeys"
    
    def test_observability(self, tenant_a):
        """Test observability checks."""
        
        # Create test data first
        self.test_full_storm_cycle(tenant_a)
        
        obs = DataObservability(tenant_a, TEST_DB_URL)
        
        # Check table health
        health = obs.check_table_health('properties')
        assert health['total_rows'] > 0, "Should have properties"
        
        # Check uplift distribution
        with TenantContext(tenant_a, TEST_DB_URL) as conn:
            storm_id = conn.execute(text("""
                SELECT storm_id FROM storms WHERE tenant_id = :tid LIMIT 1
            """), {'tid': tenant_a}).scalar()
        
        dist = obs.check_uplift_distribution(storm_id)
        assert dist['mean'] is not None, "Should have uplift mean"
        assert not dist['drift_detected'], "Should not detect drift for test data"


def run_e2e_tests():
    """Run E2E tests."""
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_e2e_tests()
