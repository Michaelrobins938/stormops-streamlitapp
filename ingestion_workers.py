"""
StormOps Ingestion Service Workers
Modular ETL jobs for public data sources
"""

import requests
import psycopg2
import csv
import json
from datetime import datetime, timedelta
from io import StringIO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class NOAAStormWorker:
    """Ingest NOAA Storm Events"""
    
    def __init__(self):
        self.base_url = "https://www.ncei.noaa.gov/pub/data/swdiab/CSV"
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def ingest_year(self, year):
        """Ingest NOAA Storm Events for a year"""
        logger.info(f"Ingesting NOAA Storm Events for {year}")
        
        try:
            # Download CSV
            url = f"{self.base_url}/StormEvents_details-ftp_v1.0_{year}_c{year}0101_{year}1231.csv.gz"
            logger.info(f"Downloading {url}")
            
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"Failed to download {year}: {response.status_code}")
                return 0
            
            # Parse CSV
            import gzip
            csv_data = gzip.decompress(response.content).decode('utf-8')
            reader = csv.DictReader(StringIO(csv_data))
            
            cursor = self.conn.cursor()
            count = 0
            
            for row in reader:
                # Filter for hail/wind events in TX
                if row.get('STATE') != 'TEXAS':
                    continue
                
                event_type = row.get('EVENT_TYPE', '').upper()
                if 'HAIL' not in event_type and 'WIND' not in event_type:
                    continue
                
                # Parse hail size
                hail_size_mm = 0
                if 'HAIL' in event_type and row.get('MAGNITUDE'):
                    try:
                        hail_size_mm = float(row['MAGNITUDE']) * 25.4  # inches to mm
                    except:
                        pass
                
                # Insert
                cursor.execute("""
                    INSERT INTO storm_events_raw (
                        event_id, event_type, event_date, state, county, 
                        lat, lon, hail_size_mm, damage_cost, source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                """, (
                    row.get('EVENT_ID'),
                    event_type,
                    row.get('BEGIN_DATE_TIME'),
                    row.get('STATE'),
                    row.get('COUNTY_FIPS'),
                    float(row.get('BEGIN_LAT', 0)),
                    float(row.get('BEGIN_LON', 0)),
                    hail_size_mm,
                    row.get('DAMAGE_PROPERTY', 0),
                    'NOAA_NCEI',
                ))
                count += 1
            
            self.conn.commit()
            cursor.close()
            logger.info(f"Ingested {count} events for {year}")
            return count
        
        except Exception as e:
            logger.error(f"Error ingesting {year}: {e}")
            return 0


class OpenMeteoWorker:
    """Ingest Open-Meteo forecasts"""
    
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def ingest_sector_forecast(self, sector_id, lat, lon):
        """Ingest forecast for a sector"""
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'hourly': 'precipitation,windspeed_10m,cape',
                'timezone': 'America/Chicago',
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch forecast for {sector_id}")
                return 0
            
            data = response.json()
            hourly = data.get('hourly', {})
            
            cursor = self.conn.cursor()
            count = 0
            
            for i, time_str in enumerate(hourly.get('time', [])):
                cursor.execute("""
                    INSERT INTO sector_forecasts_raw (
                        sector_id, forecast_time, precip_mm, wind_gust_ms, cape,
                        ingested_at
                    ) VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (sector_id, forecast_time) DO UPDATE
                    SET precip_mm = EXCLUDED.precip_mm,
                        wind_gust_ms = EXCLUDED.wind_gust_ms,
                        cape = EXCLUDED.cape
                """, (
                    sector_id,
                    time_str,
                    hourly.get('precipitation', [None])[i],
                    hourly.get('windspeed_10m', [None])[i],
                    hourly.get('cape', [None])[i],
                ))
                count += 1
            
            self.conn.commit()
            cursor.close()
            logger.info(f"Ingested {count} forecast hours for sector {sector_id}")
            return count
        
        except Exception as e:
            logger.error(f"Error ingesting forecast for {sector_id}: {e}")
            return 0


