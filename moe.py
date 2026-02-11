"""
Markov Opportunity Engine (MOE)
Models sector state transitions: Baseline → Risk → Impact → Recovery
"""

import psycopg2
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarkovOpportunityEngine:
    """
    Models each sector's state transition with associated claim counts and values.
    """
    
    # State transition matrix (empirical from hail insurance data)
    # Rows: current state, Cols: next state (Baseline, Risk, Impact, Recovery)
    TRANSITION_MATRIX = {
        'baseline': {'baseline': 0.95, 'risk': 0.05, 'impact': 0.0, 'recovery': 0.0},
        'risk': {'baseline': 0.1, 'risk': 0.5, 'impact': 0.4, 'recovery': 0.0},
        'impact': {'baseline': 0.0, 'risk': 0.0, 'impact': 0.2, 'recovery': 0.8},
        'recovery': {'baseline': 0.7, 'risk': 0.2, 'impact': 0.0, 'recovery': 0.1},
    }
    
    # Expected claim counts per state (per 100 roofs)
    CLAIM_EXPECTATIONS = {
        'baseline': {'count': 0, 'value_per_claim': 0},
        'risk': {'count': 5, 'value_per_claim': 15000},
        'impact': {'count': 45, 'value_per_claim': 75000},
        'recovery': {'count': 35, 'value_per_claim': 65000},
    }
    
    # State duration (hours)
    STATE_DURATION = {
        'baseline': 168,  # 1 week
        'risk': 12,       # 12 hours
        'impact': 6,      # 6 hours
        'recovery': 72,   # 3 days
    }
    
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
    
    def initialize_sector_states(self, event_id: str) -> int:
        """
        Initialize MOE states for all sectors in an event.
        All sectors start in 'baseline' state.
        
        Args:
            event_id: Event ID
        
        Returns:
            Number of sectors initialized
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get all sectors
            cursor.execute("SELECT id FROM sectors")
            sectors = cursor.fetchall()
            
            for sector_id, in sectors:
                cursor.execute("""
                    INSERT INTO moe_state (event_id, sector_id, state, state_probability, 
                                          expected_claim_count, expected_claim_value_usd, 
                                          recommended_canvassers, surge_multiplier)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id, sector_id) DO NOTHING
                """, (
                    event_id,
                    sector_id,
                    'baseline',
                    1.0,
                    0,
                    0,
                    0,
                    1.0,
                ))
            
            self.conn.commit()
            logger.info(f"Initialized {len(sectors)} sector states")
            return len(sectors)
        
        except Exception as e:
            logger.error(f"Error initializing sector states: {e}")
            self.conn.rollback()
            return 0
        finally:
            cursor.close()
    
    def update_sector_state(
        self,
        event_id: str,
        sector_id: str,
        hail_intensity_avg: float,
        forecast_prob_severe: float,
    ) -> Dict:
        """
        Update MOE state for a sector based on hail intensity and forecast.
        
        Args:
            event_id: Event ID
            sector_id: Sector ID
            hail_intensity_avg: Average hail intensity in mm for sector
            forecast_prob_severe: Forecast probability of severe weather (0-1)
        
        Returns:
            Dict with new state, probabilities, and expectations
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get current state
            cursor.execute("""
                SELECT state FROM moe_state
                WHERE event_id = %s AND sector_id = %s
            """, (event_id, sector_id))
            
            result = cursor.fetchone()
            current_state = result[0] if result else 'baseline'
            
            # Determine next state based on hail intensity and forecast
            if hail_intensity_avg < 20:
                # No significant hail
                if forecast_prob_severe > 0.8:
                    next_state = 'risk'
                else:
                    next_state = 'baseline'
            elif hail_intensity_avg < 40:
                # Moderate hail
                next_state = 'impact'
            else:
                # Severe hail
                next_state = 'impact'
            
            # If we're in impact and hail has passed, move to recovery
            if current_state == 'impact' and hail_intensity_avg < 10:
                next_state = 'recovery'
            
            # Get expectations for next state
            expectations = self.CLAIM_EXPECTATIONS[next_state]
            
            # Estimate roofs in sector (mock: 500 roofs per sector)
            roofs_in_sector = 500
            expected_claims = int((expectations['count'] / 100) * roofs_in_sector)
            expected_value = expected_claims * expectations['value_per_claim']
            
            # Recommend canvassers based on expected claims
            recommended_canvassers = max(1, expected_claims // 50)  # 1 canvasser per 50 claims
            
            # Surge multiplier: increase spend/comp during peak money windows
            surge_multiplier = 1.0
            if next_state == 'recovery':
                surge_multiplier = 1.5  # 50% surge during recovery (peak money window)
            elif next_state == 'impact':
                surge_multiplier = 1.2
            
            # Update database
            cursor.execute("""
                UPDATE moe_state
                SET state = %s,
                    state_probability = %s,
                    expected_claim_count = %s,
                    expected_claim_value_usd = %s,
                    recommended_canvassers = %s,
                    surge_multiplier = %s,
                    updated_at = NOW()
                WHERE event_id = %s AND sector_id = %s
            """, (
                next_state,
                1.0,
                expected_claims,
                expected_value,
                recommended_canvassers,
                surge_multiplier,
                event_id,
                sector_id,
            ))
            
            self.conn.commit()
            
            logger.info(f"Updated sector {sector_id}: {current_state} → {next_state}, "
                       f"expected claims: {expected_claims}, value: ${expected_value:,.0f}")
            
            return {
                'current_state': current_state,
                'next_state': next_state,
                'expected_claims': expected_claims,
                'expected_value': expected_value,
                'recommended_canvassers': recommended_canvassers,
                'surge_multiplier': surge_multiplier,
            }
        
        except Exception as e:
            logger.error(f"Error updating sector state: {e}")
            self.conn.rollback()
            return {}
        finally:
            cursor.close()
    
    def forecast_state_trajectory(
        self,
        event_id: str,
        sector_id: str,
        hours_ahead: int = 72,
    ) -> list:
        """
        Forecast state trajectory for a sector over next N hours.
        
        Args:
            event_id: Event ID
            sector_id: Sector ID
            hours_ahead: Hours to forecast (default 72)
        
        Returns:
            List of (hour, state, probability, expected_claims, expected_value)
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get current state
            cursor.execute("""
                SELECT state FROM moe_state
                WHERE event_id = %s AND sector_id = %s
            """, (event_id, sector_id))
            
            result = cursor.fetchone()
            current_state = result[0] if result else 'baseline'
            
            trajectory = []
            state = current_state
            
            for hour in range(0, hours_ahead + 1, 6):  # 6-hour intervals
                # Get transition probabilities
                transitions = self.TRANSITION_MATRIX.get(state, {})
                
                # Randomly sample next state based on probabilities
                states = list(transitions.keys())
                probs = list(transitions.values())
                next_state = np.random.choice(states, p=probs)
                
                # Get expectations
                expectations = self.CLAIM_EXPECTATIONS[next_state]
                roofs_in_sector = 500
                expected_claims = int((expectations['count'] / 100) * roofs_in_sector)
                expected_value = expected_claims * expectations['value_per_claim']
                
                trajectory.append({
                    'hour': hour,
                    'state': next_state,
                    'probability': transitions.get(next_state, 0),
                    'expected_claims': expected_claims,
                    'expected_value': expected_value,
                })
                
                state = next_state
            
            return trajectory
        
        except Exception as e:
            logger.error(f"Error forecasting trajectory: {e}")
            return []
        finally:
            cursor.close()
    
    def get_operational_score(self, event_id: str) -> float:
        """
        Calculate overall Operational Score (0-100) for an event.
        Combines state, expected value, and urgency.
        
        Args:
            event_id: Event ID
        
        Returns:
            Operational Score (0-100)
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            # Get all sector states for this event
            cursor.execute("""
                SELECT state, expected_claim_value_usd, surge_multiplier
                FROM moe_state
                WHERE event_id = %s
            """, (event_id,))
            
            states = cursor.fetchall()
            
            if not states:
                return 0.0
            
            # Score each state
            state_scores = {
                'baseline': 10,
                'risk': 40,
                'impact': 80,
                'recovery': 60,
            }
            
            total_score = 0
            total_value = 0
            
            for state, value, surge in states:
                score = state_scores.get(state, 0)
                # Weight by expected value and surge multiplier
                weighted_score = score * (1 + (value / 1000000)) * surge
                total_score += weighted_score
                total_value += value
            
            # Normalize to 0-100
            operational_score = min(100, (total_score / len(states)) * 0.5)
            
            logger.info(f"Operational Score: {operational_score:.1f}/100, Total Value: ${total_value:,.0f}")
            
            return operational_score
        
        except Exception as e:
            logger.error(f"Error calculating operational score: {e}")
            return 0.0
        finally:
            cursor.close()


# Example usage
if __name__ == '__main__':
    moe = MarkovOpportunityEngine()
    moe.connect()
    
    try:
        # Initialize sectors for an event
        event_id = 'test-event-1'
        moe.initialize_sector_states(event_id)
        
        # Update a sector state
        sector_id = 'sector-1'
        result = moe.update_sector_state(
            event_id=event_id,
            sector_id=sector_id,
            hail_intensity_avg=50,  # 50mm hail
            forecast_prob_severe=0.9,
        )
        print(f"State update: {result}")
        
        # Forecast trajectory
        trajectory = moe.forecast_state_trajectory(event_id, sector_id, hours_ahead=72)
        print(f"\nState trajectory (next 72 hours):")
        for t in trajectory:
            print(f"  Hour {t['hour']}: {t['state']}, {t['expected_claims']} claims, ${t['expected_value']:,.0f}")
        
        # Get operational score
        score = moe.get_operational_score(event_id)
        print(f"\nOperational Score: {score:.1f}/100")
    
    finally:
        moe.close()
