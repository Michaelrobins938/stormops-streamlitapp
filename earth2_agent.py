"""
Earth-2 Digital Twin Agentic Tool Definition
Enables AI to query and control NVIDIA Earth-2 simulation engine
"""

from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Earth2Query:
    """Structured query to Earth-2 Digital Twin."""
    region: str  # e.g., "DFW", "North Dallas"
    resolution_km: float = 1.0  # Kilometer-scale resolution
    forecast_hours: int = 6  # How far ahead to simulate
    hazard_types: List[str] = None  # ["hail", "wind", "tornado"]
    threshold_hail_inches: float = 1.5
    threshold_wind_mph: float = 60
    
    def __post_init__(self):
        if self.hazard_types is None:
            self.hazard_types = ["hail", "wind"]

@dataclass
class Earth2Response:
    """Response from Earth-2 Digital Twin."""
    query_id: str
    timestamp: datetime
    confidence: float  # 0-1 probability
    hazard_map: Dict[str, Any]  # Geospatial data
    high_impact_zones: List[Dict]  # ZIPs with >threshold
    simulation_metadata: Dict
    
    def get_actionable_zones(self, min_confidence: float = 0.7) -> List[str]:
        """Return only zones above confidence threshold."""
        return [z["zip"] for z in self.high_impact_zones if z.get("confidence", 0) >= min_confidence]

class Earth2Agent:
    """
    Agentic wrapper for Earth-2 Digital Twin.
    AI can use this to proactively monitor and simulate scenarios.
    """
    
    def __init__(self):
        self.active_monitors = {}  # Persistent watchers
        self.simulation_cache = {}
        self.sync_confidence = 1.0  # 0-1, degrades with latency
        
    def query_nowcast(self, query: Earth2Query) -> Earth2Response:
        """
        Query current state of digital twin.
        AI Tool: query_earth2_nowcast
        """
        # Simulate Earth-2 API call
        return Earth2Response(
            query_id=f"e2_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            confidence=0.85,
            hazard_map={"type": "hail_swath", "data": []},
            high_impact_zones=[
                {"zip": "75034", "hail_max": 2.5, "confidence": 0.92, "value_potential": 2.1e6},
                {"zip": "75024", "hail_max": 2.2, "confidence": 0.88, "value_potential": 1.8e6},
                {"zip": "76092", "hail_max": 2.0, "confidence": 0.79, "value_potential": 1.5e6}
            ],
            simulation_metadata={"resolution_km": query.resolution_km, "compute_time_ms": 450}
        )
    
    def simulate_what_if(self, base_query: Earth2Query, scenario: Dict) -> Earth2Response:
        """
        Run what-if simulation.
        AI Tool: simulate_earth2_scenario
        
        Example scenario: {"hail_increase": 0.5, "wind_increase": 10}
        """
        # Modify query based on scenario
        modified_query = base_query
        modified_query.threshold_hail_inches += scenario.get("hail_increase", 0)
        modified_query.threshold_wind_mph += scenario.get("wind_increase", 0)
        
        return self.query_nowcast(modified_query)
    
    def start_monitor(self, monitor_id: str, query: Earth2Query, trigger_condition: str) -> Dict:
        """
        Start persistent Earth-2 monitor (Sentinel).
        AI Tool: start_earth2_monitor
        
        Example: monitor_id="dfw_hail_watch", trigger_condition="hail > 2.0 inches"
        """
        self.active_monitors[monitor_id] = {
            "query": query,
            "trigger_condition": trigger_condition,
            "status": "listening",
            "created_at": datetime.now(),
            "last_check": None,
            "triggered_count": 0
        }
        
        return {
            "monitor_id": monitor_id,
            "status": "active",
            "message": f"Monitoring {query.region} for {trigger_condition}"
        }
    
    def stop_monitor(self, monitor_id: str) -> Dict:
        """Stop a running monitor."""
        if monitor_id in self.active_monitors:
            del self.active_monitors[monitor_id]
            return {"status": "stopped", "monitor_id": monitor_id}
        return {"status": "not_found"}
    
    def get_sync_health(self) -> Dict:
        """
        Check Earth-2 connection health.
        AI Tool: check_earth2_health
        """
        # Simulate latency check
        latency_ms = 120  # Mock value
        
        if latency_ms < 200:
            self.sync_confidence = 1.0
            status = "optimal"
        elif latency_ms < 500:
            self.sync_confidence = 0.8
            status = "degraded"
        else:
            self.sync_confidence = 0.5
            status = "slow"
        
        return {
            "status": status,
            "sync_confidence": self.sync_confidence,
            "latency_ms": latency_ms,
            "recommendation": "Proceed with route generation" if self.sync_confidence > 0.7 else "Wait for sync to improve"
        }
    
    def increase_resolution(self, region: str, target_km: float = 0.5) -> Dict:
        """
        Request higher resolution simulation for specific region.
        AI Tool: increase_earth2_resolution
        
        Cost: Higher resolution = more compute tokens
        """
        compute_cost = int((1.0 / target_km) * 10)  # Rough estimate
        
        return {
            "region": region,
            "new_resolution_km": target_km,
            "compute_cost_tokens": compute_cost,
            "status": "queued",
            "eta_seconds": 30
        }
    
    def get_time_series(self, region: str, hours_ahead: int = 12) -> List[Dict]:
        """
        Get time-series forecast from Earth-2.
        AI Tool: get_earth2_timeline
        
        Returns hourly snapshots for time-slider UI.
        """
        timeline = []
        base_time = datetime.now()
        
        for hour in range(hours_ahead):
            timeline.append({
                "timestamp": (base_time + timedelta(hours=hour)).isoformat(),
                "hail_max_inches": 2.5 - (hour * 0.15),  # Storm weakens over time
                "affected_zips": max(0, 12 - hour),
                "confidence": max(0.5, 0.95 - (hour * 0.05))
            })
        
        return timeline


