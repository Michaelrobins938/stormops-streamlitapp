"""
Behavior Event Logger
Log channel touches, journeys, and outcomes
"""

import psycopg2
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class BehaviorLogger:
    """Log behavior events"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def log_event(self, event_id: str, lead_id: str, parcel_id: str, 
                  channel: str, event_type: str, context: dict = None) -> bool:
        """Log a behavior event"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO behavior_events (
                    event_id, lead_id, parcel_id, channel, event_type,
                    timestamp, context
                ) VALUES (%s, %s, %s, %s, %s, NOW(), %s)
            """, (
                event_id, lead_id, parcel_id, channel, event_type,
                json.dumps(context or {})
            ))
            
            self.conn.commit()
            logger.info(f"Logged event: {lead_id} → {channel} ({event_type})")
            return True
        
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            self.conn.rollback()
            return False
        finally:
            cursor.close()
    
    def record_journey(self, event_id: str, lead_id: str, parcel_id: str,
                      channels: list, final_outcome: str, 
                      job_revenue: float = 0, claim_payout: float = 0) -> bool:
        """Record a complete journey"""
        cursor = self.conn.cursor()
        
        try:
            total_value = job_revenue + claim_payout
            
            cursor.execute("""
                INSERT INTO journey_outcomes (
                    event_id, lead_id, parcel_id, channels_touched,
                    final_outcome, job_revenue_usd, claim_payout_usd, total_value_usd
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id, lead_id) DO UPDATE
                SET final_outcome = EXCLUDED.final_outcome,
                    total_value_usd = EXCLUDED.total_value_usd
            """, (
                event_id, lead_id, parcel_id, channels, final_outcome,
                job_revenue, claim_payout, total_value
            ))
            
            self.conn.commit()
            logger.info(f"Recorded journey: {lead_id} → {final_outcome} (${total_value:,.0f})")
            return True
        
        except Exception as e:
            logger.error(f"Error recording journey: {e}")
            self.conn.rollback()
            return False
        finally:
            cursor.close()


class PsychographicSegmenter:
    """Segment leads by psychographic profile"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def segment_parcel(self, parcel_id: str, event_id: str) -> str:
        """Assign psychographic segment to parcel"""
        cursor = self.conn.cursor()
        
        try:
            # Get parcel attributes
            cursor.execute("""
                SELECT pa.owner_occupied, pa.assessed_value_usd, ra.roof_age_years,
                       ee.credit_proxy_score
                FROM property_attributes pa
                LEFT JOIN roof_attributes ra ON pa.parcel_id = ra.parcel_id
                LEFT JOIN external_enrichment ee ON pa.parcel_id = ee.parcel_id
                WHERE pa.parcel_id = %s
            """, (parcel_id,))
            
            result = cursor.fetchone()
            if not result:
                return 'unknown'
            
            owner_occupied, assessed_value, roof_age, credit_score = result
            
            # Simple segmentation logic
            if owner_occupied and assessed_value > 400000 and credit_score > 0.7:
                segment = 'high_intent_owner'
            elif owner_occupied and roof_age > 20:
                segment = 'aging_roof_owner'
            elif not owner_occupied:
                segment = 'investor_property'
            else:
                segment = 'standard'
            
            # Record segment membership
            cursor.execute("""
                INSERT INTO segment_membership (parcel_id, segment_id, confidence)
                VALUES (%s, %s, %s)
                ON CONFLICT (parcel_id, segment_id) DO NOTHING
            """, (parcel_id, segment, 0.8))
            
            self.conn.commit()
            logger.info(f"Segmented {parcel_id} → {segment}")
            return segment
        
        except Exception as e:
            logger.error(f"Error segmenting parcel: {e}")
            return 'unknown'
        finally:
            cursor.close()


if __name__ == '__main__':
    logger_svc = BehaviorLogger()
    logger_svc.connect()
    
    # Log sample events
    logger_svc.log_event('event-1', 'lead-1', 'parcel-1', 'sms', 'sent')
    logger_svc.log_event('event-1', 'lead-1', 'parcel-1', 'sms', 'opened')
    logger_svc.log_event('event-1', 'lead-1', 'parcel-1', 'phone', 'call_received')
    logger_svc.log_event('event-1', 'lead-1', 'parcel-1', 'door_knock', 'appointment_set')
    
    # Record journey
    logger_svc.record_journey(
        'event-1', 'lead-1', 'parcel-1',
        ['sms', 'phone', 'door_knock'],
        'conversion',
        job_revenue=10000,
        claim_payout=5000
    )
    
    logger_svc.close()
    
    # Segment
    segmenter = PsychographicSegmenter()
    segmenter.connect()
    segment = segmenter.segment_parcel('parcel-1', 'event-1')
    print(f"Segment: {segment}")
    segmenter.close()
