"""
Proposal Engine
Generates executable Proposals (lead gen, route build, SMS campaigns).
"""

import psycopg2
from psycopg2.extras import execute_values
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProposalEngine:
    """
    Generates and manages executable Proposals.
    """
    
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
    
    def generate_lead_gen_proposal(
        self,
        event_id: str,
        zip_code: str,
        sii_min: float = 60,
        sii_max: float = 100,
    ) -> Optional[str]:
        """
        Generate a lead generation Proposal.
        
        Args:
            event_id: Event ID
            zip_code: Target ZIP code
            sii_min: Minimum SII threshold
            sii_max: Maximum SII threshold
        
        Returns:
            Proposal ID if successful
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Count parcels matching criteria
            cursor.execute("""
                SELECT COUNT(*) FROM impact_scores is
                JOIN parcels p ON is.parcel_id = p.id
                WHERE is.event_id = %s
                AND p.zip_code = %s
                AND is.sii_score >= %s
                AND is.sii_score <= %s
            """, (event_id, zip_code, sii_min, sii_max))
            
            parcel_count = cursor.fetchone()[0]
            
            # Estimate value: $5k per SII point average
            avg_sii = (sii_min + sii_max) / 2
            expected_value = parcel_count * avg_sii * 5000
            
            # Create proposal
            proposal_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO proposals (
                    id, event_id, proposal_type, target_zip, target_sii_min, target_sii_max,
                    expected_leads, expected_value_usd, blast_radius, status, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                proposal_id,
                event_id,
                'lead_gen',
                zip_code,
                sii_min,
                sii_max,
                parcel_count,
                expected_value,
                parcel_count,
                'pending',
                'system',
            ))
            self.conn.commit()
            
            logger.info(f"Generated lead gen proposal: {proposal_id} ({parcel_count} leads, ${expected_value:,.0f})")
            return proposal_id
        
        except Exception as e:
            logger.error(f"Error generating lead gen proposal: {e}")
            self.conn.rollback()
            return None
        finally:
            cursor.close()
    
    def generate_route_build_proposal(
        self,
        event_id: str,
        zip_code: str,
        sii_min: float = 70,
        num_canvassers: int = 4,
    ) -> Optional[str]:
        """
        Generate a route build Proposal.
        
        Args:
            event_id: Event ID
            zip_code: Target ZIP code
            sii_min: Minimum SII threshold
            num_canvassers: Number of canvassers
        
        Returns:
            Proposal ID if successful
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Count high-SII parcels
            cursor.execute("""
                SELECT COUNT(*) FROM impact_scores is
                JOIN parcels p ON is.parcel_id = p.id
                WHERE is.event_id = %s
                AND p.zip_code = %s
                AND is.sii_score >= %s
            """, (event_id, zip_code, sii_min))
            
            parcel_count = cursor.fetchone()[0]
            roofs_per_route = parcel_count // num_canvassers
            expected_value = roofs_per_route * num_canvassers * 75 * 5000  # $75k per roof avg
            
            # Create proposal
            proposal_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO proposals (
                    id, event_id, proposal_type, target_zip, target_sii_min,
                    expected_leads, expected_value_usd, blast_radius, status, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                proposal_id,
                event_id,
                'route_build',
                zip_code,
                sii_min,
                parcel_count,
                expected_value,
                parcel_count,
                'pending',
                'system',
            ))
            self.conn.commit()
            
            logger.info(f"Generated route build proposal: {proposal_id} ({num_canvassers} routes, ${expected_value:,.0f})")
            return proposal_id
        
        except Exception as e:
            logger.error(f"Error generating route build proposal: {e}")
            self.conn.rollback()
            return None
        finally:
            cursor.close()
    
    def generate_sms_campaign_proposal(
        self,
        event_id: str,
        zip_code: str,
        segment: str = 'past_customers',
    ) -> Optional[str]:
        """
        Generate an SMS campaign Proposal.
        
        Args:
            event_id: Event ID
            zip_code: Target ZIP code
            segment: Customer segment ('past_customers', 'all', etc.)
        
        Returns:
            Proposal ID if successful
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Estimate customer count (mock: assume 800 past customers per ZIP)
            customer_count = 800 if segment == 'past_customers' else 2000
            
            # Estimate conversion: 35-45% open rate, 10% conversion
            expected_leads = int(customer_count * 0.4 * 0.1)
            expected_value = expected_leads * 75 * 5000  # $75k per roof avg
            
            # Create proposal
            proposal_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO proposals (
                    id, event_id, proposal_type, target_zip,
                    expected_leads, expected_value_usd, blast_radius, status, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                proposal_id,
                event_id,
                'sms_campaign',
                zip_code,
                expected_leads,
                expected_value,
                customer_count,
                'pending',
                'system',
            ))
            self.conn.commit()
            
            logger.info(f"Generated SMS campaign proposal: {proposal_id} ({customer_count} targets, ${expected_value:,.0f})")
            return proposal_id
        
        except Exception as e:
            logger.error(f"Error generating SMS campaign proposal: {e}")
            self.conn.rollback()
            return None
        finally:
            cursor.close()
    
    def approve_proposal(self, proposal_id: str, approved_by: str = 'operator') -> bool:
        """
        Approve a Proposal.
        
        Args:
            proposal_id: Proposal ID
            approved_by: User approving the proposal
        
        Returns:
            True if successful
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE proposals
                SET status = 'approved', approved_by = %s, updated_at = NOW()
                WHERE id = %s
            """, (approved_by, proposal_id))
            self.conn.commit()
            
            logger.info(f"Approved proposal: {proposal_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error approving proposal: {e}")
            self.conn.rollback()
            return False
        finally:
            cursor.close()
    
    def list_proposals(self, event_id: str, status: str = 'pending') -> List[Dict]:
        """
        List Proposals for an event.
        
        Args:
            event_id: Event ID
            status: Filter by status ('pending', 'approved', 'executed')
        
        Returns:
            List of proposal dicts
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, proposal_type, target_zip, expected_leads, expected_value_usd, blast_radius, status
                FROM proposals
                WHERE event_id = %s AND status = %s
                ORDER BY expected_value_usd DESC
            """, (event_id, status))
            
            proposals = []
            for row in cursor.fetchall():
                proposals.append({
                    'id': row[0],
                    'type': row[1],
                    'target_zip': row[2],
                    'expected_leads': row[3],
                    'expected_value': row[4],
                    'blast_radius': row[5],
                    'status': row[6],
                })
            
            return proposals
        
        except Exception as e:
            logger.error(f"Error listing proposals: {e}")
            return []
        finally:
            cursor.close()