class NWSAlertsWorker:
    """Ingest NWS alerts"""
    
    def __init__(self):
        self.base_url = "https://api.weather.gov/alerts/active"
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def ingest_alerts(self):
        """Ingest active NWS alerts for DFW"""
        try:
            params = {
                'point': '32.7767,-96.7970',  # Dallas center
                'status': 'actual',
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch NWS alerts")
                return 0
            
            data = response.json()
            features = data.get('features', [])
            
            cursor = self.conn.cursor()
            count = 0
            
            for feature in features:
                props = feature.get('properties', {})
                event = props.get('event', '').upper()
                
                # Filter for severe weather
                if 'HAIL' not in event and 'WIND' not in event and 'TORNADO' not in event:
                    continue
                
                cursor.execute("""
                    INSERT INTO weather_alerts_raw (
                        alert_id, event_type, headline, description,
                        effective, expires, severity, ingested_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (alert_id) DO NOTHING
                """, (
                    props.get('id'),
                    event,
                    props.get('headline'),
                    props.get('description'),
                    props.get('effective'),
                    props.get('expires'),
                    props.get('severity'),
                ))
                count += 1
            
            self.conn.commit()
            cursor.close()
            logger.info(f"Ingested {count} NWS alerts")
            return count
        
        except Exception as e:
            logger.error(f"Error ingesting NWS alerts: {e}")
            return 0


class FEMAHailWorker:
    """Ingest FEMA hailstorms"""
    
    def __init__(self):
        self.feature_service_url = "https://services.arcgis.com/P3ePLMYPQB8yQe5h/arcgis/rest/services/Hailstorms_in_the_U_S_/FeatureServer/0/query"
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def ingest_hailstorms(self):
        """Ingest FEMA hailstorms for DFW"""
        try:
            # Query DFW bounding box
            where = "1=1"  # Get all
            params = {
                'where': where,
                'outFields': '*',
                'returnGeometry': 'true',
                'f': 'json',
                'resultRecordCount': 1000,
            }
            
            response = requests.get(self.feature_service_url, params=params, timeout=30)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch FEMA hailstorms")
                return 0
            
            data = response.json()
            features = data.get('features', [])
            
            cursor = self.conn.cursor()
            count = 0
            
            for feature in features:
                props = feature.get('attributes', {})
                geom = feature.get('geometry', {})
                
                cursor.execute("""
                    INSERT INTO hail_footprints_raw (
                        hail_id, event_date, severity, source, ingested_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (hail_id) DO NOTHING
                """, (
                    props.get('OBJECTID'),
                    props.get('EVENT_DATE'),
                    props.get('SEVERITY'),
                    'FEMA',
                ))
                count += 1
            
            self.conn.commit()
            cursor.close()
            logger.info(f"Ingested {count} FEMA hailstorms")
            return count
        
        except Exception as e:
            logger.error(f"Error ingesting FEMA hailstorms: {e}")
            return 0


class IngestionOrchestrator:
    """Orchestrate all ingestion workers"""
    
    def run_all(self):
        """Run all ingestion jobs"""
        logger.info("=" * 80)
        logger.info("STORMOPS INGESTION SERVICE")
        logger.info("=" * 80)
        
        # NOAA Storm Events (last 5 years)
        noaa = NOAAStormWorker()
        noaa.connect()
        for year in range(2019, 2024):
            noaa.ingest_year(year)
        noaa.close()
        
        # Open-Meteo forecasts (DFW sectors)
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
        
        # NWS Alerts
        nws = NWSAlertsWorker()
        nws.connect()
        nws.ingest_alerts()
        nws.close()
        
        # FEMA Hailstorms
        fema = FEMAHailWorker()
        fema.connect()
        fema.ingest_hailstorms()
        fema.close()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ INGESTION COMPLETE")
        logger.info("=" * 80)


if __name__ == '__main__':
    orchestrator = IngestionOrchestrator()
    orchestrator.run_all()
