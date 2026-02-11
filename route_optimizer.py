"""
Route Optimizer
Builds optimized canvassing routes using TSP-style optimization.
"""

import psycopg2
import uuid
from typing import List, Dict, Tuple
import math
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RouteOptimizer:
    """
    Builds optimized canvassing routes for field reps.
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
    
    def build_routes(
        self,
        event_id: str,
        zip_code: str,
        sii_min: float = 70,
        num_canvassers: int = 4,
    ) -> List[str]:
        """
        Build optimized routes for canvassers.
        
        Args:
            event_id: Event ID
            zip_code: Target ZIP code
            sii_min: Minimum SII threshold
            num_canvassers: Number of canvassers
        
        Returns:
            List of route IDs
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get high-SII parcels with coordinates
            cursor.execute("""
                SELECT p.id, ST_X(p.geometry) as lon, ST_Y(p.geometry) as lat, is.sii_score
                FROM impact_scores is
                JOIN parcels p ON is.parcel_id = p.id
                WHERE is.event_id = %s
                AND p.zip_code = %s
                AND is.sii_score >= %s
                ORDER BY is.sii_score DESC
                LIMIT 500
            """, (event_id, zip_code, sii_min))
            
            parcels = cursor.fetchall()
            logger.info(f"Found {len(parcels)} parcels for routing")
            
            if not parcels:
                logger.warning("No parcels found for routing")
                return []
            
            # Cluster parcels into routes using simple geographic clustering
            routes = self._cluster_parcels(parcels, num_canvassers)
            
            # Optimize each route using nearest-neighbor TSP
            route_ids = []
            for i, route_parcels in enumerate(routes):
                route_id = self._save_route(
                    event_id=event_id,
                    route_name=f"{zip_code}-Route-{i+1}",
                    parcels=route_parcels,
                    canvasser_id=f"canvasser-{i+1}",
                )
                if route_id:
                    route_ids.append(route_id)
            
            logger.info(f"Built {len(route_ids)} routes")
            return route_ids
        
        except Exception as e:
            logger.error(f"Error building routes: {e}")
            return []
        finally:
            cursor.close()
    
    def _cluster_parcels(self, parcels: List[Tuple], num_clusters: int) -> List[List[Tuple]]:
        """
        Cluster parcels into geographic groups using k-means-like approach.
        
        Args:
            parcels: List of (parcel_id, lon, lat, sii_score)
            num_clusters: Number of clusters
        
        Returns:
            List of parcel clusters
        """
        
        if len(parcels) <= num_clusters:
            return [[p] for p in parcels]
        
        # Simple clustering: sort by lat, then divide into num_clusters groups
        sorted_parcels = sorted(parcels, key=lambda p: (p[2], p[1]))  # Sort by lat, then lon
        cluster_size = len(sorted_parcels) // num_clusters
        
        clusters = []
        for i in range(num_clusters):
            start = i * cluster_size
            end = start + cluster_size if i < num_clusters - 1 else len(sorted_parcels)
            clusters.append(sorted_parcels[start:end])
        
        return clusters
    
    def _optimize_route_tsp(self, parcels: List[Tuple]) -> List[Tuple]:
        """
        Optimize route using nearest-neighbor TSP heuristic.
        
        Args:
            parcels: List of (parcel_id, lon, lat, sii_score)
        
        Returns:
            Optimized parcel sequence
        """
        
        if len(parcels) <= 1:
            return parcels
        
        # Start with highest SII parcel
        unvisited = list(parcels)
        visited = [max(unvisited, key=lambda p: p[3])]
        unvisited.remove(visited[0])
        
        # Nearest-neighbor: always go to closest unvisited parcel
        while unvisited:
            current = visited[-1]
            nearest = min(
                unvisited,
                key=lambda p: self._distance(current[1], current[2], p[1], p[2])
            )
            visited.append(nearest)
            unvisited.remove(nearest)
        
        return visited
    
    def _distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Calculate distance between two points (Haversine formula).
        
        Args:
            lon1, lat1: First point
            lon2, lat2: Second point
        
        Returns:
            Distance in km
        """
        
        R = 6371  # Earth radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _save_route(
        self,
        event_id: str,
        route_name: str,
        parcels: List[Tuple],
        canvasser_id: str,
    ) -> str:
        """
        Save route to database.
        
        Args:
            event_id: Event ID
            route_name: Route name
            parcels: List of (parcel_id, lon, lat, sii_score)
            canvasser_id: Canvasser ID
        
        Returns:
            Route ID
        """
        
        cursor = self.conn.cursor()
        
        try:
            # Optimize route
            optimized_parcels = self._optimize_route_tsp(parcels)
            
            # Create route
            route_id = str(uuid.uuid4())
            
            # Build linestring from parcel coordinates
            coords = ','.join([f"{p[1]} {p[2]}" for p in optimized_parcels])
            linestring = f"LINESTRING({coords})"
            
            cursor.execute("""
                INSERT INTO routes (id, event_id, route_name, canvasser_id, geometry, parcel_count, status)
                VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s)
            """, (
                route_id,
                event_id,
                route_name,
                canvasser_id,
                linestring,
                len(optimized_parcels),
                'pending',
            ))
            
            # Add parcels to route
            for seq, parcel in enumerate(optimized_parcels):
                cursor.execute("""
                    INSERT INTO route_parcels (route_id, parcel_id, sequence_order)
                    VALUES (%s, %s, %s)
                """, (route_id, parcel[0], seq))
            
            self.conn.commit()
            logger.info(f"Saved route {route_id} with {len(optimized_parcels)} parcels")
            return route_id
        
        except Exception as e:
            logger.error(f"Error saving route: {e}")
            self.conn.rollback()
            return None
        finally:
            cursor.close()
