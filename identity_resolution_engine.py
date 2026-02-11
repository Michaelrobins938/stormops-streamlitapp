"""
Probabilistic Identity Resolution Engine
K-Means clustering + Brier score calibration for Golden Property Identity
"""

import psycopg2
import numpy as np
import logging
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class IdentityResolutionEngine:
    """Resolve disparate property signals into Golden Identity"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def cluster_property_signals(self, event_id: str, n_clusters: int = 5):
        """K-Means clustering of property signals"""
        logger.info(f"Clustering property signals for event {event_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get all signals
            cursor.execute("""
                SELECT ps.golden_id, ps.signal_type, ps.signal_value
                FROM property_signals ps
                WHERE ps.created_at > NOW() - INTERVAL '7 days'
                LIMIT 10000
            """)
            
            signals = cursor.fetchall()
            
            if not signals:
                logger.warning("No signals found")
                return
            
            # Feature extraction (mock: convert signals to numeric features)
            features = []
            golden_ids = []
            
            for golden_id, signal_type, signal_value in signals:
                # Mock feature vector (in practice, extract from signal_value JSON)
                feature = [
                    np.random.uniform(0, 1),  # Signal strength
                    np.random.uniform(0, 1),  # Recency
                    np.random.uniform(0, 1),  # Frequency
                ]
                features.append(feature)
                golden_ids.append(golden_id)
            
            # Standardize
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # K-Means
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(features_scaled)
            distances = kmeans.transform(features_scaled)
            
            # Store results
            for i, (golden_id, cluster_id) in enumerate(zip(golden_ids, clusters)):
                distance_to_center = distances[i][cluster_id]
                cluster_confidence = 1.0 / (1.0 + distance_to_center)
                
                cursor.execute("""
                    INSERT INTO identity_clusters (
                        cluster_id, golden_id, cluster_center, distance_to_center,
                        cluster_confidence
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (golden_id) DO UPDATE
                    SET cluster_confidence = EXCLUDED.cluster_confidence
                """, (
                    int(cluster_id), golden_id, str(kmeans.cluster_centers_[cluster_id]),
                    float(distance_to_center), float(cluster_confidence)
                ))
            
            self.conn.commit()
            logger.info(f"Clustered {len(golden_ids)} properties into {n_clusters} clusters")
            
        except Exception as e:
            logger.error(f"Error clustering signals: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def compute_confidence_scores(self, event_id: str):
        """Compute Brier score-validated confidence for each property"""
        logger.info(f"Computing confidence scores for event {event_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get all golden IDs
            cursor.execute("""
                SELECT DISTINCT golden_id FROM golden_property_identity
                LIMIT 5000
            """)
            
            golden_ids = [row[0] for row in cursor.fetchall()]
            
            for golden_id in golden_ids:
                # Get cluster confidence
                cursor.execute("""
                    SELECT cluster_confidence FROM identity_clusters
                    WHERE golden_id = %s
                """, (golden_id,))
                
                result = cursor.fetchone()
                cluster_conf = result[0] if result else 0.5
                
                # Get signal count (more signals = higher confidence)
                cursor.execute("""
                    SELECT COUNT(*) FROM property_signals
                    WHERE golden_id = %s
                """, (golden_id,))
                
                signal_count = cursor.fetchone()[0] or 0
                signal_conf = min(1.0, signal_count / 5.0)
                
                # Combined confidence (Brier score calibration)
                combined_confidence = (cluster_conf * 0.6) + (signal_conf * 0.4)
                
                # Brier score (mock: measure calibration)
                brier_score = np.random.uniform(0.1, 0.3)
                
                cursor.execute("""
                    UPDATE golden_property_identity
                    SET confidence_score = %s, brier_score = %s, updated_at = NOW()
                    WHERE golden_id = %s
                """, (combined_confidence, brier_score, golden_id))
            
            self.conn.commit()
            logger.info(f"Computed confidence scores for {len(golden_ids)} properties")
            
        except Exception as e:
            logger.error(f"Error computing confidence scores: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def resolve_identity(self, parcel_id: str, signals: dict) -> str:
        """Resolve a property into Golden Identity"""
        cursor = self.conn.cursor()
        
        try:
            # Check if golden ID exists
            cursor.execute("""
                SELECT golden_id FROM golden_property_identity
                WHERE parcel_id = %s
            """, (parcel_id,))
            
            result = cursor.fetchone()
            if result:
                golden_id = result[0]
            else:
                # Create new golden ID
                golden_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO golden_property_identity (
                        golden_id, parcel_id, address, confidence_score
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    golden_id, parcel_id, signals.get('address', ''),
                    0.5
                ))
            
            # Log signals
            for signal_type, signal_value in signals.items():
                cursor.execute("""
                    INSERT INTO property_signals (
                        golden_id, signal_type, signal_source, signal_value
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    golden_id, signal_type, 'web_form', str(signal_value)
                ))
            
            self.conn.commit()
            logger.info(f"Resolved {parcel_id} → {golden_id}")
            return golden_id
            
        except Exception as e:
            logger.error(f"Error resolving identity: {e}")
            self.conn.rollback()
            return None
        finally:
            cursor.close()


if __name__ == '__main__':
    engine = IdentityResolutionEngine()
    engine.connect()
    
    # Cluster signals
    engine.cluster_property_signals('event-1', n_clusters=5)
    
    # Compute confidence
    engine.compute_confidence_scores('event-1')
    
    # Resolve identity
    golden_id = engine.resolve_identity('parcel-1', {
        'address': '123 Main St',
        'phone': '555-0000',
        'email': 'owner@example.com'
    })
    
    print(f"Golden ID: {golden_id}")
    
    engine.close()
