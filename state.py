
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class Zone:
    zip_code: str
    impact_index: float = 0.0
    nowcast_eta: float = 0.0
    roof_count: int = 0
    selected: bool = False
    refined: bool = False
    risk_level: str = "Medium"
    details: str = ""

@dataclass
class Route:
    id: str
    name: str
    zones: List[str]
    doors: int = 0
    est_value: float = 0.0
    status: str = "Planned" # Planned, Assigned, Completed

@dataclass
class Job:
    id: str
    address: str
    zip_code: str
    job_type: str
    status: str = "Lead" # Lead, Inspected, Claim Filed, Approved, Install
    claim_complexity: str = "Standard"
    trust_assets: List[str] = field(default_factory=list)

@dataclass
class Mission:
    current_step: str = "detect_storm"
    play_score: int = 0
    show_nowcast: bool = False
    leads_generated: bool = False
    selected_priority: str = "All"
    active_filter: str = "All"
    selected_job: str = "Tear-off / Demo"
    bottleneck: str = "None Detected"
    
    checks: Dict[str, bool] = field(default_factory=lambda: {
        "storm_loaded": False,
        "zones_targeted": False,
        "routes_built": False,
        "claims_filed": False,
        "nurture_started": False
    })

@dataclass
class AppState:
    storm_id: Optional[str] = None
    storm_name: str = "Unknown Storm"
    last_sync: Optional[datetime] = None
    mission: Mission = field(default_factory=Mission)
    zones: Dict[str, Zone] = field(default_factory=dict)
    routes: List[Route] = field(default_factory=list)
    jobs: List[Job] = field(default_factory=list)
    refined_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    selected_rows: set = field(default_factory=set)
    routes_created: int = 0
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    lead_context: Any = None
    route_context: Any = None
    outreach_context: Any = None
    crm_connected: bool = False
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "doors_targeted": 0,
        "routes_built": 0,
        "inspections": 0,
        "claims_filed": 0,
        "reviews_sent": 0
    })
    # Map viewport state
    map_center_lat: float = 32.7767
    map_center_lon: float = -96.7970
    map_zoom: int = 9

    def to_dict(self):
        return {
            "storm_id": self.storm_id,
            "storm_name": self.storm_name,
            "mission": {
                "current_step": self.mission.current_step,
                "play_score": self.mission.play_score,
                "show_nowcast": self.mission.show_nowcast,
                "leads_generated": self.mission.leads_generated,
                "selected_priority": self.mission.selected_priority,
                "active_filter": self.mission.active_filter,
                "selected_job": self.mission.selected_job,
                "checks": self.mission.checks
            },
            "zones": {k: v.__dict__ for k, v in self.zones.items()},
            "routes": [r.__dict__ for r in self.routes],
            "jobs": [j.__dict__ for j in self.jobs],
            "refined_stats": self.refined_stats,
            "selected_rows": list(self.selected_rows),
            "routes_created": self.routes_created,
            "chat_history": self.chat_history,
            "crm_connected": self.crm_connected,
            "stats": self.stats,
            "map_center_lat": self.map_center_lat,
            "map_center_lon": self.map_center_lon,
            "map_zoom": self.map_zoom,
        }
