"""
SLA & Quality Monitor
Tracks time-to-first-contact, rep adherence, claim acceptance rates.
"""

import psycopg2
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SLAMonitor:
    """
    Monitors SLAs and quality metrics.
    """
    
    # SLA thresholds (minutes)
    SLA_THRESHOLDS = {
        'first_contact': 15,      # Contact within 15 minutes of lead creation
        'first_inspection': 120,  # Inspection within 2 hours
        'quote_delivery': 1440,   # Quote within 24 hours
    }
    
    def __init__(self, db_host='localhost', db_name='stormops', db_user='postgres', db_password='password'):
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.conn = None
    
    def connect(self):
        """Connect to database."""
        self.conn = psycopg2.connect(
            host=self.db_host,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def check_sla_breaches(self, event_id: str) -> List[Dict]:
        """
        Check for SLA breaches on leads.
        
        Args:
            event_id: Event ID
        
        Returns:
            List of breached leads
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get leads that haven't been contacted within SLA
            sla_minutes = self.SLA_THRESHOLDS['first_contact']
            sla_time = datetime.now() - timedelta(minutes=sla_minutes)
            
            cursor.execute("""
                SELECT l.id, l.crm_lead_id, p.address, l.created_at,
                       EXTRACT(EPOCH FROM (NOW() - l.created_at)) / 60 as minutes_elapsed
                FROM leads l
                JOIN parcels p ON l.parcel_id = p.id
                WHERE l.event_id = %s
                AND l.lead_status = 'new'
                AND l.created_at < %s
                ORDER BY minutes_elapsed DESC
            """, (event_id, sla_time))
            
            breaches = []
            for row in cursor.fetchall():
                breaches.append({
                    'lead_id': row[0],
                    'crm_lead_id': row[1],
                    'address': row[2],
                    'created_at': row[3],
                    'minutes_elapsed': int(row[4]),
                    'sla_threshold': sla_minutes,
                    'breach_severity': 'critical' if row[4] > sla_minutes * 2 else 'warning',
                })
            
            logger.info(f"Found {len(breaches)} SLA breaches")
            return breaches
        
        except Exception as e:
            logger.error(f"Error checking SLA breaches: {e}")
            return []
        finally:
            cursor.close()
    
    def get_rep_performance(self, event_id: str, rep_id: Optional[str] = None) -> List[Dict]:
        """
        Get rep performance metrics.
        
        Args:
            event_id: Event ID
            rep_id: Optional specific rep ID
        
        Returns:
            List of rep performance dicts
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            if rep_id:
                cursor.execute("""
                    SELECT r.canvasser_id, COUNT(rp.parcel_id) as roofs_assigned,
                           COUNT(CASE WHEN l.lead_status != 'new' THEN 1 END) as roofs_contacted,
                           AVG(EXTRACT(EPOCH FROM (l.updated_at - l.created_at)) / 60) as avg_contact_time_minutes
                    FROM routes r
                    LEFT JOIN route_parcels rp ON r.id = rp.route_id
                    LEFT JOIN leads l ON rp.parcel_id = l.parcel_id AND l.event_id = %s
                    WHERE r.event_id = %s AND r.canvasser_id = %s
                    GROUP BY r.canvasser_id
                """, (event_id, event_id, rep_id))
            else:
                cursor.execute("""
                    SELECT r.canvasser_id, COUNT(rp.parcel_id) as roofs_assigned,
                           COUNT(CASE WHEN l.lead_status != 'new' THEN 1 END) as roofs_contacted,
                           AVG(EXTRACT(EPOCH FROM (l.updated_at - l.created_at)) / 60) as avg_contact_time_minutes
                    FROM routes r
                    LEFT JOIN route_parcels rp ON r.id = rp.route_id
                    LEFT JOIN leads l ON rp.parcel_id = l.parcel_id AND l.event_id = %s
                    WHERE r.event_id = %s
                    GROUP BY r.canvasser_id
                    ORDER BY roofs_contacted DESC
                """, (event_id, event_id))
            
            performance = []
            for row in cursor.fetchall():
                roofs_assigned = row[1] or 0
                roofs_contacted = row[2] or 0
                contact_rate = (roofs_contacted / roofs_assigned * 100) if roofs_assigned > 0 else 0
                
                performance.append({
                    'rep_id': row[0],
                    'roofs_assigned': roofs_assigned,
                    'roofs_contacted': roofs_contacted,
                    'contact_rate': round(contact_rate, 1),
                    'avg_contact_time_minutes': round(row[3], 1) if row[3] else 0,
                })
            
            return performance
        
        except Exception as e:
            logger.error(f"Error getting rep performance: {e}")
            return []
        finally:
            cursor.close()
    
    def get_claim_acceptance_rate(self, event_id: str) -> Dict:
        """
        Get claim acceptance rate metrics.
        
        Args:
            event_id: Event ID
        
        Returns:
            Dict with acceptance metrics
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get leads with impact reports vs without
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT l.id) as total_leads,
                    COUNT(DISTINCT CASE WHEN ir.id IS NOT NULL THEN l.id END) as leads_with_reports,
                    COUNT(DISTINCT CASE WHEN l.lead_status = 'closed' THEN l.id END) as closed_leads,
                    COUNT(DISTINCT CASE WHEN l.lead_status = 'closed' AND ir.id IS NOT NULL THEN l.id END) as closed_with_reports
                FROM leads l
                LEFT JOIN impact_reports ir ON l.parcel_id = ir.parcel_id AND l.event_id = ir.event_id
                WHERE l.event_id = %s
            """, (event_id,))
            
            result = cursor.fetchone()
            total_leads = result[0] or 0
            leads_with_reports = result[1] or 0
            closed_leads = result[2] or 0
            closed_with_reports = result[3] or 0
            
            # Calculate rates
            report_coverage = (leads_with_reports / total_leads * 100) if total_leads > 0 else 0
            acceptance_rate_with_reports = (closed_with_reports / leads_with_reports * 100) if leads_with_reports > 0 else 0
            acceptance_rate_without_reports = ((closed_leads - closed_with_reports) / (total_leads - leads_with_reports) * 100) if (total_leads - leads_with_reports) > 0 else 0
            
            return {
                'total_leads': total_leads,
                'leads_with_reports': leads_with_reports,
                'report_coverage_percent': round(report_coverage, 1),
                'closed_leads': closed_leads,
                'closed_with_reports': closed_with_reports,
                'acceptance_rate_with_reports': round(acceptance_rate_with_reports, 1),
                'acceptance_rate_without_reports': round(acceptance_rate_without_reports, 1),
                'lift_from_reports': round(acceptance_rate_with_reports - acceptance_rate_without_reports, 1),
            }
        
        except Exception as e:
            logger.error(f"Error getting claim acceptance rate: {e}")
            return {}
        finally:
            cursor.close()
    
    def get_dashboard_metrics(self, event_id: str) -> Dict:
        """
        Get all dashboard metrics for an event.
        
        Args:
            event_id: Event ID
        
        Returns:
            Dict with all metrics
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT l.id) as total_leads,
                    COUNT(DISTINCT CASE WHEN l.lead_status != 'new' THEN l.id END) as contacted_leads,
                    COUNT(DISTINCT CASE WHEN l.lead_status = 'inspected' THEN l.id END) as inspected_leads,
                    COUNT(DISTINCT CASE WHEN l.lead_status = 'closed' THEN l.id END) as closed_leads,
                    SUM(CASE WHEN l.lead_status = 'closed' THEN is.estimated_claim_value_usd ELSE 0 END) as total_claim_value
                FROM leads l
                LEFT JOIN impact_scores is ON l.parcel_id = is.parcel_id AND l.event_id = is.event_id
                WHERE l.event_id = %s
            """, (event_id,))
            
            result = cursor.fetchone()
            
            return {
                'total_leads': result[0] or 0,
                'contacted_leads': result[1] or 0,
                'inspected_leads': result[2] or 0,
                'closed_leads': result[3] or 0,
                'total_claim_value': int(result[4] or 0),
                'contact_rate': round((result[1] or 0) / (result[0] or 1) * 100, 1),
                'close_rate': round((result[3] or 0) / (result[0] or 1) * 100, 1),
            }
        
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return {}
        finally:
            cursor.close()


