"""
Load test data for 75034 (Frisco) into StormOps database.
Generates 4,200 mock parcels with roof properties and SII scores.
"""

import psycopg2
from psycopg2.extras import execute_values
import uuid
import random
from datetime import datetime
import numpy as np
from sii_scorer import SIIScorer

def load_test_data(db_host='localhost', db_name='stormops', db_user='postgres', db_password='password'):
    """Load test data for 75034."""
    
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
    )
    cursor = conn.cursor()
    
    try:
        # Create event
        event_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO events (id, name, event_date, peak_hail_inches, max_wind_mph, estimated_value_usd, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            event_id,
            'DFW Storm 24',
            datetime.now(),
            2.5,
            65,
            8400000,
            'active',
        ))
        print(f"Created event: {event_id}")
        
        # Generate 4,200 mock parcels in 75034 (Frisco)
        # Frisco bounds: ~33.15-33.25°N, ~-96.85--96.75°W
        parcels = []
        for i in range(4200):
            parcel_id = f"75034-{i:05d}"
            lat = random.uniform(33.15, 33.25)
            lon = random.uniform(-96.85, -96.75)
            roof_material = random.choice(['asphalt', 'metal', 'tile', 'composite'])
            roof_age = random.randint(5, 30)
            
            parcels.append((
                str(uuid.uuid4()),
                parcel_id,
                '75034',
                f"{i} Mock St, Frisco, TX",
                f"POINT({lon} {lat})",
                roof_material,
                roof_age,
                random.uniform(200000, 500000),
            ))
        
        # Batch insert parcels
        execute_values(
            cursor,
            """
            INSERT INTO parcels (id, parcel_id, zip_code, address, geometry, roof_material, roof_age_years, estimated_value_usd)
            VALUES %s
            ON CONFLICT (parcel_id) DO NOTHING
            """,
            parcels,
        )
        conn.commit()
        print(f"Inserted {len(parcels)} parcels")
        
        # Get parcel IDs
        cursor.execute("SELECT id FROM parcels WHERE zip_code = '75034' LIMIT 4200")
        parcel_ids = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(parcel_ids)} parcels in database")
        
        # Generate hail intensities and SII scores
        scorer = SIIScorer()
        impact_scores = []
        
        for parcel_id in parcel_ids:
            # Get parcel properties
            cursor.execute("""
                SELECT roof_material, roof_age_years FROM parcels WHERE id = %s
            """, (parcel_id,))
            roof_material, roof_age = cursor.fetchone()
            
            # Mock hail intensity (0-70mm, with hotspot around 50mm)
            hail_intensity = np.random.normal(loc=40, scale=15)
            hail_intensity = max(0, min(70, hail_intensity))  # Clamp to 0-70
            
            # Score with SII
            result = scorer.score(
                hail_intensity_mm=hail_intensity,
                roof_material=roof_material,
                roof_age_years=roof_age,
            )
            
            impact_scores.append((
                event_id,
                parcel_id,
                hail_intensity,
                result['sii_score'],
                result['damage_probability'],
                result['sii_score'] * 5000,  # Rough estimate: $5k per SII point
            ))
        
        # Batch insert impact scores
        execute_values(
            cursor,
            """
            INSERT INTO impact_scores (event_id, parcel_id, hail_intensity_mm, sii_score, damage_probability, estimated_claim_value_usd)
            VALUES %s
            ON CONFLICT (event_id, parcel_id) DO UPDATE
            SET hail_intensity_mm = EXCLUDED.hail_intensity_mm,
                sii_score = EXCLUDED.sii_score,
                damage_probability = EXCLUDED.damage_probability,
                estimated_claim_value_usd = EXCLUDED.estimated_claim_value_usd
            """,
            impact_scores,
        )
        conn.commit()
        print(f"Inserted {len(impact_scores)} impact scores")
        
        # Verify: count parcels with SII >= 60
        cursor.execute("""
            SELECT COUNT(*) FROM impact_scores
            WHERE event_id = %s AND sii_score >= 60
        """, (event_id,))
        high_sii_count = cursor.fetchone()[0]
        print(f"Parcels with SII >= 60: {high_sii_count}")
        
        # Show sample
        cursor.execute("""
            SELECT p.parcel_id, p.roof_material, p.roof_age_years, i.hail_intensity_mm, i.sii_score
            FROM impact_scores i
            JOIN parcels p ON i.parcel_id = p.id
            WHERE i.event_id = %s
            ORDER BY i.sii_score DESC
            LIMIT 10
        """, (event_id,))
        
        print("\nTop 10 highest SII scores:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}, age {row[2]}y, hail {row[3]:.1f}mm, SII {row[4]:.1f}")
        
        print(f"\nTest data loaded successfully!")
        print(f"Event ID: {event_id}")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    load_test_data()
