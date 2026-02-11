"""
Earth-2 Ingestion Pipeline
Pulls hail fields from Earth-2 API, densifies onto DFW grid, writes to database.
"""

import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Earth2Ingestion:
    """
    Ingests Earth-2 hail fields and writes impact scores to database.
    """
    
    def __init__(self, db_host: str, db_name: str, db_user: str, db_password: str):
        """
        Initialize database connection.
        
        Args:
            db_host: PostgreSQL host
            db_name: Database name
            db_user: Database user
            db_password: Database password
        """
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.conn = None
    
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host=self.db_host,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
            )
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Closed database connection")
    
    def ingest_hail_field(
        self,
        event_id: str,
        hail_field: np.ndarray,
        grid_bounds: Tuple[float, float, float, float],  # (min_lat, max_lat, min_lon, max_lon)
        timestamp: datetime,
    ) -> int:
        """
        Ingest a hail field from Earth-2 and write impact scores to database.
        
        Args:
            event_id: UUID of the event
            hail_field: 2D numpy array of hail intensity (mm)
            grid_bounds: (min_lat, max_lat, min_lon, max_lon)
            timestamp: Timestamp of the hail field
        
        Returns:
            Number of parcels scored
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get all parcels in DFW
            cursor.execute("""
                SELECT id, ST_X(geometry) as lon, ST_Y(geometry) as lat
                FROM parcels
                WHERE zip_code LIKE '750%'  -- DFW ZIPs
                LIMIT 10000
            """)
            parcels = cursor.fetchall()
            logger.info(f"Found {len(parcels)} parcels in DFW")
            
            # Map each parcel to hail field grid
            impact_scores = []
            for parcel_id, lon, lat in parcels:
                hail_intensity = self._interpolate_hail_at_point(
                    lat, lon, hail_field, grid_bounds
                )
                
                if hail_intensity > 0:
                    impact_scores.append((
                        event_id,
                        parcel_id,
                        hail_intensity,
                        timestamp,
                    ))
            
            # Batch insert impact scores
            if impact_scores:
                execute_values(
                    cursor,
                    """
                    INSERT INTO impact_scores (event_id, parcel_id, hail_intensity_mm, created_at)
                    VALUES %s
                    ON CONFLICT (event_id, parcel_id) DO UPDATE
                    SET hail_intensity_mm = EXCLUDED.hail_intensity_mm,
                        updated_at = NOW()
                    """,
                    impact_scores,
                )
                self.conn.commit()
                logger.info(f"Ingested {len(impact_scores)} impact scores")
            
            return len(impact_scores)
        
        except Exception as e:
            logger.error(f"Error ingesting hail field: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _interpolate_hail_at_point(
        self,
        lat: float,
        lon: float,
        hail_field: np.ndarray,
        grid_bounds: Tuple[float, float, float, float],
    ) -> float:
        """
        Interpolate hail intensity at a specific lat/lon point.
        Uses bilinear interpolation.
        
        Args:
            lat: Latitude
            lon: Longitude
            hail_field: 2D numpy array of hail intensity
            grid_bounds: (min_lat, max_lat, min_lon, max_lon)
        
        Returns:
            Interpolated hail intensity (mm)
        """
        
        min_lat, max_lat, min_lon, max_lon = grid_bounds
        
        # Check if point is within bounds
        if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            return 0.0
        
        # Map lat/lon to grid indices
        grid_height, grid_width = hail_field.shape
        
        # Normalize to [0, 1]
        lat_norm = (lat - min_lat) / (max_lat - min_lat)
        lon_norm = (lon - min_lon) / (max_lon - min_lon)
        
        # Map to grid indices
        row = lat_norm * (grid_height - 1)
        col = lon_norm * (grid_width - 1)
        
        # Bilinear interpolation
        row_low = int(np.floor(row))
        row_high = int(np.ceil(row))
        col_low = int(np.floor(col))
        col_high = int(np.ceil(col))
        
        # Clamp to grid bounds
        row_low = max(0, min(row_low, grid_height - 1))
        row_high = max(0, min(row_high, grid_height - 1))
        col_low = max(0, min(col_low, grid_width - 1))
        col_high = max(0, min(col_high, grid_width - 1))
        
        # Get corner values
        v00 = hail_field[row_low, col_low]
        v01 = hail_field[row_low, col_high]
        v10 = hail_field[row_high, col_low]
        v11 = hail_field[row_high, col_high]
        
        # Interpolation weights
        row_frac = row - row_low
        col_frac = col - col_low
        
        # Bilinear interpolation
        v0 = v00 * (1 - col_frac) + v01 * col_frac
        v1 = v10 * (1 - col_frac) + v11 * col_frac
        value = v0 * (1 - row_frac) + v1 * row_frac
        
        return float(value)
    
    def update_impact_scores_with_sii(self, event_id: str) -> int:
        """
        Update impact_scores table with SII scores based on hail intensity and roof properties.
        
        Args:
            event_id: UUID of the event
        
        Returns:
            Number of scores updated
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Import SII scorer
            from sii_scorer import SIIScorer
            scorer = SIIScorer()
            
            # Get all impact scores for this event
            cursor.execute("""
                SELECT is.id, is.hail_intensity_mm, p.roof_material, p.roof_age_years
                FROM impact_scores is
                JOIN parcels p ON is.parcel_id = p.id
                WHERE is.event_id = %s
                AND is.sii_score IS NULL
                LIMIT 10000
            """, (event_id,))
            
            scores = cursor.fetchall()
            logger.info(f"Updating {len(scores)} impact scores with SII")
            
            updates = []
            for score_id, hail_mm, roof_material, roof_age in scores:
                result = scorer.score(
                    hail_intensity_mm=hail_mm,
                    roof_material=roof_material or 'asphalt',
                    roof_age_years=roof_age or 10,
                )
                updates.append((
                    result['sii_score'],
                    result['damage_probability'],
                    score_id,
                ))
            
            # Batch update
            if updates:
                execute_values(
                    cursor,
                    """
                    UPDATE impact_scores
                    SET sii_score = data.sii_score,
                        damage_probability = data.damage_probability,
                        updated_at = NOW()
                    FROM (VALUES %s) AS data(sii_score, damage_probability, id)
                    WHERE impact_scores.id = data.id
                    """,
                    updates,
                )
                self.conn.commit()
                logger.info(f"Updated {len(updates)} SII scores")
            
            return len(updates)
        
        except Exception as e:
            logger.error(f"Error updating SII scores: {e}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()


# Example usage
if __name__ == '__main__':
    # Initialize ingestion pipeline
    ingestion = Earth2Ingestion(
        db_host='localhost',
        db_name='stormops',
        db_user='postgres',
        db_password='password',
    )
    
    # Mock hail field (1km resolution, DFW bounds)
    # DFW bounds: ~32.5-33.5°N, ~-97.5--96.5°W
    hail_field = np.random.uniform(0, 70, size=(100, 100))  # 0-70mm hail
    grid_bounds = (32.5, 33.5, -97.5, -96.5)
    
    # Ingest
    ingestion.connect()
    try:
        count = ingestion.ingest_hail_field(
            event_id='test-event-1',
            hail_field=hail_field,
            grid_bounds=grid_bounds,
            timestamp=datetime.now(),
        )
        print(f"Ingested {count} impact scores")
        
        # Update with SII
        sii_count = ingestion.update_impact_scores_with_sii('test-event-1')
        print(f"Updated {sii_count} SII scores")
    finally:
        ingestion.close()
