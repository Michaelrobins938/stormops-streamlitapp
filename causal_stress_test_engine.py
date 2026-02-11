"""
Causal Stress Test Engine
Synthetic ground truth testing + Last-touch bias detection
"""

import psycopg2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'


class CausalStressTestEngine:
    """Test causal robustness of damage propensity scores"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self):
        self.conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def generate_synthetic_ground_truth(self, event_id: str, campaign_id: str):
        """Generate synthetic ground truth for validation"""
        logger.info(f"Generating synthetic ground truth for campaign {campaign_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get all leads in campaign
            cursor.execute("""
                SELECT l.id, pi.sii_score, l.lead_status
                FROM leads l
                JOIN parcel_impacts pi ON l.parcel_id = pi.parcel_id
                WHERE l.event_id = %s
                LIMIT 1000
            """, (event_id,))
            
            leads = cursor.fetchall()
            
            errors = []
            
            for lead_id, sii_score, lead_status in leads:
                # Synthetic ground truth: assume conversion if SII > 70
                synthetic_conversion = 1 if sii_score > 70 else 0
                
                # Actual conversion (mock)
                actual_conversion = 1 if lead_status == 'closed' else 0
                
                # Error
                error = abs(synthetic_conversion - actual_conversion)
                errors.append(error)
            
            # Mean absolute error
            mae = np.mean(errors) if errors else 0
            
            logger.info(f"Synthetic ground truth MAE: {mae:.3f}")
            return mae
            
        except Exception as e:
            logger.error(f"Error generating synthetic ground truth: {e}")
            return None
        finally:
            cursor.close()
    
    def detect_last_touch_bias(self, event_id: str, campaign_id: str) -> float:
        """Detect last-touch bias in attribution"""
        logger.info(f"Detecting last-touch bias for campaign {campaign_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get journeys
            cursor.execute("""
                SELECT channels_touched, final_outcome, total_value_usd
                FROM journey_outcomes
                WHERE event_id = %s
                LIMIT 1000
            """, (event_id,))
            
            journeys = cursor.fetchall()
            
            last_touch_credit = 0
            total_value = 0
            
            for channels, outcome, value in journeys:
                if outcome == 'conversion' and channels:
                    # Last touch gets all credit
                    last_channel = channels[-1]
                    last_touch_credit += value
                    total_value += value
            
            # Bias delta (how much credit last-touch gets vs fair share)
            fair_share = total_value / len(channels) if channels else 0
            bias_delta = (last_touch_credit / total_value - 1.0 / len(channels)) if total_value > 0 else 0
            
            logger.info(f"Last-touch bias delta: {bias_delta:.3f}")
            return bias_delta
            
        except Exception as e:
            logger.error(f"Error detecting last-touch bias: {e}")
            return 0.0
        finally:
            cursor.close()
    
    def run_stress_test(self, event_id: str, campaign_id: str) -> dict:
        """Run full causal stress test"""
        logger.info(f"Running causal stress test for campaign {campaign_id}")
        
        cursor = self.conn.cursor()
        
        try:
            # Get damage propensity score
            cursor.execute("""
                SELECT AVG(sii_score) FROM parcel_impacts
                WHERE event_id = %s
            """, (event_id,))
            
            damage_propensity = cursor.fetchone()[0] or 0
            
            # Synthetic ground truth error
            sgt_error = self.generate_synthetic_ground_truth(event_id, campaign_id)
            
            # Last-touch bias
            ltb_delta = self.detect_last_touch_bias(event_id, campaign_id)
            
            # Robustness flag (pass if errors are low)
            robustness_flag = (sgt_error < 0.2 and abs(ltb_delta) < 0.3) if sgt_error else False
            
            # Store results
            cursor.execute("""
                INSERT INTO causal_stress_tests (
                    event_id, campaign_id, damage_propensity_score,
                    last_touch_bias_delta, synthetic_ground_truth_error,
                    robustness_flag
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                event_id, campaign_id, damage_propensity,
                ltb_delta, sgt_error, robustness_flag
            ))
            
            self.conn.commit()
            
            result = {
                'damage_propensity_score': damage_propensity,
                'last_touch_bias_delta': ltb_delta,
                'synthetic_ground_truth_error': sgt_error,
                'robustness_flag': robustness_flag,
            }
            
            logger.info(f"Stress test result: {'PASS' if robustness_flag else 'FAIL'}")
            return result
            
        except Exception as e:
            logger.error(f"Error running stress test: {e}")
            self.conn.rollback()
            return {}
        finally:
            cursor.close()


if __name__ == '__main__':
    engine = CausalStressTestEngine()
    engine.connect()
    
    result = engine.run_stress_test('event-1', 'campaign-1')
    print(f"Stress test result: {result}")
    
    engine.close()
