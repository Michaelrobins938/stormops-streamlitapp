"""
Batch job processor for bulk operations
"""

import psycopg2
from datetime import datetime
import logging

from proposal_engine import ProposalEngine
from route_optimizer import RouteOptimizer
from impact_report_generator import ImpactReportGenerator
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process batch jobs"""
    
    def __init__(self):
        self.db_host = DB_HOST
        self.db_name = DB_NAME
        self.db_user = DB_USER
        self.db_password = DB_PASSWORD
    
    def process_all_events(self):
        """Process all active events"""
        try:
            conn = psycopg2.connect(
                host=self.db_host, database=self.db_name, 
                user=self.db_user, password=self.db_password
            )
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM events WHERE status = 'active'")
            events = cursor.fetchall()
            cursor.close()
            conn.close()
            
            for event_id, in events:
                self.process_event(event_id)
        
        except Exception as e:
            logger.error(f"Error processing events: {e}")
    
    def process_event(self, event_id):
        """Process single event"""
        logger.info(f"Processing event: {event_id}")
        
        try:
            # Generate proposals
            engine = ProposalEngine(self.db_host, self.db_name, self.db_user, self.db_password)
            engine.connect()
            
            lead_gen_id = engine.generate_lead_gen_proposal(event_id, '75034')
            logger.info(f"  Generated lead gen: {lead_gen_id}")
            
            sms_id = engine.generate_sms_campaign_proposal(event_id, '75034')
            logger.info(f"  Generated SMS: {sms_id}")
            
            engine.close()
            
            # Build routes
            optimizer = RouteOptimizer(self.db_host, self.db_name, self.db_user, self.db_password)
            optimizer.connect()
            
            route_ids = optimizer.build_routes(event_id, '75034')
            logger.info(f"  Built {len(route_ids)} routes")
            
            optimizer.close()
            
            # Generate reports
            gen = ImpactReportGenerator(self.db_host, self.db_name, self.db_user, self.db_password)
            gen.connect()
            
            report_count = gen.generate_batch_reports(event_id, sii_min=75)
            logger.info(f"  Generated {report_count} reports")
            
            gen.close()
            
            logger.info(f"✅ Event {event_id} processed")
        
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}")
    
    def cleanup_old_events(self, days=30):
        """Archive old events"""
        try:
            conn = psycopg2.connect(
                host=self.db_host, database=self.db_name,
                user=self.db_user, password=self.db_password
            )
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE events
                SET status = 'archived'
                WHERE status = 'active' AND event_date < NOW() - INTERVAL '%s days'
            """, (days,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Archived events older than {days} days")
        
        except Exception as e:
            logger.error(f"Error archiving events: {e}")


if __name__ == '__main__':
    processor = BatchProcessor()
    processor.process_all_events()
