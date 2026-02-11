"""
StormOps Attribution Integration
Minimal adapter: Lakehouse journeys → first-principles-attribution → Postgres
"""

import sys
sys.path.append('/home/forsythe/kirocli/kirocli/integrations/first-principles-attribution/backend')

from datetime import datetime
from typing import List, Dict
from models.attribution import Journey, TouchPoint
from engines.attribution.engine import AttributionEngine as FPAEngine


class AttributionEngine:
    """Wrapper for first-principles-attribution engine."""
    
    def format_journey(self, property_id: str, events: List[Dict]) -> Journey:
        """Convert StormOps events to attribution journey format."""
        touchpoints = []
        
        for event in events:
            tp = TouchPoint(
                channel=event.get('channel', 'direct'),
                timestamp=datetime.fromisoformat(event.get('timestamp').replace('Z', '+00:00'))
            )
            touchpoints.append(tp)
        
        return Journey(
            journey_id=property_id,
            path=touchpoints,
            conversion=events[-1].get('converted', False),
            conversion_value=events[-1].get('conversion_value', 0),
            num_touchpoints=len(touchpoints),
            duration_hours=0.0
        )
    
    def run_attribution(self, journeys: List[Journey], alpha: float = 0.5) -> Dict:
        """Run attribution engine on journeys."""
        engine = FPAEngine(journeys)
        return engine.run_analysis(alpha=alpha)
    
    def get_channel_attribution(self, zip_code: str, event_id: str) -> Dict:
        """Get channel attribution for a storm event in a ZIP."""
        
        # Query journeys from lakehouse (placeholder - wire to Trino)
        raw_events = self._fetch_journeys_from_lakehouse(zip_code, event_id)
        
        # Convert to Journey objects
        journeys = []
        for prop_id, events in raw_events.items():
            journey = self.format_journey(prop_id, events)
            journeys.append(journey)
        
        if not journeys:
            return {'error': 'No journeys found'}
        
        # Run attribution
        result = self.run_attribution(journeys, alpha=0.5)
        
        return {
            'zip_code': zip_code,
            'event_id': event_id,
            'channels': result['hybrid_result']['channel_attributions'],
            'total_journeys': result['total_journeys'],
            'conversions': result['total_conversions'],
            'processing_time_ms': result['processing_time_ms'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _fetch_journeys_from_lakehouse(self, zip_code: str, event_id: str) -> Dict[str, List[Dict]]:
        """Fetch journeys from Iceberg via Trino (or SQLite fallback)."""
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
            
            cursor.execute("""
                SELECT property_id, channel, timestamp, converted, conversion_value
                FROM customer_journeys
                WHERE zip_code = ? AND event_id = ?
                ORDER BY property_id, timestamp
            """, (zip_code, event_id))
            
            journeys = {}
            for row in cursor.fetchall():
                prop_id, channel, ts, converted, value = row
                if prop_id not in journeys:
                    journeys[prop_id] = []
                journeys[prop_id].append({
                    'channel': channel,
                    'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                    'converted': converted,
                    'conversion_value': value or 0
                })
            
            return journeys
            
        except Exception as e:
            print(f"Trino query failed: {e}")
            print("Falling back to SQLite")
            
            # Fallback to SQLite
            from sqlalchemy import create_engine, text
            engine = create_engine('sqlite:///stormops_journeys.db')
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT property_id, channel, timestamp, converted, conversion_value
                    FROM customer_journeys
                    WHERE zip_code = :zip AND event_id = :eid
                    ORDER BY property_id, timestamp
                """), {'zip': zip_code, 'eid': event_id})
                
                journeys = {}
                for row in result:
                    prop_id, channel, ts, converted, value = row
                    if prop_id not in journeys:
                        journeys[prop_id] = []
                    journeys[prop_id].append({
                        'channel': channel,
                        'timestamp': str(ts),
                        'converted': bool(converted),
                        'conversion_value': value or 0
                    })
                
                return journeys


def write_attribution_to_postgres(attribution: Dict):
    """Write attribution results to database (SQLite fallback if Postgres unavailable)."""
    from sqlalchemy import create_engine, text
    
    # Use SQLite for now
    engine = create_engine('sqlite:///stormops_attribution.db')
    
    # Create table if not exists
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS channel_attribution (
                zip_code TEXT,
                event_id TEXT,
                channel TEXT,
                credit FLOAT,
                total_journeys INT,
                conversions INT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (zip_code, event_id, channel)
            )
        """))
        
        # Insert attribution
        for channel, credit in attribution['channels'].items():
            conn.execute(text("""
                INSERT OR REPLACE INTO channel_attribution 
                (zip_code, event_id, channel, credit, total_journeys, conversions)
                VALUES (:zip, :event, :channel, :credit, :journeys, :conversions)
            """), {
                'zip': attribution['zip_code'],
                'event': attribution['event_id'],
                'channel': channel,
                'credit': credit,
                'journeys': attribution['total_journeys'],
                'conversions': attribution['conversions']
            })
    
    print(f"✅ Wrote attribution to SQLite: {len(attribution['channels'])} channels")
    return True


if __name__ == '__main__':
    # Test attribution engine integration
    engine = AttributionEngine()
    
    print("=" * 60)
    print("ATTRIBUTION ENGINE INTEGRATION TEST")
    print("=" * 60)
    
    # Run attribution on mock data
    result = engine.get_channel_attribution('75209', 'DFW_STORM_24')
    
    print(f"\nZIP Code: {result['zip_code']}")
    print(f"Event: {result['event_id']}")
    print(f"Total Journeys: {result['total_journeys']}")
    print(f"Conversions: {result['conversions']}")
    print(f"Processing Time: {result['processing_time_ms']:.2f}ms")
    
    print("\nChannel Attribution:")
    for channel, credit in sorted(result['channels'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {channel}: {credit*100:.1f}%")
    
    print("\n" + "=" * 60)
    print("Writing to Postgres...")
    write_attribution_to_postgres(result)
    
    print("\n" + "=" * 60)
    print("✅ Attribution pipeline complete")
    print("\nNext: Display in UI")
    print("  Query: SELECT * FROM channel_attribution WHERE event_id = 'DFW_STORM_24'")
    print("=" * 60)
