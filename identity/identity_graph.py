"""
Identity Graph - Unified identity resolution across channels/devices/storms
Deterministic + probabilistic linking
"""

from sqlalchemy import create_engine, text
from typing import Dict, List, Optional
import uuid
from datetime import datetime

class IdentityGraph:
    """Unified identity graph for homeowners."""
    
    def __init__(self, tenant_id: uuid.UUID, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.tenant_id = tenant_id
        self.engine = create_engine(db_url)
        self._init_schema()
    
    def _init_schema(self):
        """Create identity tables."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS identities (
                    identity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS identity_links (
                    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    identity_id UUID NOT NULL REFERENCES identities(identity_id),
                    identifier_type TEXT NOT NULL,
                    identifier_value TEXT NOT NULL,
                    link_strength FLOAT NOT NULL DEFAULT 1.0,
                    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(identity_id, identifier_type, identifier_value)
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_identity_links_lookup 
                ON identity_links(identifier_type, identifier_value)
            """))
    
    def link_property(self, property_id: uuid.UUID, identifiers: Dict[str, str]) -> uuid.UUID:
        """Link a property to an identity with additional identifiers."""
        
        # Check if property already linked
        with self.engine.connect() as conn:
            existing = conn.execute(text("""
                SELECT identity_id FROM identity_links
                WHERE identifier_type = 'property_id' 
                  AND identifier_value = :pid
            """), {'pid': str(property_id)}).fetchone()
            
            if existing:
                identity_id = existing[0]
            else:
                # Try to find existing identity via other identifiers
                identity_id = self._resolve_identity(identifiers)
                
                if not identity_id:
                    # Create new identity
                    identity_id = uuid.uuid4()
                    conn.execute(text("""
                        INSERT INTO identities (identity_id, tenant_id)
                        VALUES (:iid, :tid)
                    """), {'iid': identity_id, 'tid': self.tenant_id})
                    conn.commit()
        
        # Link property
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO identity_links (identity_id, identifier_type, identifier_value, link_strength)
                VALUES (:iid, 'property_id', :pid, 1.0)
                ON CONFLICT (identity_id, identifier_type, identifier_value) DO NOTHING
            """), {'iid': identity_id, 'pid': str(property_id)})
            
            # Link additional identifiers
            for id_type, id_value in identifiers.items():
                if id_value:
                    strength = 1.0 if id_type in ['email', 'phone'] else 0.8
                    conn.execute(text("""
                        INSERT INTO identity_links (identity_id, identifier_type, identifier_value, link_strength)
                        VALUES (:iid, :type, :value, :strength)
                        ON CONFLICT (identity_id, identifier_type, identifier_value) DO NOTHING
                    """), {'iid': identity_id, 'type': id_type, 'value': id_value, 'strength': strength})
        
        return identity_id
    
    def _resolve_identity(self, identifiers: Dict[str, str]) -> Optional[uuid.UUID]:
        """Resolve identity from identifiers (deterministic match)."""
        
        with self.engine.connect() as conn:
            for id_type, id_value in identifiers.items():
                if id_value and id_type in ['email', 'phone']:  # High-confidence identifiers
                    result = conn.execute(text("""
                        SELECT identity_id FROM identity_links
                        WHERE identifier_type = :type 
                          AND identifier_value = :value
                        LIMIT 1
                    """), {'type': id_type, 'value': id_value}).fetchone()
                    
                    if result:
                        return result[0]
        
        return None
    
    def resolve_identity(self, identifier_type: str, identifier_value: str) -> Optional[uuid.UUID]:
        """Resolve identity from a single identifier."""
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT identity_id FROM identity_links
                WHERE identifier_type = :type 
                  AND identifier_value = :value
                LIMIT 1
            """), {'type': identifier_type, 'value': identifier_value}).fetchone()
            
            return result[0] if result else None
    
    def get_identifiers(self, identity_id: uuid.UUID) -> List[Dict]:
        """Get all identifiers for an identity."""
        
        with self.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT identifier_type, identifier_value, link_strength, linked_at
                FROM identity_links
                WHERE identity_id = :iid
                ORDER BY link_strength DESC, linked_at DESC
            """), {'iid': identity_id}).fetchall()
        
        return [{
            'type': r[0],
            'value': r[1],
            'strength': r[2],
            'linked_at': r[3].isoformat()
        } for r in results]
    
    def merge_identities(self, id_a: uuid.UUID, id_b: uuid.UUID) -> uuid.UUID:
        """Merge two identities (keep id_a, move id_b links)."""
        
        with self.engine.begin() as conn:
            # Move all links from id_b to id_a
            conn.execute(text("""
                UPDATE identity_links
                SET identity_id = :id_a
                WHERE identity_id = :id_b
            """), {'id_a': id_a, 'id_b': id_b})
            
            # Delete id_b
            conn.execute(text("""
                DELETE FROM identities WHERE identity_id = :id_b
            """), {'id_b': id_b})
        
        return id_a
    
    def get_stats(self) -> Dict:
        """Get identity graph stats."""
        
        with self.engine.connect() as conn:
            stats = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT i.identity_id) as total_identities,
                    COUNT(il.link_id) as total_links,
                    AVG(link_count) as avg_links_per_identity
                FROM identities i
                LEFT JOIN identity_links il ON i.identity_id = il.identity_id
                LEFT JOIN (
                    SELECT identity_id, COUNT(*) as link_count
                    FROM identity_links
                    GROUP BY identity_id
                ) lc ON i.identity_id = lc.identity_id
                WHERE i.tenant_id = :tid
            """), {'tid': self.tenant_id}).fetchone()
        
        return {
            'total_identities': stats[0] or 0,
            'total_links': stats[1] or 0,
            'avg_links_per_identity': float(stats[2]) if stats[2] else 0
        }


if __name__ == '__main__':
    print("=" * 60)
    print("IDENTITY GRAPH - SETUP & TEST")
    print("=" * 60)
    
    tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
    graph = IdentityGraph(tenant_id)
    
    # Link a property
    print("\nLinking property...")
    property_id = uuid.uuid4()
    identity_id = graph.link_property(property_id, {
        'email': 'john@example.com',
        'phone': '+1234567890',
        'device_id': 'device_123'
    })
    print(f"✅ Linked to identity: {identity_id}")
    
    # Resolve identity
    print("\nResolving identity by email...")
    resolved = graph.resolve_identity('email', 'john@example.com')
    print(f"✅ Resolved: {resolved}")
    
    # Get identifiers
    print("\nIdentifiers for identity:")
    identifiers = graph.get_identifiers(identity_id)
    for ident in identifiers:
        print(f"  {ident['type']}: {ident['value']} (strength: {ident['strength']})")
    
    # Stats
    print("\nIdentity graph stats:")
    stats = graph.get_stats()
    print(f"  Total identities: {stats['total_identities']}")
    print(f"  Total links: {stats['total_links']}")
    print(f"  Avg links/identity: {stats['avg_links_per_identity']:.1f}")
    
    print("\n✅ Identity graph ready")
