"""
Data transformation jobs: raw → normalized
"""

import psycopg2
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class DataTransforms:
    """Transform raw data into normalized tables"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def transform_storm_events(self):
        """Transform raw NOAA events to normalized"""
        logger.info("Transforming storm events...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO storm_events (
                    event_id, event_type, event_date, state, county,
                    lat, lon, hail_size_mm, damage_cost, source
                )
                SELECT 
                    event_id, event_type, event_date, state, county,
                    lat, lon, hail_size_mm, damage_cost, source
                FROM storm_events_raw
                WHERE event_id NOT IN (SELECT event_id FROM storm_events)
                ON CONFLICT (event_id) DO NOTHING
            """)
            
            self.conn.commit()
            count = cursor.rowcount
            logger.info(f"Transformed {count} storm events")
            return count
        
        except Exception as e:
            logger.error(f"Error transforming storm events: {e}")
            self.conn.rollback()
            return 0
        finally:
            cursor.close()
    
    def transform_forecasts(self):
        """Transform raw forecasts to normalized"""
        logger.info("Transforming forecasts...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO sector_forecasts (
                    sector_id, forecast_time, precip_mm, wind_gust_ms, cape
                )
                SELECT 
                    sector_id, forecast_time, precip_mm, wind_gust_ms, cape
                FROM sector_forecasts_raw
                ON CONFLICT (sector_id, forecast_time) DO UPDATE
                SET precip_mm = EXCLUDED.precip_mm,
                    wind_gust_ms = EXCLUDED.wind_gust_ms,
                    cape = EXCLUDED.cape
            """)
            
            self.conn.commit()
            count = cursor.rowcount
            logger.info(f"Transformed {count} forecast records")
            return count
        
        except Exception as e:
            logger.error(f"Error transforming forecasts: {e}")
            self.conn.rollback()
            return 0
        finally:
            cursor.close()
    
    def transform_alerts(self):
        """Transform raw alerts to normalized"""
        logger.info("Transforming alerts...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO weather_alerts (
                    alert_id, event_type, headline, description,
                    effective, expires, severity
                )
                SELECT 
                    alert_id, event_type, headline, description,
                    effective, expires, severity
                FROM weather_alerts_raw
                WHERE alert_id NOT IN (SELECT alert_id FROM weather_alerts)
                ON CONFLICT (alert_id) DO NOTHING
            """)
            
            self.conn.commit()
            count = cursor.rowcount
            logger.info(f"Transformed {count} alerts")
            return count
        
        except Exception as e:
            logger.error(f"Error transforming alerts: {e}")
            self.conn.rollback()
            return 0
        finally:
            cursor.close()
    
    def transform_hail_footprints(self):
        """Transform raw hail footprints to normalized"""
        logger.info("Transforming hail footprints...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO hail_footprints (
                    hail_id, event_date, severity, source
                )
                SELECT 
                    hail_id, event_date, severity, source
                FROM hail_footprints_raw
                WHERE hail_id NOT IN (SELECT hail_id FROM hail_footprints)
                ON CONFLICT (hail_id) DO NOTHING
            """)
            
            self.conn.commit()
            count = cursor.rowcount
            logger.info(f"Transformed {count} hail footprints")
            return count
        
        except Exception as e:
            logger.error(f"Error transforming hail footprints: {e}")
            self.conn.rollback()
            return 0
        finally:
            cursor.close()
    
    def run_all(self):
        """Run all transformations"""
        logger.info("=" * 80)
        logger.info("DATA TRANSFORMATION JOBS")
        logger.info("=" * 80)
        
        self.connect()
        
        try:
            self.transform_storm_events()
            self.transform_forecasts()
            self.transform_alerts()
            self.transform_hail_footprints()
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ TRANSFORMATIONS COMPLETE")
            logger.info("=" * 80)
        
        finally:
            self.close()


if __name__ == '__main__':
    transforms = DataTransforms()
    transforms.run_all()
