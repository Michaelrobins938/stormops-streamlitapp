"""
Behavior Attribution Engine
Markov + Shapley hybrid for multi-touch attribution
"""

import psycopg2
import numpy as np
import logging
from itertools import combinations
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class MarkovAttributionEngine:
    """Markov chain attribution"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def build_transition_matrix(self, event_id: str) -> dict:
        """Build Markov transition matrix from behavior events"""
        logger.info(f"Building transition matrix for event {event_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get all journeys
            cursor.execute("""
                SELECT lead_id, channels_touched, final_outcome
                FROM journey_outcomes
                WHERE event_id = %s
            """, (event_id,))
            
            journeys = cursor.fetchall()
            transitions = defaultdict(lambda: defaultdict(int))
            
            for lead_id, channels, outcome in journeys:
                if not channels:
                    continue
                
                # Build state sequence: channel1 → channel2 → ... → outcome
                states = list(channels) + [outcome]
                
                for i in range(len(states) - 1):
                    from_state = states[i]
                    to_state = states[i + 1]
                    transitions[from_state][to_state] += 1
            
            # Compute probabilities
            transition_probs = {}
            for from_state, to_states in transitions.items():
                total = sum(to_states.values())
                for to_state, count in to_states.items():
                    prob = count / total if total > 0 else 0
                    transition_probs[(from_state, to_state)] = prob
                    
                    # Store in DB
                    cursor.execute("""
                        INSERT INTO markov_transitions (
                            event_id, from_state, to_state, channel, count, probability
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (event_id, from_state, to_state, channel) DO UPDATE
                        SET probability = EXCLUDED.probability
                    """, (event_id, from_state, to_state, from_state, count, prob))
            
            self.conn.commit()
            logger.info(f"Built transition matrix with {len(transition_probs)} transitions")
            return transition_probs
        
        except Exception as e:
            logger.error(f"Error building transition matrix: {e}")
            self.conn.rollback()
            return {}
        finally:
            cursor.close()
    
    def compute_removal_effects(self, event_id: str, channels: list) -> dict:
        """Compute Markov removal effect for each channel"""
        logger.info(f"Computing removal effects for {len(channels)} channels")
        
        cursor = self.conn.cursor()
        
        try:
            removal_effects = {}
            
            for channel in channels:
                # Get conversion rate with channel
                cursor.execute("""
                    SELECT COUNT(CASE WHEN final_outcome = 'conversion' THEN 1 END),
                           COUNT(*)
                    FROM journey_outcomes
                    WHERE event_id = %s AND %s = ANY(channels_touched)
                """, (event_id, channel))
                
                result = cursor.fetchone()
                conversions_with = result[0] if result else 0
                total_with = result[1] if result else 1
                rate_with = conversions_with / total_with if total_with > 0 else 0
                
                # Get conversion rate without channel
                cursor.execute("""
                    SELECT COUNT(CASE WHEN final_outcome = 'conversion' THEN 1 END),
                           COUNT(*)
                    FROM journey_outcomes
                    WHERE event_id = %s AND NOT %s = ANY(channels_touched)
                """, (event_id, channel))
                
                result = cursor.fetchone()
                conversions_without = result[0] if result else 0
                total_without = result[1] if result else 1
                rate_without = conversions_without / total_without if total_without > 0 else 0
                
                # Removal effect = rate_with - rate_without
                removal_effects[channel] = rate_with - rate_without
            
            logger.info(f"Computed removal effects: {removal_effects}")
            return removal_effects
        
        except Exception as e:
            logger.error(f"Error computing removal effects: {e}")
            return {}
        finally:
            cursor.close()


class ShapleyAttributionEngine:
    """Shapley value attribution"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def compute_coalition_value(self, event_id: str, coalition: list) -> float:
        """Compute value of a channel coalition"""
        cursor = self.conn.cursor()
        
        try:
            # Get conversion rate for this coalition
            if not coalition:
                return 0.0
            
            placeholders = ','.join(['%s'] * len(coalition))
            cursor.execute(f"""
                SELECT COUNT(CASE WHEN final_outcome = 'conversion' THEN 1 END),
                       COUNT(*),
                       AVG(total_value_usd)
                FROM journey_outcomes
                WHERE event_id = %s AND channels_touched && ARRAY[{placeholders}]
            """, [event_id] + coalition)
            
            result = cursor.fetchone()
            conversions = result[0] if result else 0
            total = result[1] if result else 1
            avg_value = result[2] if result else 0
            
            conversion_rate = conversions / total if total > 0 else 0
            coalition_value = conversion_rate * avg_value
            
            return coalition_value
        
        except Exception as e:
            logger.error(f"Error computing coalition value: {e}")
            return 0.0
        finally:
            cursor.close()
    
    def compute_shapley_values(self, event_id: str, channels: list, samples: int = 100) -> dict:
        """Compute Shapley values via sampling"""
        logger.info(f"Computing Shapley values for {len(channels)} channels ({samples} samples)")
        
        shapley_values = {ch: 0.0 for ch in channels}
        
        for _ in range(samples):
            # Random permutation
            perm = np.random.permutation(channels)
            
            for i, channel in enumerate(perm):
                # Coalition without this channel
                coalition_without = list(perm[:i])
                value_without = self.compute_coalition_value(event_id, coalition_without)
                
                # Coalition with this channel
                coalition_with = list(perm[:i+1])
                value_with = self.compute_coalition_value(event_id, coalition_with)
                
                # Marginal contribution
                marginal = value_with - value_without
                shapley_values[channel] += marginal / samples
        
        logger.info(f"Shapley values: {shapley_values}")
        return shapley_values


class HybridAttributionEngine:
    """Hybrid Markov + Shapley attribution"""
    
    def __init__(self, alpha: float = 0.7):
        self.alpha = alpha
        self.markov_engine = MarkovAttributionEngine()
        self.shapley_engine = ShapleyAttributionEngine()
        self.conn = None
    
    def connect(self):
        self.markov_engine.connect()
        self.shapley_engine.connect()
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        self.markov_engine.close()
        self.shapley_engine.close()
        if self.conn:
            self.conn.close()
    
    def compute_hybrid_attribution(self, event_id: str, channels: list) -> dict:
        """Compute hybrid Markov + Shapley attribution"""
        logger.info(f"Computing hybrid attribution for event {event_id}")
        
        # Markov removal effects
        markov_effects = self.markov_engine.compute_removal_effects(event_id, channels)
        
        # Normalize Markov effects
        total_markov = sum(max(0, v) for v in markov_effects.values())
        markov_shares = {ch: (max(0, markov_effects.get(ch, 0)) / total_markov if total_markov > 0 else 0) 
                        for ch in channels}
        
        # Shapley values
        shapley_values = self.shapley_engine.compute_shapley_values(event_id, channels, samples=50)
        
        # Normalize Shapley
        total_shapley = sum(max(0, v) for v in shapley_values.values())
        shapley_shares = {ch: (max(0, shapley_values.get(ch, 0)) / total_shapley if total_shapley > 0 else 0)
                         for ch in channels}
        
        # Hybrid score
        hybrid_scores = {}
        for channel in channels:
            hybrid = (self.alpha * markov_shares.get(channel, 0) + 
                     (1 - self.alpha) * shapley_shares.get(channel, 0))
            hybrid_scores[channel] = hybrid
            
            # Store in DB
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO shapley_attribution (
                        event_id, lead_id, channel, shapley_value, markov_share,
                        hybrid_score, alpha
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id, lead_id, channel) DO UPDATE
                    SET hybrid_score = EXCLUDED.hybrid_score
                """, (event_id, 'aggregate', channel, shapley_values.get(channel, 0),
                     markov_shares.get(channel, 0), hybrid, self.alpha))
                self.conn.commit()
            finally:
                cursor.close()
        
        logger.info(f"Hybrid scores: {hybrid_scores}")
        return hybrid_scores


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python behavior_attribution.py <event_id>")
        sys.exit(1)
    
    event_id = sys.argv[1]
    
    # Run hybrid attribution
    engine = HybridAttributionEngine(alpha=0.7)
    engine.connect()
    
    channels = ['sms', 'phone', 'door_knock', 'email']
    hybrid_scores = engine.compute_hybrid_attribution(event_id, channels)
    
    print(f"\nHybrid Attribution Scores:")
    for channel, score in sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {channel}: {score:.3f}")
    
    engine.close()
