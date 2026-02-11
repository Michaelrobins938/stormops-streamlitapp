"""
Impact Report Generator
Creates physics-backed reports for high-SII roofs.
"""

import psycopg2
import uuid
import json
from datetime import datetime
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImpactReportGenerator:
    """
    Generates physics-backed Impact Reports for roofs.
    """
    
    def __init__(self, db_host='localhost', db_name='stormops', db_user='postgres', db_password='password'):
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.conn = None
    
    def connect(self):
        """Connect to database."""
        self.conn = psycopg2.connect(
            host=self.db_host,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def generate_report(
        self,
        event_id: str,
        parcel_id: str,
        hail_intensity_mm: float,
        sii_score: float,
        damage_probability: float,
        roof_material: str,
        roof_age_years: int,
    ) -> Optional[str]:
        """
        Generate an Impact Report for a parcel.
        
        Args:
            event_id: Event ID
            parcel_id: Parcel ID
            hail_intensity_mm: Hail intensity in mm
            sii_score: SII score (0-100)
            damage_probability: Damage probability (0-1)
            roof_material: Roof material type
            roof_age_years: Roof age in years
        
        Returns:
            Report ID if successful
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Convert hail to inches
            hail_inches = hail_intensity_mm / 25.4
            
            # Estimate claim value based on SII and roof area (mock: 2000 sq ft avg)
            roof_area_sqft = 2000
            cost_per_sqft = 5  # $5 per sq ft for roofing
            base_replacement_cost = roof_area_sqft * cost_per_sqft
            estimated_claim_value = int(base_replacement_cost * damage_probability)
            
            # Generate report content
            report_data = {
                'event_id': event_id,
                'parcel_id': parcel_id,
                'generated_at': datetime.now().isoformat(),
                'hail_size': {
                    'mm': round(hail_intensity_mm, 1),
                    'inches': round(hail_inches, 2),
                    'description': self._hail_size_description(hail_inches),
                },
                'roof_info': {
                    'material': roof_material,
                    'age_years': roof_age_years,
                    'area_sqft': roof_area_sqft,
                },
                'damage_assessment': {
                    'sii_score': round(sii_score, 1),
                    'damage_probability': round(damage_probability, 3),
                    'damage_level': self._damage_level(sii_score),
                    'expected_damage_type': self._expected_damage_type(roof_material, hail_inches),
                },
                'financial_impact': {
                    'base_replacement_cost': base_replacement_cost,
                    'estimated_claim_value': estimated_claim_value,
                    'deductible_assumption': 1000,
                    'net_claim_value': max(0, estimated_claim_value - 1000),
                },
                'recommendations': self._generate_recommendations(sii_score, damage_probability),
            }
            
            # Save to database
            report_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO impact_reports (
                    id, event_id, parcel_id, hail_size_inches, damage_probability,
                    estimated_claim_value_usd, report_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id, parcel_id) DO UPDATE
                SET report_json = EXCLUDED.report_json,
                    updated_at = NOW()
            """, (
                report_id,
                event_id,
                parcel_id,
                hail_inches,
                damage_probability,
                estimated_claim_value,
                json.dumps(report_data),
            ))
            
            self.conn.commit()
            logger.info(f"Generated impact report: {report_id}")
            return report_id
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            self.conn.rollback()
            return None
        finally:
            cursor.close()
    
    def generate_batch_reports(
        self,
        event_id: str,
        sii_min: float = 75,
    ) -> int:
        """
        Generate Impact Reports for all high-SII parcels in an event.
        
        Args:
            event_id: Event ID
            sii_min: Minimum SII threshold
        
        Returns:
            Number of reports generated
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get all high-SII parcels
            cursor.execute("""
                SELECT is.id, is.parcel_id, is.hail_intensity_mm, is.sii_score, 
                       is.damage_probability, p.roof_material, p.roof_age_years
                FROM impact_scores is
                JOIN parcels p ON is.parcel_id = p.id
                WHERE is.event_id = %s AND is.sii_score >= %s
                AND NOT EXISTS (
                    SELECT 1 FROM impact_reports ir
                    WHERE ir.event_id = %s AND ir.parcel_id = is.parcel_id
                )
                LIMIT 1000
            """, (event_id, sii_min, event_id))
            
            parcels = cursor.fetchall()
            logger.info(f"Generating {len(parcels)} impact reports")
            
            count = 0
            for parcel in parcels:
                report_id = self.generate_report(
                    event_id=event_id,
                    parcel_id=parcel[1],
                    hail_intensity_mm=parcel[2],
                    sii_score=parcel[3],
                    damage_probability=parcel[4],
                    roof_material=parcel[5] or 'asphalt',
                    roof_age_years=parcel[6] or 10,
                )
                if report_id:
                    count += 1
            
            logger.info(f"Generated {count} impact reports")
            return count
        
        except Exception as e:
            logger.error(f"Error generating batch reports: {e}")
            return 0
        finally:
            cursor.close()
    
    def get_report(self, report_id: str) -> Optional[Dict]:
        """
        Retrieve an Impact Report.
        
        Args:
            report_id: Report ID
        
        Returns:
            Report data dict
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT report_json FROM impact_reports WHERE id = %s
            """, (report_id,))
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
        
        except Exception as e:
            logger.error(f"Error retrieving report: {e}")
            return None
        finally:
            cursor.close()
    
    def _hail_size_description(self, hail_inches: float) -> str:
        """Describe hail size."""
        if hail_inches < 0.5:
            return "Pea-sized"
        elif hail_inches < 0.75:
            return "Marble-sized"
        elif hail_inches < 1.0:
            return "Penny-sized"
        elif hail_inches < 1.5:
            return "Quarter-sized"
        elif hail_inches < 2.0:
            return "Golf ball-sized"
        else:
            return "Baseball-sized or larger"
    
    def _damage_level(self, sii_score: float) -> str:
        """Classify damage level."""
        if sii_score < 20:
            return "Minimal"
        elif sii_score < 40:
            return "Light"
        elif sii_score < 60:
            return "Moderate"
        elif sii_score < 80:
            return "Severe"
        else:
            return "Catastrophic"
    
    def _expected_damage_type(self, roof_material: str, hail_inches: float) -> str:
        """Describe expected damage type."""
        if roof_material.lower() == 'asphalt':
            if hail_inches < 1.0:
                return "Granule loss, minor bruising"
            elif hail_inches < 1.5:
                return "Significant granule loss, bruising, potential leaks"
            else:
                return "Severe damage, likely replacement needed"
        elif roof_material.lower() == 'metal':
            if hail_inches < 1.5:
                return "Denting, cosmetic damage"
            else:
                return "Severe denting, potential structural damage"
        elif roof_material.lower() == 'tile':
            if hail_inches < 1.5:
                return "Cracking, minor breakage"
            else:
                return "Significant breakage, replacement needed"
        else:
            return "Potential damage, inspection recommended"
    
    def _generate_recommendations(self, sii_score: float, damage_probability: float) -> list:
        """Generate recommendations."""
        recommendations = []
        
        if damage_probability > 0.8:
            recommendations.append("Immediate inspection recommended")
            recommendations.append("Contact homeowner within 24 hours")
        elif damage_probability > 0.5:
            recommendations.append("Schedule inspection within 48 hours")
            recommendations.append("Prepare claim documentation")
        else:
            recommendations.append("Monitor for additional damage")
        
        if sii_score > 80:
            recommendations.append("High priority for claims processing")
            recommendations.append("Consider expedited adjuster dispatch")
        
        recommendations.append("Document all damage with photos/video")
        recommendations.append("Provide homeowner with Impact Report")
        
        return recommendations


# Example usage
if __name__ == '__main__':
    gen = ImpactReportGenerator()
    gen.connect()
    
    try:
        # Generate a single report
        report_id = gen.generate_report(
            event_id='test-event-1',
            parcel_id='test-parcel-1',
            hail_intensity_mm=50,
            sii_score=75,
            damage_probability=0.85,
            roof_material='asphalt',
            roof_age_years=15,
        )
        
        if report_id:
            print(f"Generated report: {report_id}")
            
            # Retrieve and display
            report = gen.get_report(report_id)
            print(f"\nReport content:")
            print(json.dumps(report, indent=2))
    
    finally:
        gen.close()
