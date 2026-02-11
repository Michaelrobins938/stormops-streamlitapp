"""
Markov Chain Weather Prediction
Predicts next-day weather states based on historical patterns
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class WeatherPredictor:
    """Markov chain-based weather prediction for DFW."""
    
    def __init__(self):
        # Weather states: Clear, Cloudy, Rain, Severe
        self.states = ["Clear", "Cloudy", "Rain", "Severe"]
        
        # Transition matrix (historical DFW patterns)
        # Rows = current state, Cols = next state
        self.transition_matrix = np.array([
            [0.70, 0.20, 0.08, 0.02],  # Clear -> [Clear, Cloudy, Rain, Severe]
            [0.30, 0.50, 0.15, 0.05],  # Cloudy -> ...
            [0.20, 0.40, 0.35, 0.05],  # Rain -> ...
            [0.40, 0.30, 0.20, 0.10]   # Severe -> ...
        ])
        
        # Severe weather sub-states
        self.severe_types = {
            "hail": 0.40,
            "wind": 0.35,
            "tornado": 0.15,
            "flood": 0.10
        }
    
    def predict_next_days(self, current_state: str, days: int = 7) -> List[Dict]:
        """Predict weather for next N days using Markov chain."""
        
        if current_state not in self.states:
            current_state = "Clear"
        
        predictions = []
        state_idx = self.states.index(current_state)
        
        for day in range(1, days + 1):
            # Get probability distribution for next state
            probs = self.transition_matrix[state_idx]
            
            # Sample next state
            next_state_idx = np.random.choice(len(self.states), p=probs)
            next_state = self.states[next_state_idx]
            
            # Generate prediction details
            pred = {
                "day": day,
                "date": (datetime.now() + timedelta(days=day)).strftime("%Y-%m-%d"),
                "state": next_state,
                "probability": float(probs[next_state_idx]),
                "confidence": self._calculate_confidence(probs)
            }
            
            # Add severe weather details
            if next_state == "Severe":
                severe_type = np.random.choice(
                    list(self.severe_types.keys()),
                    p=list(self.severe_types.values())
                )
                pred["severe_type"] = severe_type
                pred["hail_probability"] = self.severe_types["hail"]
                pred["estimated_hail_size"] = np.random.uniform(1.0, 2.5) if severe_type == "hail" else 0
            
            predictions.append(pred)
            
            # Update state for next iteration
            state_idx = next_state_idx
        
        return predictions
    
    def _calculate_confidence(self, probs: np.ndarray) -> float:
        """Calculate prediction confidence based on entropy."""
        # Lower entropy = higher confidence
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        max_entropy = np.log2(len(probs))
        confidence = 1 - (entropy / max_entropy)
        return float(confidence)
    
    def get_severe_weather_days(self, current_state: str, days: int = 14) -> List[int]:
        """Return list of days with severe weather probability > 50%."""
        predictions = self.predict_next_days(current_state, days)
        
        severe_days = []
        for pred in predictions:
            if pred["state"] == "Severe" or pred["probability"] > 0.5:
                severe_days.append(pred["day"])
        
        return severe_days
    
    def calculate_storm_window(self, current_state: str) -> Dict:
        """Calculate optimal canvassing window based on predictions."""
        predictions = self.predict_next_days(current_state, 7)
        
        # Find first severe weather day
        first_severe = None
        for pred in predictions:
            if pred["state"] == "Severe":
                first_severe = pred["day"]
                break
        
        if first_severe:
            # Optimal window: 1-2 days after severe weather
            optimal_start = first_severe + 1
            optimal_end = first_severe + 3
            
            return {
                "severe_weather_day": first_severe,
                "optimal_canvass_start": optimal_start,
                "optimal_canvass_end": optimal_end,
                "window_days": optimal_end - optimal_start,
                "urgency": "HIGH" if first_severe <= 3 else "MEDIUM"
            }
        
        return {
            "severe_weather_day": None,
            "optimal_canvass_start": None,
            "optimal_canvass_end": None,
            "window_days": 0,
            "urgency": "LOW"
        }
    
    def get_current_state_from_conditions(self, hail: float, wind: float, precip: float) -> str:
        """Infer current weather state from conditions."""
        if hail > 1.0 or wind > 60:
            return "Severe"
        elif precip > 5:
            return "Rain"
        elif precip > 0 or wind > 20:
            return "Cloudy"
        else:
            return "Clear"
