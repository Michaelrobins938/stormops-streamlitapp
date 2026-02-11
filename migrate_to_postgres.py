"""
SQLite to Postgres Migration
Migrates existing storm data to multi-tenant Postgres schema
"""

import pandas as pd
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime

class StormOpsMigration:
    """Migrate from SQLite to Postgres with tenanting."""
    
    def __init__(self, tenant_id: uuid.UUID, tenant_name: str):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        
        # Source DBs (SQLite)
        self.sqlite_attribution = create_engine('sqlite:///stormops_attribution.db')
        self.sqlite_journeys = create_engine('sqlite:///stormops_journeys.db')
        
        # Target DB (Postgres)
        self.postgres = create_engine('postgresql://stormops:password@localhost:5432/stormops')
    
    def migrate_all(self, event_id: str = 'DFW_STORM_24'):
        """Run full migration."""
        
        print(f"Migrating {event_id} to tenant {self.tenant_name}...")
        
        # Create storm
        storm_id = self.migrate_storm(event_id)
        print(f"✅ Storm: {storm_id}")
        
        # Migrate properties
        property_map = self.migrate_properties(event_id)
        print(f"✅ Properties: {len(property_map)}")
        
        # Migrate journeys
        journey_count = self.migrate_journeys(event_id, storm_id, property_map)
        print(f"✅ Journeys: {journey_count}")
        
        # Migrate uplift
        uplift_count = self.migrate_uplift(event_id, storm_id, property_map)
        print(f"✅ Uplift: {uplift_count}")
        
        # Migrate experiments
        exp_count = self.migrate_experiments(event_id, storm_id, property_map)
        print(f"✅ Experiments: {exp_count}")
        
        # Migrate policy decisions
        policy_count = self.migrate_policy_decisions(event_id, storm_id, property_map)
        print(f"✅ Policy decisions: {policy_count}")
        
        return {
            'storm_id': str(storm_id),
            'properties': len(property_map),
            'journeys': journey_count,
            'uplift': uplift_count,
            'experiments': exp_count,
            'policy_decisions': policy_count
        }
    
    def migrate_storm(self, event_id: str) -> uuid.UUID:
        """Create storm record."""
        
        storm_id = uuid.uuid4()
        
        with self.postgres.begin() as conn:
            conn.execute(text("""
                INSERT INTO storms (storm_id, tenant_id, event_id, name, status)
                VALUES (:sid, :tid, :eid, :name, 'completed')
            """), {
                'sid': storm_id,
                'tid': self.tenant_id,
                'eid': event_id,
                'name': event_id.replace('_', ' ').title()
            })
        
        return storm_id
    
    def migrate_properties(self, event_id: str) -> dict:
        """Migrate properties and return old_id -> new_uuid map."""
        
        # Load from journeys DB
        with self.sqlite_journeys.connect() as conn:
            props = pd.read_sql(f"""
                SELECT DISTINCT property_id, zip_code
                FROM customer_journeys
                WHERE event_id = '{event_id}'
            """, conn)
        
        property_map = {}
        
        with self.postgres.begin() as conn:
            for _, row in props.iterrows():
                new_id = uuid.uuid4()
                property_map[row['property_id']] = new_id
                
                conn.execute(text("""
                    INSERT INTO properties (property_id, tenant_id, external_id, zip_code)
                    VALUES (:pid, :tid, :ext_id, :zip)
                    ON CONFLICT (tenant_id, external_id) DO NOTHING
                """), {
                    'pid': new_id,
                    'tid': self.tenant_id,
                    'ext_id': row['property_id'],
                    'zip': row['zip_code']
                })
        
        return property_map
    
    def migrate_journeys(self, event_id: str, storm_id: uuid.UUID, property_map: dict) -> int:
        """Migrate customer journeys."""
        
        with self.sqlite_journeys.connect() as conn:
            journeys = pd.read_sql(f"""
                SELECT property_id, channel, play_id, timestamp, converted, conversion_value
                FROM customer_journeys
                WHERE event_id = '{event_id}'
            """, conn)
        
        count = 0
        with self.postgres.begin() as conn:
            for _, row in journeys.iterrows():
                if row['property_id'] in property_map:
                    conn.execute(text("""
                        INSERT INTO customer_journeys 
                        (tenant_id, storm_id, property_id, channel, play_id, timestamp, converted, conversion_value)
                        VALUES (:tid, :sid, :pid, :channel, :play, :ts, :conv, :value)
                    """), {
                        'tid': self.tenant_id,
                        'sid': storm_id,
                        'pid': property_map[row['property_id']],
                        'channel': row['channel'],
                        'play': row['play_id'],
                        'ts': row['timestamp'],
                        'conv': row['converted'],
                        'value': row['conversion_value']
                    })
                    count += 1
        
        return count
    
    def migrate_uplift(self, event_id: str, storm_id: uuid.UUID, property_map: dict) -> int:
        """Migrate uplift scores."""
        
        with self.sqlite_attribution.connect() as conn:
            uplift = pd.read_sql("""
                SELECT property_id, expected_uplift, next_best_action
                FROM lead_uplift
            """, conn)
        
        count = 0
        with self.postgres.begin() as conn:
            for _, row in uplift.iterrows():
                if row['property_id'] in property_map:
                    conn.execute(text("""
                        INSERT INTO lead_uplift 
                        (tenant_id, storm_id, property_id, expected_uplift, next_best_action, model_version)
                        VALUES (:tid, :sid, :pid, :uplift, :action, 'v1')
                        ON CONFLICT (tenant_id, storm_id, property_id) DO NOTHING
                    """), {
                        'tid': self.tenant_id,
                        'sid': storm_id,
                        'pid': property_map[row['property_id']],
                        'uplift': row['expected_uplift'],
                        'action': row['next_best_action']
                    })
                    count += 1
        
        return count
    
    def migrate_experiments(self, event_id: str, storm_id: uuid.UUID, property_map: dict) -> int:
        """Migrate experiments and assignments."""
        
        with self.sqlite_attribution.connect() as conn:
            experiments = pd.read_sql("""
                SELECT DISTINCT experiment_id, hypothesis
                FROM experiments
            """, conn)
            
            assignments = pd.read_sql("""
                SELECT experiment_id, property_id, variant, universal_control
                FROM experiment_assignments
            """, conn)
        
        exp_map = {}
        
        with self.postgres.begin() as conn:
            # Migrate experiments
            for _, exp in experiments.iterrows():
                new_exp_id = uuid.uuid4()
                exp_map[exp['experiment_id']] = new_exp_id
                
                conn.execute(text("""
                    INSERT INTO experiments (experiment_id, tenant_id, storm_id, name, hypothesis, status)
                    VALUES (:eid, :tid, :sid, :name, :hyp, 'completed')
                """), {
                    'eid': new_exp_id,
                    'tid': self.tenant_id,
                    'sid': storm_id,
                    'name': exp['experiment_id'],
                    'hyp': exp['hypothesis']
                })
            
            # Migrate assignments
            count = 0
            for _, asg in assignments.iterrows():
                if asg['property_id'] in property_map and asg['experiment_id'] in exp_map:
                    conn.execute(text("""
                        INSERT INTO experiment_assignments 
                        (tenant_id, experiment_id, property_id, variant, universal_control)
                        VALUES (:tid, :eid, :pid, :variant, :uc)
                        ON CONFLICT (tenant_id, experiment_id, property_id) DO NOTHING
                    """), {
                        'tid': self.tenant_id,
                        'eid': exp_map[asg['experiment_id']],
                        'pid': property_map[asg['property_id']],
                        'variant': asg['variant'],
                        'uc': asg['universal_control']
                    })
                    count += 1
        
        return count
    
    def migrate_policy_decisions(self, event_id: str, storm_id: uuid.UUID, property_map: dict) -> int:
        """Migrate policy decisions."""
        
        with self.sqlite_attribution.connect() as conn:
            decisions = pd.read_sql("""
                SELECT property_id, decision, reason, expected_uplift, timestamp
                FROM treatment_decisions
            """, conn)
        
        count = 0
        with self.postgres.begin() as conn:
            for _, row in decisions.iterrows():
                if row['property_id'] in property_map:
                    conn.execute(text("""
                        INSERT INTO policy_decisions_log 
                        (tenant_id, storm_id, property_id, decision, reason, expected_uplift, policy_mode, timestamp)
                        VALUES (:tid, :sid, :pid, :decision, :reason, :uplift, 'moderate', :ts)
                    """), {
                        'tid': self.tenant_id,
                        'sid': storm_id,
                        'pid': property_map[row['property_id']],
                        'decision': row['decision'],
                        'reason': row['reason'],
                        'uplift': row['expected_uplift'],
                        'ts': row['timestamp']
                    })
                    count += 1
        
        return count


if __name__ == '__main__':
    print("=" * 60)
    print("SQLITE → POSTGRES MIGRATION")
    print("=" * 60)
    
    # Create tenant first
    from tenant_manager import TenantManager
    
    manager = TenantManager()
    tenant = manager.provision_tenant(
        org_name='DFW Elite Roofing',
        tier='standard',
        admin_email='admin@dfwelite.com'
    )
    
    print(f"\n✅ Tenant created: {tenant['tenant_id']}")
    
    # Run migration
    tenant_id = uuid.UUID(tenant['tenant_id'])
    migration = StormOpsMigration(tenant_id, tenant['org_name'])
    
    result = migration.migrate_all('DFW_STORM_24')
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Storm ID: {result['storm_id']}")
    print(f"Properties: {result['properties']}")
    print(f"Journeys: {result['journeys']}")
    print(f"Uplift scores: {result['uplift']}")
    print(f"Experiments: {result['experiments']}")
    print(f"Policy decisions: {result['policy_decisions']}")
