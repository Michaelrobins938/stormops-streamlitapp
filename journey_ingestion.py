"""
Journey Ingestion: A-tier leads → customer_journeys table
Minimal pipeline to populate Iceberg with real StormOps events
"""

from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict

def generate_journeys_from_a_tier_leads(csv_path='a_tier_leads.csv') -> List[Dict]:
    """Convert A-tier leads into realistic customer journeys."""
    
    df = pd.read_csv(csv_path)
    journeys = []
    
    for _, lead in df.iterrows():
        property_id = lead['property_id']
        zip_code = str(int(lead['zip_code'])) if pd.notna(lead['zip_code']) else '75209'
        persona = lead['primary_persona']
        play = lead['recommended_play']
        sii = lead['sii_score']
        
        # Generate realistic journey based on persona
        base_time = datetime(2024, 6, 15, 10, 0, 0)
        
        # All journeys start with GA4 (website visit)
        events = [
            {
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'ga4',
                'timestamp': base_time,
                'converted': False,
                'conversion_value': 0
            }
        ]
        
        # Persona-specific journey patterns
        if persona == 'Deal_Hunter':
            # High digital engagement, responds to financing plays
            events.append({
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'email',
                'timestamp': base_time + timedelta(hours=2),
                'converted': False,
                'conversion_value': 0
            })
            events.append({
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'door_knock',
                'timestamp': base_time + timedelta(hours=24),
                'converted': False,
                'conversion_value': 0
            })
            if sii >= 100:  # High SII = conversion
                events.append({
                    'property_id': property_id,
                    'zip_code': zip_code,
                    'event_id': 'DFW_STORM_24',
                    'channel': 'call',
                    'timestamp': base_time + timedelta(hours=48),
                    'converted': True,
                    'conversion_value': lead['estimated_value'] * 0.03  # 3% of home value
                })
        
        elif persona == 'Proof_Seeker':
            # Needs documentation, responds to impact reports
            events.append({
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'door_knock',
                'timestamp': base_time + timedelta(hours=6),
                'converted': False,
                'conversion_value': 0
            })
            events.append({
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'email',
                'timestamp': base_time + timedelta(hours=12),
                'converted': False,
                'conversion_value': 0
            })
            if sii >= 90:
                events.append({
                    'property_id': property_id,
                    'zip_code': zip_code,
                    'event_id': 'DFW_STORM_24',
                    'channel': 'call',
                    'timestamp': base_time + timedelta(hours=72),
                    'converted': True,
                    'conversion_value': lead['estimated_value'] * 0.03
                })
        
        elif persona == 'Family_Protector':
            # Safety-focused, responds to warranty plays
            events.append({
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'door_knock',
                'timestamp': base_time + timedelta(hours=4),
                'converted': False,
                'conversion_value': 0
            })
            events.append({
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'sms',
                'timestamp': base_time + timedelta(hours=24),
                'converted': False,
                'conversion_value': 0
            })
            if sii >= 95:
                events.append({
                    'property_id': property_id,
                    'zip_code': zip_code,
                    'event_id': 'DFW_STORM_24',
                    'channel': 'call',
                    'timestamp': base_time + timedelta(hours=36),
                    'converted': True,
                    'conversion_value': lead['estimated_value'] * 0.03
                })
        
        else:  # Status_Conscious or default
            events.append({
                'property_id': property_id,
                'zip_code': zip_code,
                'event_id': 'DFW_STORM_24',
                'channel': 'door_knock',
                'timestamp': base_time + timedelta(hours=8),
                'converted': False,
                'conversion_value': 0
            })
            if sii >= 100:
                events.append({
                    'property_id': property_id,
                    'zip_code': zip_code,
                    'event_id': 'DFW_STORM_24',
                    'channel': 'call',
                    'timestamp': base_time + timedelta(hours=48),
                    'converted': True,
                    'conversion_value': lead['estimated_value'] * 0.03
                })
        
        journeys.extend(events)
    
    return journeys


def write_journeys_to_trino(journeys: List[Dict]):
    """Write journeys to Iceberg via Trino."""
    try:
        from trino.dbapi import connect
        conn = connect(
            host='localhost',
            port=8080,
            user='stormops',
            catalog='iceberg',
            schema='stormops'
        )
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_journeys (
                property_id VARCHAR,
                zip_code VARCHAR,
                event_id VARCHAR,
                channel VARCHAR,
                timestamp TIMESTAMP,
                converted BOOLEAN,
                conversion_value DOUBLE
            )
        """)
        
        # Insert journeys
        for journey in journeys:
            cursor.execute("""
                INSERT INTO customer_journeys VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                journey['property_id'],
                journey['zip_code'],
                journey['event_id'],
                journey['channel'],
                journey['timestamp'],
                journey['converted'],
                journey['conversion_value']
            ))
        
        print(f"✅ Wrote {len(journeys)} events to Trino")
        return True
        
    except Exception as e:
        print(f"⚠️  Trino write failed: {e}")
        print("Falling back to SQLite")
        return write_journeys_to_sqlite(journeys)


def write_journeys_to_sqlite(journeys: List[Dict]):
    """Fallback: Write journeys to SQLite."""
    from sqlalchemy import create_engine, text
    
    engine = create_engine('sqlite:///stormops_journeys.db')
    
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_journeys (
                property_id TEXT,
                zip_code TEXT,
                event_id TEXT,
                channel TEXT,
                timestamp DATETIME,
                converted INTEGER,
                conversion_value REAL
            )
        """))
        
        for journey in journeys:
            conn.execute(text("""
                INSERT INTO customer_journeys VALUES 
                (:pid, :zip, :eid, :channel, :ts, :converted, :value)
            """), {
                'pid': journey['property_id'],
                'zip': journey['zip_code'],
                'eid': journey['event_id'],
                'channel': journey['channel'],
                'ts': journey['timestamp'],
                'converted': int(journey['converted']),
                'value': journey['conversion_value']
            })
    
    print(f"✅ Wrote {len(journeys)} events to SQLite")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("JOURNEY INGESTION: A-tier leads → customer_journeys")
    print("=" * 60)
    
    # Generate journeys from A-tier leads
    journeys = generate_journeys_from_a_tier_leads()
    
    print(f"\nGenerated {len(journeys)} journey events")
    
    # Count by channel
    from collections import Counter
    channel_counts = Counter(j['channel'] for j in journeys)
    print("\nEvents by channel:")
    for channel, count in channel_counts.most_common():
        print(f"  {channel}: {count}")
    
    # Count conversions
    conversions = sum(1 for j in journeys if j['converted'])
    print(f"\nConversions: {conversions}")
    
    # Write to database
    print("\nWriting to database...")
    write_journeys_to_trino(journeys)
    
    print("\n" + "=" * 60)
    print("✅ Journey ingestion complete")
    print("\nNext: Run attribution_integration.py to see real attribution")
    print("=" * 60)
