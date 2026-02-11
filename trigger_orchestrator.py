"""
Trigger Orchestrator
Listens to feature changes and orchestrates Proposal emission
"""

import psycopg2
import logging
from datetime import datetime
from feature_engineering import FeatureEngineer, TriggerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class TriggerOrchestrator:
    """Orchestrate feature computation and trigger emission"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def process_event(self, event_id: str):
        """Process a single event end-to-end"""
        logger.info(f"Processing event {event_id}")
        
        try:
            # Step 1: Compute sector features
            engineer = FeatureEngineer()
            engineer.connect()
            
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM sectors")
            sectors = cursor.fetchall()
            cursor.close()
            
            for sector_id, in sectors:
                engineer.compute_sector_features(sector_id, event_id)
            
            # Step 2: Compute parcel impacts
            engineer.compute_parcel_impacts(event_id)
            engineer.close()
            
            # Step 3: Check triggers and emit Proposals
            triggers = TriggerService()
            triggers.connect()
            triggers.check_triggers(event_id)
            triggers.close()
            
            logger.info(f"✅ Event {event_id} processed")
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    def process_all_active_events(self):
        """Process all active events"""
        logger.info("Processing all active events...")
        
        self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM events WHERE status = 'active'")
            events = cursor.fetchall()
            cursor.close()
            
            for event_id, in events:
                self.process_event(event_id)
            
            logger.info(f"Processed {len(events)} events")
            
        finally:
            self.close()


if __name__ == '__main__':
    import sys
    
    orchestrator = TriggerOrchestrator()
    
    if len(sys.argv) > 1:
        event_id = sys.argv[1]
        orchestrator.process_event(event_id)
    else:
        orchestrator.process_all_active_events()