# Example usage
if __name__ == '__main__':
    monitor = SLAMonitor()
    monitor.connect()
    
    try:
        event_id = 'test-event-1'
        
        # Check SLA breaches
        breaches = monitor.check_sla_breaches(event_id)
        print(f"SLA Breaches: {len(breaches)}")
        for breach in breaches[:3]:
            print(f"  {breach['address']}: {breach['minutes_elapsed']} min (SLA: {breach['sla_threshold']} min)")
        
        # Get rep performance
        performance = monitor.get_rep_performance(event_id)
        print(f"\nRep Performance:")
        for rep in performance:
            print(f"  {rep['rep_id']}: {rep['roofs_contacted']}/{rep['roofs_assigned']} contacted ({rep['contact_rate']}%)")
        
        # Get claim acceptance rate
        acceptance = monitor.get_claim_acceptance_rate(event_id)
        print(f"\nClaim Acceptance:")
        print(f"  With reports: {acceptance.get('acceptance_rate_with_reports', 0)}%")
        print(f"  Without reports: {acceptance.get('acceptance_rate_without_reports', 0)}%")
        print(f"  Lift: {acceptance.get('lift_from_reports', 0)}%")
        
        # Get dashboard metrics
        metrics = monitor.get_dashboard_metrics(event_id)
        print(f"\nDashboard Metrics:")
        print(f"  Total leads: {metrics.get('total_leads', 0)}")
        print(f"  Contacted: {metrics.get('contacted_leads', 0)} ({metrics.get('contact_rate', 0)}%)")
        print(f"  Closed: {metrics.get('closed_leads', 0)} ({metrics.get('close_rate', 0)}%)")
        print(f"  Total claim value: ${metrics.get('total_claim_value', 0):,.0f}")
    
    finally:
        monitor.close()
