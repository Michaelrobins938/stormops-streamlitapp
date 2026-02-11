"""
Database migrations for StormOps
"""

import psycopg2
import logging
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Migration:
    """Database migrations"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def create_migrations_table(self):
        """Create migrations tracking table"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        self.conn.commit()
        cursor.close()
        logger.info("Created migrations table")
    
    def is_applied(self, name):
        """Check if migration is applied"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM migrations WHERE name = %s", (name,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    
    def mark_applied(self, name):
        """Mark migration as applied"""
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO migrations (name) VALUES (%s)", (name,))
        self.conn.commit()
        cursor.close()
    
    def migrate_001_add_impact_report_fields(self):
        """Add fields to impact_reports table"""
        if self.is_applied('001_add_impact_report_fields'):
            logger.info("Migration 001 already applied")
            return
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                ALTER TABLE impact_reports
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()
            """)
            self.conn.commit()
            self.mark_applied('001_add_impact_report_fields')
            logger.info("✅ Migration 001 applied")
        except Exception as e:
            logger.error(f"Migration 001 failed: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def migrate_002_add_proposal_indexes(self):
        """Add indexes to proposals table"""
        if self.is_applied('002_add_proposal_indexes'):
            logger.info("Migration 002 already applied")
            return
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_proposals_created_by ON proposals(created_by)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_proposals_approved_by ON proposals(approved_by)
            """)
            self.conn.commit()
            self.mark_applied('002_add_proposal_indexes')
            logger.info("✅ Migration 002 applied")
        except Exception as e:
            logger.error(f"Migration 002 failed: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def migrate_003_add_lead_fields(self):
        """Add fields to leads table"""
        if self.is_applied('003_add_lead_fields'):
            logger.info("Migration 003 already applied")
            return
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                ALTER TABLE leads
                ADD COLUMN IF NOT EXISTS first_contact_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS inspection_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS quote_at TIMESTAMP
            """)
            self.conn.commit()
            self.mark_applied('003_add_lead_fields')
            logger.info("✅ Migration 003 applied")
        except Exception as e:
            logger.error(f"Migration 003 failed: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def run_all(self):
        """Run all pending migrations"""
        logger.info("=" * 80)
        logger.info("RUNNING DATABASE MIGRATIONS")
        logger.info("=" * 80)
        
        self.connect()
        
        try:
            self.create_migrations_table()
            self.migrate_001_add_impact_report_fields()
            self.migrate_002_add_proposal_indexes()
            self.migrate_003_add_lead_fields()
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ ALL MIGRATIONS COMPLETE")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"Migration error: {e}")
        
        finally:
            self.close()


if __name__ == '__main__':
    migration = Migration()
    migration.run_all()
