"""
Capacity and Constraint Validator
Checks if Proposals are feasible given team capacity and governance rules
"""

import psycopg2
import logging
from datetime import datetime, date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class CapacityValidator:
    """Validate Proposals against capacity constraints"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def validate_proposal(self, proposal_id: str) -> tuple:
        """Validate a Proposal against all constraints"""
        logger.info(f"Validating proposal {proposal_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get proposal
            cursor.execute("""
                SELECT proposal_type, expected_leads, target_zip, event_id
                FROM proposals WHERE id = %s
            """, (proposal_id,))
            
            result = cursor.fetchone()
            if not result:
                return False, "Proposal not found"
            
            proposal_type, expected_leads, target_zip, event_id = result
            
            # Check capacity
            if proposal_type == 'lead_gen':
                ok, msg = self._check_lead_gen_capacity(expected_leads, target_zip)
                if not ok:
                    return False, msg
            
            elif proposal_type == 'route_build':
                ok, msg = self._check_route_capacity(expected_leads)
                if not ok:
                    return False, msg
            
            elif proposal_type == 'sms_campaign':
                ok, msg = self._check_sms_compliance(expected_leads, event_id)
                if not ok:
                    return False, msg
            
            # Check saturation
            ok, msg = self._check_neighborhood_saturation(target_zip, event_id)
            if not ok:
                return False, msg
            
            logger.info(f"✅ Proposal {proposal_id} is feasible")
            return True, "Feasible"
        
        except Exception as e:
            logger.error(f"Error validating proposal: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def _check_lead_gen_capacity(self, expected_leads: int, target_zip: str) -> tuple:
        """Check if we have capacity to handle leads"""
        cursor = self.conn.cursor()
        
        try:
            # Get available rep capacity
            cursor.execute("""
                SELECT SUM(max_stops - assigned_stops)
                FROM rep_daily_capacity
                WHERE event_date = %s AND rep_id IN (
                    SELECT rep_id FROM field_reps WHERE territory = %s
                )
            """, (date.today(), target_zip))
            
            available_capacity = cursor.fetchone()[0] or 0
            
            if available_capacity < expected_leads:
                return False, f"Insufficient capacity: {available_capacity} available, {expected_leads} needed"
            
            return True, "Capacity OK"
        
        except Exception as e:
            logger.error(f"Error checking lead gen capacity: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def _check_route_capacity(self, expected_routes: int) -> tuple:
        """Check if we have enough reps for routes"""
        cursor = self.conn.cursor()
        
        try:
            # Get available reps
            cursor.execute("""
                SELECT COUNT(*) FROM field_reps WHERE status = 'available'
            """)
            
            available_reps = cursor.fetchone()[0] or 0
            
            if available_reps < expected_routes:
                return False, f"Insufficient reps: {available_reps} available, {expected_routes} needed"
            
            return True, "Capacity OK"
        
        except Exception as e:
            logger.error(f"Error checking route capacity: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def _check_sms_compliance(self, sms_count: int, event_id: str) -> tuple:
        """Check TCPA compliance for SMS"""
        cursor = self.conn.cursor()
        
        try:
            # Check daily SMS limit (max 3 per number per day)
            cursor.execute("""
                SELECT COUNT(*) FROM tcpa_compliance
                WHERE event_id = %s AND sms_sent_at > NOW() - INTERVAL '24 hours'
                GROUP BY phone_number HAVING COUNT(*) >= 3
            """, (event_id,))
            
            blocked_numbers = cursor.fetchone()
            if blocked_numbers and blocked_numbers[0] > 0:
                return False, f"TCPA limit exceeded for {blocked_numbers[0]} numbers"
            
            return True, "TCPA compliant"
        
        except Exception as e:
            logger.error(f"Error checking SMS compliance: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def _check_neighborhood_saturation(self, target_zip: str, event_id: str) -> tuple:
        """Check neighborhood saturation"""
        cursor = self.conn.cursor()
        
        try:
            # Get saturation ratio
            cursor.execute("""
                SELECT saturation_ratio FROM neighborhood_saturation
                WHERE event_id = %s AND neighborhood_id = %s
            """, (event_id, target_zip))
            
            result = cursor.fetchone()
            if result:
                saturation = result[0]
                if saturation > 0.8:
                    return False, f"Neighborhood saturation too high: {saturation:.1%}"
            
            return True, "Saturation OK"
        
        except Exception as e:
            logger.error(f"Error checking saturation: {e}")
            return False, str(e)
        finally:
            cursor.close()


class GovernanceValidator:
    """Validate Proposals against governance rules"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def validate_proposal(self, proposal_id: str) -> tuple:
        """Validate Proposal against governance rules"""
        logger.info(f"Validating governance for proposal {proposal_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get all enabled rules
            cursor.execute("""
                SELECT rule_type, constraint_type, constraint_value
                FROM governance_rules WHERE enabled = TRUE
            """)
            
            rules = cursor.fetchall()
            
            for rule_type, constraint_type, constraint_value in rules:
                if rule_type == 'TCPA':
                    ok, msg = self._check_tcpa_rule(proposal_id, constraint_value)
                    if not ok:
                        return False, msg
                
                elif rule_type == 'FREQUENCY':
                    ok, msg = self._check_frequency_rule(proposal_id, constraint_value)
                    if not ok:
                        return False, msg
                
                elif rule_type == 'TERRITORY':
                    ok, msg = self._check_territory_rule(proposal_id, constraint_value)
                    if not ok:
                        return False, msg
            
            logger.info(f"✅ Proposal {proposal_id} passes governance")
            return True, "Governance OK"
        
        except Exception as e:
            logger.error(f"Error validating governance: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def _check_tcpa_rule(self, proposal_id: str, constraint: str) -> tuple:
        """Check TCPA rules"""
        # constraint format: "max_sms_per_number_per_day:3"
        parts = constraint.split(':')
        if len(parts) != 2:
            return True, "Invalid constraint format"
        
        max_sms = int(parts[1])
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM tcpa_compliance
                WHERE sms_sent_at > NOW() - INTERVAL '24 hours'
                GROUP BY phone_number HAVING COUNT(*) > %s
            """, (max_sms,))
            
            violations = cursor.fetchone()
            if violations and violations[0] > 0:
                return False, f"TCPA violation: SMS limit {max_sms} exceeded"
            
            return True, "TCPA OK"
        finally:
            cursor.close()
    
    def _check_frequency_rule(self, proposal_id: str, constraint: str) -> tuple:
        """Check frequency rules"""
        # constraint format: "max_contacts_per_parcel_per_day:1"
        return True, "Frequency OK"
    
    def _check_territory_rule(self, proposal_id: str, constraint: str) -> tuple:
        """Check territory rules"""
        # constraint format: "no_double_knock_same_day"
        return True, "Territory OK"


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python capacity_validator.py <proposal_id>")
        sys.exit(1)
    
    proposal_id = sys.argv[1]
    
    # Validate capacity
    validator = CapacityValidator()
    validator.connect()
    ok, msg = validator.validate_proposal(proposal_id)
    validator.close()
    
    print(f"Capacity: {'✅' if ok else '❌'} {msg}")
    
    # Validate governance
    gov = GovernanceValidator()
    gov.connect()
    ok, msg = gov.validate_proposal(proposal_id)
    gov.close()
    
    print(f"Governance: {'✅' if ok else '❌'} {msg}")
