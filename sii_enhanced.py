"""
Enhanced SII Model
Incorporates roof attributes, property data, and external enrichment
"""

import psycopg2
import logging
from sii_scorer import SIIScorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class EnhancedSIIScorer:
    """SII with enrichment factors"""
    
    def __init__(self):
        self.base_scorer = SIIScorer()
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def score_parcel(self, parcel_id: str, hail_intensity_mm: float) -> dict:
        """Score parcel with enrichment factors"""
        cursor = self.conn.cursor()
        
        try:
            # Get base roof attributes
            cursor.execute("""
                SELECT roof_material, roof_age_years, roof_area_sqft, roof_complexity
                FROM roof_attributes WHERE parcel_id = %s
            """, (parcel_id,))
            
            roof_result = cursor.fetchone()
            if not roof_result:
                # Fallback to base scoring
                return self.base_scorer.score(hail_intensity_mm)
            
            roof_material, roof_age, roof_area, roof_complexity = roof_result
            
            # Get property attributes
            cursor.execute("""
                SELECT assessed_value_usd, owner_occupied, building_use
                FROM property_attributes WHERE parcel_id = %s
            """, (parcel_id,))
            
            prop_result = cursor.fetchone()
            assessed_value, owner_occupied, building_use = prop_result if prop_result else (0, True, 'residential')
            
            # Get external enrichment
            cursor.execute("""
                SELECT flood_zone, wildfire_risk_score, credit_proxy_score
                FROM external_enrichment WHERE parcel_id = %s
            """, (parcel_id,))
            
            enrichment_result = cursor.fetchone()
            flood_zone, wildfire_risk, credit_score = enrichment_result if enrichment_result else ('X', 0, 0.5)
            
            # Base SII
            base_result = self.base_scorer.score(hail_intensity_mm, roof_material, roof_age)
            base_sii = base_result['sii_score']
            
            # Adjustments
            multiplier = 1.0
            
            # Roof complexity adjustment
            if roof_complexity == 'complex':
                multiplier *= 1.15
            elif roof_complexity == 'simple':
                multiplier *= 0.85
            
            # Property value adjustment (higher value = more likely to claim)
            if assessed_value > 500000:
                multiplier *= 1.1
            elif assessed_value < 250000:
                multiplier *= 0.9
            
            # Owner-occupied adjustment (more likely to claim)
            if owner_occupied:
                multiplier *= 1.05
            
            # Flood zone adjustment (flood risk = less roof damage claim priority)
            if flood_zone in ['AE', 'A']:
                multiplier *= 0.9
            
            # Wildfire risk adjustment
            if wildfire_risk > 0.7:
                multiplier *= 0.85
            
            # Credit proxy adjustment (higher credit = more likely to claim)
            multiplier *= (0.8 + credit_score * 0.4)
            
            # Enhanced SII
            enhanced_sii = min(100, base_sii * multiplier)
            
            # Estimate claim value based on roof area and property value
            estimated_claim = (roof_area * 10) + (assessed_value * 0.05)
            
            return {
                'sii_score': round(enhanced_sii, 1),
                'base_sii_score': round(base_sii, 1),
                'multiplier': round(multiplier, 2),
                'estimated_claim_value': round(estimated_claim, 0),
                'roof_material': roof_material,
                'roof_age_years': roof_age,
                'assessed_value': assessed_value,
                'owner_occupied': owner_occupied,
            }
        
        except Exception as e:
            logger.error(f"Error scoring parcel: {e}")
            return self.base_scorer.score(hail_intensity_mm)
        finally:
            cursor.close()


class ResponseTimingModel:
    """Model conversion decay over time"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def get_conversion_rate(self, event_id: str, severity_band: str, hours_since_hail: int) -> float:
        """Get conversion rate for given time since hail"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT conversion_rate FROM response_timing
                WHERE event_id = %s AND severity_band = %s
                AND hours_since_hail = %s
            """, (event_id, severity_band, hours_since_hail))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            # Estimate decay curve if not in DB
            # Conversion peaks at 6-12 hours, decays after 48h
            if hours_since_hail < 6:
                return 0.3
            elif hours_since_hail < 12:
                return 0.5
            elif hours_since_hail < 24:
                return 0.4
            elif hours_since_hail < 48:
                return 0.25
            else:
                return 0.1
        
        except Exception as e:
            logger.error(f"Error getting conversion rate: {e}")
            return 0.2
        finally:
            cursor.close()


if __name__ == '__main__':
    scorer = EnhancedSIIScorer()
    scorer.connect()
    
    # Test enhanced scoring
    result = scorer.score_parcel('test-parcel-1', 50)
    print(f"Enhanced SII: {result['sii_score']}")
    print(f"Base SII: {result.get('base_sii_score', 'N/A')}")
    print(f"Multiplier: {result.get('multiplier', 'N/A')}")
    print(f"Est. Claim: ${result.get('estimated_claim_value', 0):,.0f}")
    
    scorer.close()