# Tool definitions for AI model
EARTH2_TOOLS = [
    {
        "name": "query_earth2_nowcast",
        "description": "Query current state of NVIDIA Earth-2 Digital Twin for live hazard data",
        "parameters": {
            "region": {"type": "string", "description": "Geographic region (e.g., 'DFW', 'North Dallas')"},
            "resolution_km": {"type": "number", "description": "Simulation resolution in kilometers (default: 1.0)"},
            "forecast_hours": {"type": "integer", "description": "Hours ahead to forecast (default: 6)"}
        }
    },
    {
        "name": "simulate_earth2_scenario",
        "description": "Run what-if simulation (e.g., 'What if hail increases by 0.5 inches?')",
        "parameters": {
            "region": {"type": "string"},
            "scenario": {"type": "object", "description": "Scenario modifications (e.g., {'hail_increase': 0.5})"}
        }
    },
    {
        "name": "start_earth2_monitor",
        "description": "Start persistent Earth-2 monitor that watches for specific conditions",
        "parameters": {
            "monitor_id": {"type": "string", "description": "Unique ID for this monitor"},
            "region": {"type": "string"},
            "trigger_condition": {"type": "string", "description": "Condition to watch for (e.g., 'hail > 2.0 inches')"}
        }
    },
    {
        "name": "check_earth2_health",
        "description": "Check Earth-2 connection health and sync confidence",
        "parameters": {}
    },
    {
        "name": "increase_earth2_resolution",
        "description": "Request higher resolution simulation for specific region (costs compute tokens)",
        "parameters": {
            "region": {"type": "string"},
            "target_km": {"type": "number", "description": "Target resolution in km (lower = higher detail)"}
        }
    },
    {
        "name": "get_earth2_timeline",
        "description": "Get hourly time-series forecast for time-slider UI",
        "parameters": {
            "region": {"type": "string"},
            "hours_ahead": {"type": "integer", "description": "How many hours to forecast"}
        }
    }
]
