"""
Ingestion job scheduler (APScheduler)
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

from ingestion_workers import (
    NOAAStormWorker, OpenMeteoWorker, NWSAlertsWorker, FEMAHailWorker
)
from data_transforms import DataTransforms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IngestionScheduler:
    """Schedule ingestion jobs"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
    
    def schedule_jobs(self):
        """Schedule all ingestion jobs"""
        
        # NOAA Storm Events: daily at 2 AM
        self.scheduler.add_job(
            self._run_noaa_ingestion,
            CronTrigger(hour=2, minute=0),
            id='noaa_ingestion',
            name='NOAA Storm Events Ingestion',
        )
        
        # Open-Meteo Forecasts: every 15 minutes
        self.scheduler.add_job(
            self._run_meteo_ingestion,
            'interval',
            minutes=15,
            id='meteo_ingestion',
            name='Open-Meteo Forecast Ingestion',
        )
        
        # NWS Alerts: every 5 minutes
        self.scheduler.add_job(
            self._run_nws_ingestion,
            'interval',
            minutes=5,
            id='nws_ingestion',
            name='NWS Alerts Ingestion',
        )
        
        # FEMA Hailstorms: daily at 3 AM
        self.scheduler.add_job(
            self._run_fema_ingestion,
            CronTrigger(hour=3, minute=0),
            id='fema_ingestion',
            name='FEMA Hailstorms Ingestion',
        )
        
        # Data Transforms: every hour
        self.scheduler.add_job(
            self._run_transforms,
            'interval',
            hours=1,
            id='data_transforms',
            name='Data Transformations',
        )
        
        logger.info("Scheduled all ingestion jobs")
    
    def _run_noaa_ingestion(self):
        """Run NOAA ingestion"""
        logger.info("Running NOAA ingestion...")
        try:
            noaa = NOAAStormWorker()
            noaa.connect()
            noaa.ingest_year(2024)
            noaa.close()
        except Exception as e:
            logger.error(f"NOAA ingestion failed: {e}")
    
    def _run_meteo_ingestion(self):
        """Run Open-Meteo ingestion"""
        logger.info("Running Open-Meteo ingestion...")
        try:
            meteo = OpenMeteoWorker()
            meteo.connect()
            sectors = [
                ('sector_downtown', 32.7767, -96.7970),
                ('sector_north', 33.2000, -96.8000),
                ('sector_south', 32.5000, -96.8000),
            ]
            for sector_id, lat, lon in sectors:
                meteo.ingest_sector_forecast(sector_id, lat, lon)
            meteo.close()
        except Exception as e:
            logger.error(f"Open-Meteo ingestion failed: {e}")
    
    def _run_nws_ingestion(self):
        """Run NWS ingestion"""
        logger.info("Running NWS ingestion...")
        try:
            nws = NWSAlertsWorker()
            nws.connect()
            nws.ingest_alerts()
            nws.close()
        except Exception as e:
            logger.error(f"NWS ingestion failed: {e}")
    
    def _run_fema_ingestion(self):
        """Run FEMA ingestion"""
        logger.info("Running FEMA ingestion...")
        try:
            fema = FEMAHailWorker()
            fema.connect()
            fema.ingest_hailstorms()
            fema.close()
        except Exception as e:
            logger.error(f"FEMA ingestion failed: {e}")
    
    def _run_transforms(self):
        """Run data transforms"""
        logger.info("Running data transforms...")
        try:
            transforms = DataTransforms()
            transforms.run_all()
        except Exception as e:
            logger.error(f"Data transforms failed: {e}")
    
    def start(self):
        """Start scheduler"""
        self.schedule_jobs()
        self.scheduler.start()
        logger.info("Ingestion scheduler started")
    
    def stop(self):
        """Stop scheduler"""
        self.scheduler.shutdown()
        logger.info("Ingestion scheduler stopped")


if __name__ == '__main__':
    scheduler = IngestionScheduler()
    scheduler.start()
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
