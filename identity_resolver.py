"""
Identity Resolution Engine
Probabilistic property identity matching using behavioral fingerprinting
"""

import hashlib
import uuid
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from datetime import datetime
import numpy as np

class IdentityResolver:
    """
    Resolve disparate property signals into Golden Identity
    Uses probabilistic softmax matching
    """
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
    
    def create_identity(self, tenant_id: uuid.UUID, property_id: uuid.UUID,
                       confidence_score: float = 1.0,
                       resolution_method: str = 'exact') -> uuid.UUID:
        """Create new property identity"""
        identity_id = uuid.uuid4()
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO property_identities (
                    identity_id, tenant_id, property_id,
                    confidence_score, resolution_method
                ) VALUES (
                    :identity_id, :tenant_id, :property_id,
                    :confidence, :method
                )
            """), {
                "identity_id": str(identity_id),
                "tenant_id": str(tenant_id),
                "property_id": str(property_id),
                "confidence": confidence_score,
                "method": resolution_method
            })
            conn.commit()
        
        return identity_id
    
    def add_signal(self, identity_id: uuid.UUID, signal_type: str, 
                  signal_value: str, match_weight: float = 1.0):
        """Add identity signal (email, phone, address, etc.)"""
        signal_hash = hashlib.sha256(signal_value.encode()).hexdigest()
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO identity_signals (
                    identity_id, signal_type, signal_value, signal_hash, match_weight
                ) VALUES (
                    :identity_id, :signal_type, :signal_value, :signal_hash, :match_weight
                )
            """), {
                "identity_id": str(identity_id),
                "signal_type": signal_type,
                "signal_value": signal_value,
                "signal_hash": signal_hash,
                "match_weight": match_weight
            })
            conn.commit()
    
    def fuzzy_match_property(self, tenant_id: uuid.UUID, 
                            email: Optional[str] = None,
                            phone: Optional[str] = None,
                            address: Optional[str] = None) -> Optional[Dict]:
        """
        Fuzzy match property using multiple signals
        Returns best match with confidence score
        """
        signals = []
        if email:
            signals.append(('email', email))
        if phone:
            signals.append(('phone', phone))
        if address:
            signals.append(('address', address))
        
        if not signals:
            return None
        
        # Hash signals
        signal_hashes = [hashlib.sha256(val.encode()).hexdigest() for _, val in signals]
        
        with self.engine.connect() as conn:
            # Find matching identities
            result = conn.execute(text("""
                SELECT 
                    pi.identity_id,
                    pi.property_id,
                    pi.confidence_score,
                    COUNT(DISTINCT isig.signal_id) as signal_matches,
                    SUM(isig.match_weight) as total_weight
                FROM property_identities pi
                JOIN identity_signals isig ON pi.identity_id = isig.identity_id
                WHERE pi.tenant_id = :tenant_id
                  AND isig.signal_hash = ANY(:hashes)
                GROUP BY pi.identity_id, pi.property_id, pi.confidence_score
                ORDER BY total_weight DESC, signal_matches DESC
                LIMIT 1
            """), {
                "tenant_id": str(tenant_id),
                "hashes": signal_hashes
            })
            
            row = result.fetchone()
            if not row:
                return None
            
            # Calculate match confidence using softmax
            signal_count = len(signals)
            matches = row[3]
            weight = row[4]
            
            # Confidence = (matches / total_signals) * weight_factor
            confidence = (matches / signal_count) * min(1.0, weight / signal_count)
            
            return {
                "identity_id": row[0],
                "property_id": row[1],
                "base_confidence": row[2],
                "match_confidence": confidence,
                "signal_matches": matches
            }
    
    def resolve_or_create(self, tenant_id: uuid.UUID, property_id: uuid.UUID,
                         email: Optional[str] = None,
                         phone: Optional[str] = None,
                         address: Optional[str] = None) -> uuid.UUID:
        """
        Resolve existing identity or create new one
        Returns identity_id
        """
        # Try fuzzy match
        match = self.fuzzy_match_property(tenant_id, email, phone, address)
        
        if match and match["match_confidence"] > 0.7:
            # High confidence match - use existing
            identity_id = uuid.UUID(match["identity_id"])
            
            # Update confidence score (Bayesian update)
            new_confidence = (match["base_confidence"] + match["match_confidence"]) / 2
            
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE property_identities
                    SET confidence_score = :confidence,
                        updated_at = NOW()
                    WHERE identity_id = :identity_id
                """), {
                    "identity_id": str(identity_id),
                    "confidence": new_confidence
                })
                conn.commit()
            
            return identity_id
        
        else:
            # Create new identity
            identity_id = self.create_identity(
                tenant_id, property_id,
                confidence_score=0.5,
                resolution_method='fuzzy' if match else 'new'
            )
            
            # Add signals
            if email:
                self.add_signal(identity_id, 'email', email, 1.0)
            if phone:
                self.add_signal(identity_id, 'phone', phone, 0.9)
            if address:
                self.add_signal(identity_id, 'address', address, 0.8)
            
            return identity_id
    
    def link_household(self, identity_ids: List[uuid.UUID]) -> uuid.UUID:
        """
        Link multiple identities into a household
        Returns household_id
        """
        household_id = uuid.uuid4()
        
        with self.engine.connect() as conn:
            for identity_id in identity_ids:
                conn.execute(text("""
                    UPDATE property_identities
                    SET household_id = :household_id,
                        updated_at = NOW()
                    WHERE identity_id = :identity_id
                """), {
                    "household_id": str(household_id),
                    "identity_id": str(identity_id)
                })
            conn.commit()
        
        return household_id
    
    def update_behavioral_profile(self, identity_id: uuid.UUID,
                                  web_sessions: int = 0,
                                  form_submissions: int = 0,
                                  call_attempts: int = 0):
        """Update behavioral fingerprint"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE property_identities
                SET web_sessions = web_sessions + :web,
                    form_submissions = form_submissions + :forms,
                    call_attempts = call_attempts + :calls,
                    updated_at = NOW()
                WHERE identity_id = :identity_id
            """), {
                "identity_id": str(identity_id),
                "web": web_sessions,
                "forms": form_submissions,
                "calls": call_attempts
            })
            conn.commit()
    
    def get_golden_identity(self, property_id: uuid.UUID) -> Optional[Dict]:
        """Retrieve golden identity for a property"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    pi.identity_id,
                    pi.property_id,
                    pi.confidence_score,
                    pi.household_id,
                    pi.decision_maker_name,
                    pi.decision_maker_email,
                    pi.decision_maker_phone,
                    pi.web_sessions,
                    pi.form_submissions,
                    pi.call_attempts
                FROM property_identities pi
                WHERE pi.property_id = :property_id
                ORDER BY pi.confidence_score DESC
                LIMIT 1
            """), {"property_id": str(property_id)})
            
            row = result.fetchone()
            if not row:
                return None
            
            return dict(row._mapping)
    
    def calculate_brier_score(self, identity_id: uuid.UUID, 
                             actual_converted: bool) -> float:
        """
        Calculate Brier score for confidence calibration
        Brier = (predicted_prob - actual_outcome)^2
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT confidence_score
                FROM property_identities
                WHERE identity_id = :identity_id
            """), {"identity_id": str(identity_id)})
            
            row = result.fetchone()
            if not row:
                return 1.0
            
            predicted = row[0]
            actual = 1.0 if actual_converted else 0.0
            
            brier = (predicted - actual) ** 2
            
            # Update confidence based on Brier score
            new_confidence = predicted - (brier * 0.1)  # Adjust by 10% of error
            new_confidence = max(0.0, min(1.0, new_confidence))
            
            conn.execute(text("""
                UPDATE property_identities
                SET confidence_score = :confidence
                WHERE identity_id = :identity_id
            """), {
                "identity_id": str(identity_id),
                "confidence": new_confidence
            })
            conn.commit()
        
        return brier


if __name__ == "__main__":
    # Demo
    resolver = IdentityResolver("postgresql://stormops:password@localhost:5432/stormops")
    
    tenant_id = uuid.uuid4()
    property_id = uuid.uuid4()
    
    # Create identity with signals
    identity_id = resolver.resolve_or_create(
        tenant_id, property_id,
        email="homeowner@example.com",
        phone="214-555-0100",
        address="123 Main St, Dallas, TX 75024"
    )
    
    print(f"✅ Created identity: {identity_id}")
    
    # Fuzzy match (should find existing)
    match = resolver.fuzzy_match_property(
        tenant_id,
        email="homeowner@example.com"
    )
    
    if match:
        print(f"✅ Fuzzy match: {match['match_confidence']:.2%} confidence")
    
    # Update behavioral profile
    resolver.update_behavioral_profile(identity_id, web_sessions=3, form_submissions=1)
    print(f"✅ Updated behavioral profile")
