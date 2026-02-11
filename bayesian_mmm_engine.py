"""
Bayesian Media Mix Modeling + Market Saturation Engine
Weibull adstock decay + Hill function saturation
"""

import psycopg2
import numpy as np
import logging
from scipy.special import gamma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class BayesianMMM:
    """Bayesian Media Mix Modeling"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def weibull_adstock(self, t: float, decay_rate: float, shape: float) -> float:
        """Weibull adstock decay function"""
        if t <= 0:
            return 1.0
        return np.exp(-decay_rate * (t ** shape))
    
    def hill_saturation(self, x: float, k: float, s: float) -> float:
        """Hill function for saturation"""
        return (x ** s) / (k ** s + x ** s)
    
    def compute_adstock_decay(self, event_id: str, zip_code: str):
        """Compute Weibull adstock decay for storm event"""
        logger.info(f"Computing adstock decay for {zip_code}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get event timestamp
            cursor.execute("""
                SELECT event_date FROM events WHERE id = %s
            """, (event_id,))
            
            result = cursor.fetchone()
            if not result:
                return
            
            event_date = result[0]
            
            # Compute decay for each channel
            channels = ['sms', 'phone', 'door_knock', 'email']
            
            for channel in channels:
                # Mock Weibull parameters (in practice, fit from data)
                decay_rate = np.random.uniform(0.1, 0.5)
                shape = np.random.uniform(0.5, 2.0)
                
                # Compute half-life (when adstock = 0.5)
                half_life = (np.log(2) / decay_rate) ** (1 / shape)
                
                cursor.execute("""
                    INSERT INTO bayesian_mmm_params (
                        event_id, zip_code, channel, adstock_decay_rate,
                        adstock_shape, baseline_conversion, channel_elasticity
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id, zip_code, channel) DO UPDATE
                    SET adstock_decay_rate = EXCLUDED.adstock_decay_rate
                """, (
                    event_id, zip_code, channel, decay_rate, shape,
                    np.random.uniform(0.05, 0.15), np.random.uniform(0.5, 1.5)
                ))
            
            self.conn.commit()
            logger.info(f"Computed adstock decay for {zip_code}")
            
        except Exception as e:
            logger.error(f"Error computing adstock: {e}")
            self.conn.rollback()
        finally:
            cursor.close()


class MarketSaturationEngine:
    """Market saturation tracking with Hill functions"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def compute_saturation(self, event_id: str, neighborhood_id: str):
        """Compute market saturation using Hill function"""
        logger.info(f"Computing saturation for {neighborhood_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get canvassing density
            cursor.execute("""
                SELECT COUNT(*) FROM leads
                WHERE event_id = %s AND parcel_id IN (
                    SELECT id FROM parcels WHERE zip_code = %s
                )
            """, (event_id, neighborhood_id))
            
            canvassing_count = cursor.fetchone()[0] or 0
            
            # Get total parcels
            cursor.execute("""
                SELECT COUNT(*) FROM parcels WHERE zip_code = %s
            """, (neighborhood_id,))
            
            total_parcels = cursor.fetchone()[0] or 1
            canvassing_density = canvassing_count / total_parcels
            
            # Get competitor density (mock)
            competitor_density = np.random.uniform(0.1, 0.5)
            
            # Hill function saturation (k=0.5, s=2)
            k = 0.5
            s = 2.0
            saturation_score = (canvassing_density ** s) / (k ** s + canvassing_density ** s)
            
            # Determine status
            if saturation_score > 0.8:
                saturation_status = 'saturated'
            elif saturation_score > 0.5:
                saturation_status = 'moderate'
            else:
                saturation_status = 'available'
            
            # Compute uplift delta (mock)
            uplift_delta = np.random.uniform(-0.2, 0.3)
            
            cursor.execute("""
                INSERT INTO market_saturation (
                    event_id, neighborhood_id, canvassing_density,
                    competitor_density, saturation_score, saturation_status,
                    uplift_delta
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id, neighborhood_id) DO UPDATE
                SET saturation_score = EXCLUDED.saturation_score,
                    saturation_status = EXCLUDED.saturation_status
            """, (
                event_id, neighborhood_id, canvassing_density,
                competitor_density, saturation_score, saturation_status,
                uplift_delta
            ))
            
            self.conn.commit()
            logger.info(f"Saturation: {saturation_status} ({saturation_score:.2f})")
            
        except Exception as e:
            logger.error(f"Error computing saturation: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def get_blue_ocean_zips(self, event_id: str, limit: int = 5) -> list:
        """Get unsaturated ZIPs for reallocation"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT neighborhood_id, saturation_score, uplift_delta
                FROM market_saturation
                WHERE event_id = %s AND saturation_status IN ('available', 'moderate')
                ORDER BY uplift_delta DESC
                LIMIT %s
            """, (event_id, limit))
            
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} blue ocean ZIPs")
            return results
            
        except Exception as e:
            logger.error(f"Error getting blue ocean ZIPs: {e}")
            return []
        finally:
            cursor.close()


if __name__ == '__main__':
    mmm = BayesianMMM()
    mmm.connect()
    mmm.compute_adstock_decay('event-1', '75034')
    mmm.close()
    
    saturation = MarketSaturationEngine()
    saturation.connect()
    saturation.compute_saturation('event-1', '75034')
    blue_ocean = saturation.get_blue_ocean_zips('event-1')
    print(f"Blue ocean ZIPs: {blue_ocean}")
    saturation.close()
