#!/usr/bin/env python3
"""
StormOps Ingestion Service
Main entry point for all data ingestion jobs
"""

import click
import logging
from datetime import datetime

from ingestion_workers import IngestionOrchestrator
from data_transforms import DataTransforms
from data_quality import DataQuality
from ingestion_scheduler import IngestionScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """StormOps Ingestion Service"""
    pass


@cli.command()
def ingest_all():
    """Run all ingestion jobs once"""
    logger.info("Starting full ingestion cycle...")
    
    orchestrator = IngestionOrchestrator()
    orchestrator.run_all()
    
    transforms = DataTransforms()
    transforms.run_all()
    
    quality = DataQuality()
    quality.run_all()


@cli.command()
def ingest_noaa():
    """Ingest NOAA Storm Events"""
    from ingestion_workers import NOAAStormWorker
    
    worker = NOAAStormWorker()
    worker.connect()
    
    for year in range(2019, 2024):
        worker.ingest_year(year)
    
    worker.close()


@cli.command()
def ingest_forecasts():
    """Ingest Open-Meteo forecasts"""
    from ingestion_workers import OpenMeteoWorker
    
    worker = OpenMeteoWorker()
    worker.connect()
    
    sectors = [
        ('sector_downtown', 32.7767, -96.7970),
        ('sector_north', 33.2000, -96.8000),
        ('sector_south', 32.5000, -96.8000),
    ]
    
    for sector_id, lat, lon in sectors:
        worker.ingest_sector_forecast(sector_id, lat, lon)
    
    worker.close()


@cli.command()
def ingest_alerts():
    """Ingest NWS alerts"""
    from ingestion_workers import NWSAlertsWorker
    
    worker = NWSAlertsWorker()
    worker.connect()
    worker.ingest_alerts()
    worker.close()


@cli.command()
def ingest_hail():
    """Ingest FEMA hailstorms"""
    from ingestion_workers import FEMAHailWorker
    
    worker = FEMAHailWorker()
    worker.connect()
    worker.ingest_hailstorms()
    worker.close()


@cli.command()
def transform():
    """Run data transformations"""
    transforms = DataTransforms()
    transforms.run_all()


@cli.command()
def quality_check():
    """Run data quality checks"""
    quality = DataQuality()
    quality.run_all()


@cli.command()
def schedule():
    """Start ingestion scheduler"""
    logger.info("Starting ingestion scheduler...")
    
    scheduler = IngestionScheduler()
    scheduler.start()
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == '__main__':
    cli()
