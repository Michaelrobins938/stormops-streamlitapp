"""
Enrichment data loaders
Load roof attributes, property data, rep productivity, external enrichment
"""

import psycopg2
import logging
import random
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class RoofAttributeLoader:
    """Load roof attributes from permits/appraisals"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_mock_roof_data(self):
        """Load mock roof attributes for all parcels"""
        logger.info("Loading mock roof attributes...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM parcels LIMIT 5000")
            parcels = cursor.fetchall()
            
            for parcel_id, in parcels:
                roof_material = random.choice(['asphalt', 'metal', 'tile', 'composite'])
                roof_age = random.randint(5, 30)
                roof_area = random.randint(1500, 3500)
                roof_complexity = random.choice(['simple', 'moderate', 'complex'])
                replacement_cost = roof_area * random.uniform(8, 15)
                
                cursor.execute("""
                    INSERT INTO roof_attributes (
                        parcel_id, roof_material, roof_age_years, roof_area_sqft,
                        roof_complexity, estimated_replacement_cost_usd
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (parcel_id) DO NOTHING
                """, (
                    parcel_id, roof_material, roof_age, roof_area,
                    roof_complexity, replacement_cost
                ))
            
            self.conn.commit()
            logger.info(f"Loaded roof attributes for {len(parcels)} parcels")
            
        except Exception as e:
            logger.error(f"Error loading roof data: {e}")
            self.conn.rollback()
        finally:
            cursor.close()


class PropertyAttributeLoader:
    """Load property attributes"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_mock_property_data(self):
        """Load mock property attributes"""
        logger.info("Loading mock property attributes...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM parcels LIMIT 5000")
            parcels = cursor.fetchall()
            
            for parcel_id, in parcels:
                building_use = random.choice(['residential', 'commercial', 'mixed'])
                owner_occupied = random.choice([True, False])
                assessed_value = random.uniform(200000, 800000)
                value_band = 'high' if assessed_value > 500000 else 'medium' if assessed_value > 300000 else 'low'
                year_built = random.randint(1980, 2020)
                
                cursor.execute("""
                    INSERT INTO property_attributes (
                        parcel_id, building_use, owner_occupied, assessed_value_usd,
                        value_band, year_built
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (parcel_id) DO NOTHING
                """, (
                    parcel_id, building_use, owner_occupied, assessed_value,
                    value_band, year_built
                ))
            
            self.conn.commit()
            logger.info(f"Loaded property attributes for {len(parcels)} parcels")
            
        except Exception as e:
            logger.error(f"Error loading property data: {e}")
            self.conn.rollback()
        finally:
            cursor.close()


class RepProductivityLoader:
    """Load rep productivity metrics"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_mock_productivity(self, event_id: str):
        """Load mock rep productivity"""
        logger.info(f"Loading mock rep productivity for event {event_id}...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT rep_id FROM field_reps")
            reps = cursor.fetchall()
            
            for rep_id, in reps:
                inspections = random.randint(5, 20)
                estimates = int(inspections * random.uniform(0.6, 0.9))
                jobs = int(estimates * random.uniform(0.4, 0.7))
                avg_revenue = random.uniform(5000, 15000)
                close_rate = jobs / inspections if inspections > 0 else 0
                no_show_rate = random.uniform(0.05, 0.15)
                
                cursor.execute("""
                    INSERT INTO rep_productivity (
                        rep_id, event_id, inspections_completed, estimates_sent,
                        jobs_sold, avg_revenue_per_inspection_usd, close_rate,
                        no_show_rate, avg_stop_duration_minutes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (rep_id, event_id) DO NOTHING
                """, (
                    rep_id, event_id, inspections, estimates, jobs,
                    avg_revenue, close_rate, no_show_rate, 30
                ))
            
            self.conn.commit()
            logger.info(f"Loaded productivity for {len(reps)} reps")
            
        except Exception as e:
            logger.error(f"Error loading productivity: {e}")
            self.conn.rollback()
        finally:
            cursor.close()


class ChannelPerformanceLoader:
    """Load channel performance metrics"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_mock_channel_performance(self, event_id: str):
        """Load mock channel performance"""
        logger.info(f"Loading mock channel performance for event {event_id}...")
        
        cursor = self.conn.cursor()
        
        try:
            channels = ['sms', 'phone', 'door_knock']
            severity_bands = ['low', 'moderate', 'severe']
            
            for channel in channels:
                for severity in severity_bands:
                    contacts = random.randint(100, 500)
                    
                    # SMS has lower conversion, door-knock highest
                    if channel == 'sms':
                        conversion = random.uniform(0.05, 0.15)
                    elif channel == 'phone':
                        conversion = random.uniform(0.15, 0.30)
                    else:
                        conversion = random.uniform(0.25, 0.45)
                    
                    responses = int(contacts * conversion)
                    appointments = int(responses * random.uniform(0.6, 0.9))
                    
                    cursor.execute("""
                        INSERT INTO channel_performance (
                            event_id, channel, severity_band, contacts_sent,
                            responses, appointments_set, conversion_rate,
                            unsubscribe_rate, complaint_rate
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (event_id, channel, severity_band) DO NOTHING
                    """, (
                        event_id, channel, severity, contacts, responses,
                        appointments, conversion, random.uniform(0.01, 0.05),
                        random.uniform(0.001, 0.01)
                    ))
            
            self.conn.commit()
            logger.info(f"Loaded channel performance")
            
        except Exception as e:
            logger.error(f"Error loading channel performance: {e}")
            self.conn.rollback()
        finally:
            cursor.close()


class ExternalEnrichmentLoader:
    """Load external enrichment data"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_mock_enrichment(self):
        """Load mock external enrichment"""
        logger.info("Loading mock external enrichment...")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM parcels LIMIT 5000")
            parcels = cursor.fetchall()
            
            for parcel_id, in parcels:
                flood_zone = random.choice(['X', 'AE', 'A', 'D'])
                wildfire_risk = random.uniform(0, 1)
                income_band = random.choice(['low', 'medium', 'high'])
                credit_score = random.uniform(0.3, 0.9)
                competitor_permits = random.randint(0, 20)
                review_burst = random.randint(0, 10)
                
                cursor.execute("""
                    INSERT INTO external_enrichment (
                        parcel_id, flood_zone, wildfire_risk_score,
                        neighborhood_income_band, credit_proxy_score,
                        competitor_permit_count_12m, google_review_burst_30d
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (parcel_id) DO NOTHING
                """, (
                    parcel_id, flood_zone, wildfire_risk, income_band,
                    credit_score, competitor_permits, review_burst
                ))
            
            self.conn.commit()
            logger.info(f"Loaded enrichment for {len(parcels)} parcels")
            
        except Exception as e:
            logger.error(f"Error loading enrichment: {e}")
            self.conn.rollback()
        finally:
            cursor.close()


if __name__ == '__main__':
    # Load all enrichment data
    roof_loader = RoofAttributeLoader()
    roof_loader.connect()
    roof_loader.load_mock_roof_data()
    roof_loader.close()
    
    prop_loader = PropertyAttributeLoader()
    prop_loader.connect()
    prop_loader.load_mock_property_data()
    prop_loader.close()
    
    rep_loader = RepProductivityLoader()
    rep_loader.connect()
    rep_loader.load_mock_productivity('test-event-1')
    rep_loader.close()
    
    channel_loader = ChannelPerformanceLoader()
    channel_loader.connect()
    channel_loader.load_mock_channel_performance('test-event-1')
    channel_loader.close()
    
    enrichment_loader = ExternalEnrichmentLoader()
    enrichment_loader.connect()
    enrichment_loader.load_mock_enrichment()
    enrichment_loader.close()
    
    logger.info("✅ All enrichment data loaded")
