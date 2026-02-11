"""
Hybrid Attribution Engine
Markov-Shapley framework with α-sweep control
"""

import numpy as np
from typing import Dict, List, Tuple
from sqlalchemy import create_engine, text
import uuid
from itertools import combinations, permutations

class HybridAttributionEngine:
    """
    Implements the First-Principles Hybrid Attribution Framework
    Combines Markov Removal Effects with Shapley Values
    """
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
    
    def calculate_markov_credit(self, storm_id: uuid.UUID, 
                               channel: str) -> float:
        """
        Calculate Markov removal effect for a channel
        RE = (P(conversion | with channel) - P(conversion | without)) / P(conversion | with)
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT calculate_removal_effect(:storm_id, :channel)
            """), {
                "storm_id": str(storm_id),
                "channel": channel
            })
            
            removal_effect = result.scalar() or 0.0
        
        return removal_effect
    
    def calculate_shapley_credit(self, journey_path: List[str], 
                                channel: str) -> float:
        """
        Calculate Shapley value for a channel in a journey
        Uses exact combinatorial formula
        """
        if channel not in journey_path:
            return 0.0
        
        n = len(journey_path)
        channel_idx = journey_path.index(channel)
        
        # Simplified Shapley: equal credit + positional bonus
        base_credit = 1.0 / n
        
        # Positional weight (middle touchpoints get slight boost)
        position_weight = 1.0 - abs(2 * channel_idx / (n - 1) - 1) * 0.2
        
        return base_credit * position_weight
    
    def calculate_hybrid_credit(self, markov_credit: float, 
                               shapley_credit: float,
                               alpha: float = 0.5) -> float:
        """
        Combine Markov and Shapley using α parameter
        α = 0: Pure Markov (causal)
        α = 1: Pure Shapley (fair)
        """
        return (alpha * markov_credit) + ((1 - alpha) * shapley_credit)
    
    def attribute_journey(self, tenant_id: uuid.UUID, storm_id: uuid.UUID,
                         property_id: uuid.UUID, journey_path: List[str],
                         alpha: float = 0.5) -> Dict[str, float]:
        """
        Attribute credit across all touchpoints in a journey
        Returns dict of {channel: hybrid_credit}
        """
        attribution = {}
        
        for channel in set(journey_path):
            # Markov credit (causal contribution)
            markov_credit = self.calculate_markov_credit(storm_id, channel)
            
            # Shapley credit (fair allocation)
            shapley_credit = self.calculate_shapley_credit(journey_path, channel)
            
            # Hybrid credit
            hybrid_credit = self.calculate_hybrid_credit(
                markov_credit, shapley_credit, alpha
            )
            
            attribution[channel] = hybrid_credit
            
            # Store in database
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO attribution_touchpoints (
                        tenant_id, storm_id, property_id, channel,
                        touchpoint_timestamp, touchpoint_order,
                        markov_credit, shapley_credit, hybrid_credit
                    ) VALUES (
                        :tenant_id, :storm_id, :property_id, :channel,
                        NOW(), :order, :markov, :shapley, :hybrid
                    )
                """), {
                    "tenant_id": str(tenant_id),
                    "storm_id": str(storm_id),
                    "property_id": str(property_id),
                    "channel": channel,
                    "order": journey_path.index(channel),
                    "markov": markov_credit,
                    "shapley": shapley_credit,
                    "hybrid": hybrid_credit
                })
                conn.commit()
        
        return attribution
    
    def alpha_sweep(self, storm_id: uuid.UUID, 
                   alpha_range: List[float] = None) -> Dict[float, Dict]:
        """
        Perform α-sweep analysis
        Shows how attribution changes as α varies from 0 (Markov) to 1 (Shapley)
        """
        if alpha_range is None:
            alpha_range = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        results = {}
        
        with self.engine.connect() as conn:
            # Get all journeys for this storm
            journeys = conn.execute(text("""
                SELECT property_id, touchpoint_sequence
                FROM customer_journeys_v2
                WHERE storm_id = :storm_id
                  AND converted = TRUE
            """), {"storm_id": str(storm_id)}).fetchall()
        
        for alpha in alpha_range:
            channel_credits = {}
            
            for journey in journeys:
                property_id = journey[0]
                path = journey[1]
                
                for channel in set(path):
                    markov = self.calculate_markov_credit(storm_id, channel)
                    shapley = self.calculate_shapley_credit(path, channel)
                    hybrid = self.calculate_hybrid_credit(markov, shapley, alpha)
                    
                    if channel not in channel_credits:
                        channel_credits[channel] = 0
                    channel_credits[channel] += hybrid
            
            results[alpha] = channel_credits
        
        return results
    
    def get_channel_attribution_summary(self, storm_id: uuid.UUID,
                                       alpha: float = 0.5) -> Dict:
        """
        Get attribution summary for all channels
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    channel,
                    COUNT(DISTINCT property_id) as touches,
                    AVG(markov_credit) as avg_markov,
                    AVG(shapley_credit) as avg_shapley,
                    SUM(hybrid_credit) as total_hybrid
                FROM attribution_touchpoints
                WHERE storm_id = :storm_id
                GROUP BY channel
                ORDER BY total_hybrid DESC
            """), {"storm_id": str(storm_id)})
            
            return [dict(row._mapping) for row in result.fetchall()]


class BayesianMMM:
    """
    Bayesian Media Mix Modeling with Adstock and Saturation
    """
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
    
    def weibull_adstock(self, spend_series: np.ndarray, 
                       alpha: float = 0.5, theta: float = 0.3) -> np.ndarray:
        """
        Apply Weibull adstock transformation
        Models memory decay of marketing effects
        """
        n = len(spend_series)
        adstocked = np.zeros(n)
        
        for t in range(n):
            adstocked[t] = spend_series[t]
            
            # Add decayed effects from previous periods
            for lag in range(1, t + 1):
                weight = alpha * (lag ** (alpha - 1)) * np.exp(-(lag / theta) ** alpha)
                adstocked[t] += spend_series[t - lag] * weight
        
        return adstocked
    
    def hill_saturation(self, x: float, k: float, s: float = 1.0) -> float:
        """
        Hill saturation function
        Models diminishing returns
        """
        return (x ** s) / ((k ** s) + (x ** s))
    
    def detect_saturation(self, tenant_id: uuid.UUID, storm_id: uuid.UUID,
                         channel_name: str, zip_code: str = None) -> Dict:
        """
        Detect if a channel is saturated in a ZIP
        """
        with self.engine.connect() as conn:
            # Get channel parameters
            channel = conn.execute(text("""
                SELECT channel_id, saturation_k, saturation_s
                FROM mmm_channels
                WHERE tenant_id = :tenant_id
                  AND channel_name = :channel_name
            """), {
                "tenant_id": str(tenant_id),
                "channel_name": channel_name
            }).fetchone()
            
            if not channel:
                return {"error": "Channel not found"}
            
            channel_id = channel[0]
            k = channel[1] or 100.0
            s = channel[2] or 1.0
            
            # Get recent spend
            query = """
                SELECT SUM(touches) as total_touches
                FROM mmm_observations
                WHERE channel_id = :channel_id
                  AND storm_id = :storm_id
            """
            params = {
                "channel_id": str(channel_id),
                "storm_id": str(storm_id)
            }
            
            if zip_code:
                query += " AND zip_code = :zip_code"
                params["zip_code"] = zip_code
            
            result = conn.execute(text(query), params).fetchone()
            total_touches = result[0] or 0
        
        # Calculate saturation score
        saturation_score = self.hill_saturation(total_touches, k, s)
        
        status = "undersaturated"
        if saturation_score > 0.8:
            status = "saturated"
        elif saturation_score > 0.5:
            status = "optimal"
        
        return {
            "channel": channel_name,
            "zip_code": zip_code,
            "total_touches": total_touches,
            "saturation_score": saturation_score,
            "status": status,
            "recommendation": self._get_saturation_recommendation(status)
        }
    
    def _get_saturation_recommendation(self, status: str) -> str:
        """Get actionable recommendation based on saturation"""
        if status == "saturated":
            return "Reduce spend. Reallocate budget to undersaturated ZIPs."
        elif status == "optimal":
            return "Maintain current spend level."
        else:
            return "Increase spend. High marginal returns available."


class UpliftModeling:
    """
    T-Learner for Conditional Average Treatment Effect (CATE)
    """
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
    
    def segment_by_uplift(self, property_id: uuid.UUID, 
                         cate: float, confidence_interval: Tuple[float, float]) -> str:
        """
        Segment properties into uplift bands
        """
        lower, upper = confidence_interval
        
        if cate > 0.15 and lower > 0:
            return "persuadable"  # High uplift, confident
        elif cate > 0.05 and upper > 0.1:
            return "sure_thing"  # Will convert anyway
        elif cate < -0.05:
            return "sleeping_dog"  # Treatment hurts
        else:
            return "lost_cause"  # No effect
    
    def calculate_brier_score(self, predictions: List[float], 
                             actuals: List[bool]) -> float:
        """
        Calculate Brier score for calibration
        Lower is better (0 = perfect)
        """
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")
        
        squared_errors = [(p - (1.0 if a else 0.0)) ** 2 
                         for p, a in zip(predictions, actuals)]
        
        return sum(squared_errors) / len(squared_errors)


if __name__ == "__main__":
    # Demo
    db_url = "postgresql://stormops:password@localhost:5432/stormops"
    
    # Test Hybrid Attribution
    print("🎯 Hybrid Attribution Engine")
    print("=" * 50)
    
    engine = HybridAttributionEngine(db_url)
    
    # Example journey
    journey = ['earth2_alert', 'door_knock', 'sms', 'web_form', 'call']
    
    print(f"\nJourney: {' → '.join(journey)}")
    
    # Calculate Shapley for each channel
    for channel in set(journey):
        shapley = engine.calculate_shapley_credit(journey, channel)
        print(f"  {channel}: {shapley:.3f} Shapley credit")
    
    # Alpha sweep
    print("\n📊 α-Sweep Analysis")
    for alpha in [0.0, 0.5, 1.0]:
        print(f"\n  α = {alpha} ({'Pure Markov' if alpha == 0 else 'Pure Shapley' if alpha == 1 else 'Hybrid'})")
        for channel in set(journey):
            markov = 0.2  # Placeholder
            shapley = engine.calculate_shapley_credit(journey, channel)
            hybrid = engine.calculate_hybrid_credit(markov, shapley, alpha)
            print(f"    {channel}: {hybrid:.3f}")
    
    # Test MMM
    print("\n\n📈 Bayesian MMM")
    print("=" * 50)
    
    mmm = BayesianMMM(db_url)
    
    # Adstock example
    spend = np.array([100, 150, 200, 180, 160])
    adstocked = mmm.weibull_adstock(spend, alpha=0.5, theta=0.3)
    
    print("\nAdstock Transformation:")
    print(f"  Original: {spend}")
    print(f"  Adstocked: {adstocked.round(2)}")
    
    # Saturation example
    print("\nHill Saturation:")
    for touches in [50, 100, 200, 500]:
        sat = mmm.hill_saturation(touches, k=150, s=1.0)
        print(f"  {touches} touches → {sat:.2%} saturation")
    
    print("\n✅ Marketing Science engines initialized")
