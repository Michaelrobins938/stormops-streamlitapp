"""
Governance Rules Engine
Enforces TCPA, frequency caps, territory rules, and ethical constraints
"""

import psycopg2
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class GovernanceEngine:
    """Enforce governance rules"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def check_tcpa_compliance(self, phone: str, event_id: str) -> tuple:
        """Check TCPA SMS limits"""
        cursor = self.conn.cursor()
        
        try:
            # Check 24-hour limit (max 3 SMS per number per day)
            cursor.execute("""
                SELECT COUNT(*) FROM tcpa_compliance
                WHERE phone_number = %s AND event_id = %s
                AND sms_sent_at > NOW() - INTERVAL '24 hours'
            """, (phone, event_id))
            
            sms_24h = cursor.fetchone()[0] or 0
            
            if sms_24h >= 3:
                return False, f"TCPA limit exceeded: {sms_24h} SMS in 24h"
            
            # Check opt-out
            cursor.execute("""
                SELECT opted_out FROM tcpa_compliance
                WHERE phone_number = %s
            """, (phone,))
            
            result = cursor.fetchone()
            if result and result[0]:
                return False, "Number opted out"
            
            return True, "TCPA compliant"
        
        except Exception as e:
            logger.error(f"Error checking TCPA: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def check_frequency_cap(self, parcel_id: str, event_id: str) -> tuple:
        """Check contact frequency cap"""
        cursor = self.conn.cursor()
        
        try:
            # Check if already contacted today
            cursor.execute("""
                SELECT COUNT(*) FROM lead_outcomes
                WHERE parcel_id = %s AND event_id = %s
                AND contacted_at > NOW() - INTERVAL '24 hours'
            """, (parcel_id, event_id))
            
            contacts_24h = cursor.fetchone()[0] or 0
            
            if contacts_24h > 0:
                return False, "Already contacted in last 24 hours"
            
            return True, "Frequency OK"
        
        except Exception as e:
            logger.error(f"Error checking frequency: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def check_neighborhood_saturation(self, neighborhood_id: str, event_id: str) -> tuple:
        """Check neighborhood saturation"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT saturation_ratio FROM neighborhood_saturation
                WHERE neighborhood_id = %s AND event_id = %s
            """, (neighborhood_id, event_id))
            
            result = cursor.fetchone()
            if result:
                saturation = result[0]
                if saturation > 0.8:
                    return False, f"Neighborhood saturation {saturation:.1%} exceeds 80%"
            
            return True, "Saturation OK"
        
        except Exception as e:
            logger.error(f"Error checking saturation: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def check_double_knock(self, parcel_id: str, event_id: str) -> tuple:
        """Check for double-knock (same street, same day)"""
        cursor = self.conn.cursor()
        
        try:
            # Get parcel address
            cursor.execute("""
                SELECT address FROM parcels WHERE id = %s
            """, (parcel_id,))
            
            result = cursor.fetchone()
            if not result:
                return True, "Parcel not found"
            
            address = result[0]
            street = ' '.join(address.split()[:-1]) if address else ''
            
            # Check if street already contacted today
            cursor.execute("""
                SELECT COUNT(*) FROM lead_outcomes lo
                JOIN parcels p ON lo.parcel_id = p.id
                WHERE p.address LIKE %s AND lo.event_id = %s
                AND lo.contacted_at > NOW() - INTERVAL '24 hours'
            """, (f"{street}%", event_id))
            
            street_contacts = cursor.fetchone()[0] or 0
            
            if street_contacts > 2:
                return False, f"Street already contacted {street_contacts} times today"
            
            return True, "Double-knock OK"
        
        except Exception as e:
            logger.error(f"Error checking double-knock: {e}")
            return False, str(e)
        finally:
            cursor.close()
    
    def validate_all(self, parcel_id: str, phone: str, event_id: str) -> tuple:
        """Validate all governance rules"""
        logger.info(f"Validating governance for {parcel_id}")
        
        checks = [
            ("TCPA", self.check_tcpa_compliance(phone, event_id)),
            ("Frequency", self.check_frequency_cap(parcel_id, event_id)),
            ("Saturation", self.check_neighborhood_saturation(parcel_id, event_id)),
            ("Double-knock", self.check_double_knock(parcel_id, event_id)),
        ]
        
        failures = [name for name, (ok, _) in checks if not ok]
        
        if failures:
            return False, f"Governance violations: {', '.join(failures)}"
        
        return True, "All checks passed"


class ComplianceReporter:
    """Generate compliance reports"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def report_tcpa_violations(self, event_id: str) -> dict:
        """Report TCPA violations"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) as violations,
                       COUNT(DISTINCT phone_number) as affected_numbers
                FROM tcpa_compliance
                WHERE event_id = %s AND sms_count_24h >= 3
            """, (event_id,))
            
            result = cursor.fetchone()
            
            return {
                'violations': result[0] or 0,
                'affected_numbers': result[1] or 0,
            }
        
        except Exception as e:
            logger.error(f"Error reporting TCPA violations: {e}")
            return {}
        finally:
            cursor.close()
    
    def report_saturation(self, event_id: str) -> list:
        """Report neighborhood saturation"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT neighborhood_id, saturation_ratio, contacted_parcels, total_parcels
                FROM neighborhood_saturation
                WHERE event_id = %s AND saturation_ratio > 0.5
                ORDER BY saturation_ratio DESC
            """, (event_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'neighborhood': row[0],
                    'saturation': row[1],
                    'contacted': row[2],
                    'total': row[3],
                })
            
            return results
        
        except Exception as e:
            logger.error(f"Error reporting saturation: {e}")
            return []
        finally:
            cursor.close()


if __name__ == '__main__':
    engine = GovernanceEngine()
    engine.connect()
    
    # Test TCPA check
    ok, msg = engine.check_tcpa_compliance('555-0000', 'test-event')
    print(f"TCPA: {'✅' if ok else '❌'} {msg}")
    
    # Test frequency check
    ok, msg = engine.check_frequency_cap('test-parcel', 'test-event')
    print(f"Frequency: {'✅' if ok else '❌'} {msg}")
    
    engine.close()
