"""
Health check for StormOps infrastructure
"""

import psycopg2
import requests
import logging
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthCheck:
    """Check system health"""
    
    @staticmethod
    def check_database():
        """Check database connectivity"""
        try:
            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True, "OK"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def check_tables():
        """Check database tables"""
        try:
            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
            )
            cursor = conn.cursor()
            
            tables = ['events', 'parcels', 'impact_scores', 'leads', 'routes', 'proposals']
            missing = []
            
            for table in tables:
                cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
                if cursor.fetchone() is None:
                    missing.append(table)
            
            cursor.close()
            conn.close()
            
            if missing:
                return False, f"Missing tables: {', '.join(missing)}"
            return True, "All tables OK"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def check_data_freshness():
        """Check if data is recent"""
        try:
            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
            )
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT MAX(updated_at) FROM events WHERE status = 'active'
            """)
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result and result[0]:
                age_seconds = (datetime.now() - result[0]).total_seconds()
                if age_seconds > 3600:  # 1 hour
                    return False, f"Data is {age_seconds / 60:.0f} minutes old"
                return True, f"Data is {age_seconds / 60:.0f} minutes old"
            return False, "No active events"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def check_api():
        """Check API gateway"""
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                return True, "OK"
            return False, f"Status {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def check_all():
        """Run all health checks"""
        logger.info("=" * 80)
        logger.info("STORMOPS HEALTH CHECK")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {datetime.now().isoformat()}\n")
        
        checks = [
            ("Database", HealthCheck.check_database),
            ("Tables", HealthCheck.check_tables),
            ("Data Freshness", HealthCheck.check_data_freshness),
            ("API Gateway", HealthCheck.check_api),
        ]
        
        results = []
        for name, check in checks:
            ok, msg = check()
            status = "✅" if ok else "❌"
            logger.info(f"{status} {name}: {msg}")
            results.append((name, ok))
        
        logger.info("\n" + "=" * 80)
        
        all_ok = all(ok for _, ok in results)
        if all_ok:
            logger.info("✅ ALL SYSTEMS OK")
        else:
            logger.warning("⚠️  SOME SYSTEMS DOWN")
        
        logger.info("=" * 80)
        
        return all_ok


if __name__ == '__main__':
    HealthCheck.check_all()
