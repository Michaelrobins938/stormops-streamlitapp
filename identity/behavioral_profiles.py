"""
Behavioral Profiles - Aggregated profiles keyed by identity_id
Journeys, plays, experiments, SII, uplift, claims, LTV
"""

from sqlalchemy import create_engine, text
from typing import Dict, Optional
import uuid
from datetime import datetime

class BehavioralProfileService:
    """Behavioral profiles for identities."""
    
    def __init__(self, tenant_id: uuid.UUID, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.tenant_id = tenant_id
        self.engine = create_engine(db_url)
        self._init_schema()
    
    def _init_schema(self):
        """Create profile tables."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS behavioral_profiles (
                    identity_id UUID PRIMARY KEY REFERENCES identities(identity_id),
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    total_storms INT DEFAULT 0,
                    total_conversions INT DEFAULT 0,
                    lifetime_value FLOAT DEFAULT 0,
                    avg_sii_score FLOAT,
                    avg_uplift FLOAT,
                    primary_channel TEXT,
                    segment TEXT,
                    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
    
    def get_profile(self, identity_id: uuid.UUID) -> Optional[Dict]:
        """Get behavioral profile for identity."""
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    identity_id,
                    total_storms,
                    total_conversions,
                    lifetime_value,
                    avg_sii_score,
                    avg_uplift,
                    primary_channel,
                    segment,
                    last_updated
                FROM behavioral_profiles
                WHERE identity_id = :iid
            """), {'iid': identity_id}).fetchone()
            
            if result:
                return {
                    'identity_id': str(result[0]),
                    'total_storms': result[1],
                    'total_conversions': result[2],
                    'lifetime_value': result[3],
                    'avg_sii_score': result[4],
                    'avg_uplift': result[5],
                    'primary_channel': result[6],
                    'segment': result[7],
                    'last_updated': result[8].isoformat()
                }
        
        return None
    
    def update_profile(self, identity_id: uuid.UUID, event: Dict):
        """Update profile based on event."""
        
        with self.engine.begin() as conn:
            # Get or create profile
            profile = self.get_profile(identity_id)
            
            if not profile:
                conn.execute(text("""
                    INSERT INTO behavioral_profiles (identity_id, tenant_id)
                    VALUES (:iid, :tid)
                """), {'iid': identity_id, 'tid': self.tenant_id})
                profile = {
                    'total_storms': 0,
                    'total_conversions': 0,
                    'lifetime_value': 0,
                    'avg_sii_score': None,
                    'avg_uplift': None,
                    'primary_channel': None,
                    'segment': None
                }
            
            # Update based on event type
            if event.get('type') == 'storm_participation':
                conn.execute(text("""
                    UPDATE behavioral_profiles
                    SET total_storms = total_storms + 1,
                        last_updated = NOW()
                    WHERE identity_id = :iid
                """), {'iid': identity_id})
            
            elif event.get('type') == 'conversion':
                value = event.get('value', 0)
                conn.execute(text("""
                    UPDATE behavioral_profiles
                    SET total_conversions = total_conversions + 1,
                        lifetime_value = lifetime_value + :value,
                        last_updated = NOW()
                    WHERE identity_id = :iid
                """), {'iid': identity_id, 'value': value})
            
            elif event.get('type') == 'sii_score':
                score = event.get('score')
                conn.execute(text("""
                    UPDATE behavioral_profiles
                    SET avg_sii_score = COALESCE(
                        (avg_sii_score * total_storms + :score) / (total_storms + 1),
                        :score
                    ),
                    last_updated = NOW()
                    WHERE identity_id = :iid
                """), {'iid': identity_id, 'score': score})
            
            elif event.get('type') == 'uplift_score':
                uplift = event.get('uplift')
                conn.execute(text("""
                    UPDATE behavioral_profiles
                    SET avg_uplift = COALESCE(
                        (avg_uplift * total_storms + :uplift) / (total_storms + 1),
                        :uplift
                    ),
                    last_updated = NOW()
                    WHERE identity_id = :iid
                """), {'iid': identity_id, 'uplift': uplift})
            
            elif event.get('type') == 'channel_interaction':
                channel = event.get('channel')
                # Update primary channel (most frequent)
                conn.execute(text("""
                    UPDATE behavioral_profiles
                    SET primary_channel = :channel,
                        last_updated = NOW()
                    WHERE identity_id = :iid
                """), {'iid': identity_id, 'channel': channel})
    
    def get_segment(self, identity_id: uuid.UUID) -> str:
        """Get segment for identity."""
        
        profile = self.get_profile(identity_id)
        
        if not profile:
            return 'unknown'
        
        # Simple segmentation logic
        ltv = profile['lifetime_value']
        conversions = profile['total_conversions']
        
        if ltv > 50000:
            return 'high_value'
        elif ltv > 15000:
            return 'medium_value'
        elif conversions > 0:
            return 'converted'
        else:
            return 'prospect'
    
    def get_lifetime_value(self, identity_id: uuid.UUID) -> float:
        """Get lifetime value for identity."""
        
        profile = self.get_profile(identity_id)
        return profile['lifetime_value'] if profile else 0.0
    
    def get_top_profiles(self, limit: int = 100, order_by: str = 'lifetime_value') -> List[Dict]:
        """Get top profiles by metric."""
        
        with self.engine.connect() as conn:
            results = conn.execute(text(f"""
                SELECT 
                    identity_id,
                    total_storms,
                    total_conversions,
                    lifetime_value,
                    avg_sii_score,
                    avg_uplift,
                    segment
                FROM behavioral_profiles
                WHERE tenant_id = :tid
                ORDER BY {order_by} DESC
                LIMIT :limit
            """), {'tid': self.tenant_id, 'limit': limit}).fetchall()
        
        return [{
            'identity_id': str(r[0]),
            'total_storms': r[1],
            'total_conversions': r[2],
            'lifetime_value': r[3],
            'avg_sii_score': r[4],
            'avg_uplift': r[5],
            'segment': r[6]
        } for r in results]


if __name__ == '__main__':
    print("=" * 60)
    print("BEHAVIORAL PROFILES - SETUP & TEST")
    print("=" * 60)
    
    tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
    service = BehavioralProfileService(tenant_id)
    
    # Create test identity
    from identity_graph import IdentityGraph
    graph = IdentityGraph(tenant_id)
    
    property_id = uuid.uuid4()
    identity_id = graph.link_property(property_id, {
        'email': 'test@example.com'
    })
    
    print(f"\nCreated identity: {identity_id}")
    
    # Update profile with events
    print("\nUpdating profile...")
    service.update_profile(identity_id, {'type': 'storm_participation'})
    service.update_profile(identity_id, {'type': 'sii_score', 'score': 0.75})
    service.update_profile(identity_id, {'type': 'uplift_score', 'uplift': 0.20})
    service.update_profile(identity_id, {'type': 'conversion', 'value': 15000})
    service.update_profile(identity_id, {'type': 'channel_interaction', 'channel': 'door_knock'})
    
    # Get profile
    print("\nProfile:")
    profile = service.get_profile(identity_id)
    for key, value in profile.items():
        print(f"  {key}: {value}")
    
    # Get segment
    segment = service.get_segment(identity_id)
    print(f"\nSegment: {segment}")
    
    # Get LTV
    ltv = service.get_lifetime_value(identity_id)
    print(f"LTV: ${ltv:,.0f}")
    
    print("\n✅ Behavioral profiles ready")
