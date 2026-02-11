"""
Load A-tier leads CSV into StormOps backend
Maps enriched CSV columns → internal lead schema
"""

import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

def load_a_tier_leads(csv_path: str = 'a_tier_leads.csv', event_id: str = 'DFW_STORM_24'):
    """Import A-tier leads from CSV into backend tables."""
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} A-tier leads from {csv_path}")
    
    with engine.begin() as conn:
        for _, row in df.iterrows():
            # Insert/update property
            conn.execute(text("""
                INSERT INTO properties (property_id, address, city, zip_code, latitude, longitude)
                VALUES (:pid, :addr, :city, :zip, 0, 0)
                ON CONFLICT (property_id) DO UPDATE SET
                    address = EXCLUDED.address,
                    city = EXCLUDED.city,
                    zip_code = EXCLUDED.zip_code
            """), {
                'pid': row['property_id'],
                'addr': row['address'],
                'city': row['city'],
                'zip': row['zip_code']
            })
            
            # Insert SII score + risk
            conn.execute(text("""
                INSERT INTO property_exposure (property_id, event_id, sii_score, physics_risk_score, hwds_exposure_score)
                VALUES (:pid, :eid, :sii, :phys, :hwds)
                ON CONFLICT (property_id, event_id) DO UPDATE SET
                    sii_score = EXCLUDED.sii_score,
                    physics_risk_score = EXCLUDED.physics_risk_score,
                    hwds_exposure_score = EXCLUDED.hwds_exposure_score
            """), {
                'pid': row['property_id'],
                'eid': event_id,
                'sii': row['sii_score'],
                'phys': row.get('physics_risk_score', 0),
                'hwds': row.get('hwds_exposure_score', 0)
            })
            
            # Insert persona + play
            conn.execute(text("""
                INSERT INTO psychographic_profiles (property_id, primary_persona, risk_tolerance, price_sensitivity)
                VALUES (:pid, :persona, :risk_tol, :price_sens)
                ON CONFLICT (property_id) DO UPDATE SET
                    primary_persona = EXCLUDED.primary_persona,
                    risk_tolerance = EXCLUDED.risk_tolerance,
                    price_sensitivity = EXCLUDED.price_sensitivity
            """), {
                'pid': row['property_id'],
                'persona': row['primary_persona'],
                'risk_tol': row.get('risk_tolerance', 50),
                'price_sens': row.get('price_sensitivity', 50)
            })
            
            # Insert recommended play
            conn.execute(text("""
                INSERT INTO property_plays (property_id, play_id, play_message, follow_up_sla_hours)
                VALUES (:pid, :play, :msg, :sla)
                ON CONFLICT (property_id, play_id) DO UPDATE SET
                    play_message = EXCLUDED.play_message,
                    follow_up_sla_hours = EXCLUDED.follow_up_sla_hours
            """), {
                'pid': row['property_id'],
                'play': row['recommended_play'],
                'msg': row.get('play_message', ''),
                'sla': row.get('follow_up_sla_hours', 24)
            })
    
    print(f"✅ Imported {len(df)} A-tier leads into backend")
    
    # Verify counts by ZIP
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT p.zip_code, COUNT(*) as cnt
            FROM properties p
            JOIN property_exposure pe ON p.property_id = pe.property_id
            WHERE pe.event_id = :eid AND pe.sii_score >= 100
            GROUP BY p.zip_code
            ORDER BY cnt DESC
        """), {'eid': event_id})
        
        print("\nA-tier leads by ZIP:")
        for row in result:
            print(f"  {row.zip_code}: {row.cnt}")

if __name__ == '__main__':
    load_a_tier_leads()
