"""
Sidebar State Schema - AI-Native Control Plane
Defines the complete state machine that the AI can read and manipulate.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from datetime import datetime

ActionState = Literal["idle", "proposed", "running", "success", "error"]
ConnectionState = Literal["online", "degraded", "offline"]

@dataclass
class ActionButton:
    """Represents an executable action in the sidebar."""
    id: str
    label: str
    state: ActionState = "idle"
    progress: float = 0.0  # 0-100
    progress_message: str = ""
    enabled: bool = True
    proposed_by_ai: bool = False  # Ghost state
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "state": self.state,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "enabled": self.enabled,
            "proposed_by_ai": self.proposed_by_ai,
            "result_summary": self.result_summary,
            "error_message": self.error_message
        }

@dataclass
class ConnectionNode:
    """Represents an external service connection."""
    service: str
    state: ConnectionState
    last_check: datetime
    error_message: Optional[str] = None
    
    def to_dict(self):
        return {
            "service": self.service,
            "state": self.state,
            "last_check": self.last_check.isoformat(),
            "error_message": self.error_message
        }

@dataclass
class ActiveAgent:
    """Represents a persistent AI agent/watcher."""
    id: str
    name: str
    description: str
    status: Literal["listening", "triggered", "paused"]
    trigger_condition: str
    created_at: datetime
    last_triggered: Optional[datetime] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "trigger_condition": self.trigger_condition,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None
        }

@dataclass
class PendingApproval:
    """Represents AI-generated work awaiting human approval."""
    id: str
    type: Literal["drafts", "routes", "selections", "claims"]
    count: int
    preview: str
    created_at: datetime
    
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "count": self.count,
            "preview": self.preview,
            "created_at": self.created_at.isoformat()
        }

@dataclass
class ScoreBreakdown:
    """Detailed breakdown of Storm Play Score."""
    total: int
    detection: int
    targeting: int
    routing: int
    intel: int
    nurture: int
    gaps: List[Dict[str, any]] = field(default_factory=list)  # What's missing
    
    def to_dict(self):
        return {
            "total": self.total,
            "detection": self.detection,
            "targeting": self.targeting,
            "routing": self.routing,
            "intel": self.intel,
            "nurture": self.nurture,
            "gaps": self.gaps
        }

@dataclass
class SidebarState:
    """Complete sidebar state accessible by AI."""
    
    # Phase control
    current_phase: str
    phase_code: str
    autopilot_enabled: bool = False
    
    # Actions
    actions: Dict[str, ActionButton] = field(default_factory=dict)
    
    # Connections
    connections: Dict[str, ConnectionNode] = field(default_factory=dict)
    
    # Active agents
    agents: List[ActiveAgent] = field(default_factory=list)
    
    # Approval queue
    pending_approvals: List[PendingApproval] = field(default_factory=list)
    
    # Scoring
    score: ScoreBreakdown = field(default_factory=lambda: ScoreBreakdown(0, 0, 0, 0, 0, 0))
    
    # Resource metering
    compute_used: float = 0.0  # 0-100%
    api_calls_today: int = 0
    
    def to_dict(self):
        return {
            "current_phase": self.current_phase,
            "phase_code": self.phase_code,
            "autopilot_enabled": self.autopilot_enabled,
            "actions": {k: v.to_dict() for k, v in self.actions.items()},
            "connections": {k: v.to_dict() for k, v in self.connections.items()},
            "agents": [a.to_dict() for a in self.agents],
            "pending_approvals": [p.to_dict() for p in self.pending_approvals],
            "score": self.score.to_dict(),
            "compute_used": self.compute_used,
            "api_calls_today": self.api_calls_today
        }
    
    def get_next_best_action(self) -> Optional[str]:
        """AI determines the highest-value next action based on gaps."""
        if not self.score.gaps:
            return None
        
        # Return the action_id of the highest-impact gap
        sorted_gaps = sorted(self.score.gaps, key=lambda x: x.get("impact", 0), reverse=True)
        return sorted_gaps[0].get("action_id") if sorted_gaps else None
    
    def propose_action(self, action_id: str):
        """AI proposes an action (ghost state)."""
        if action_id in self.actions:
            self.actions[action_id].proposed_by_ai = True
    
    def execute_action(self, action_id: str):
        """Mark action as running."""
        if action_id in self.actions:
            self.actions[action_id].state = "running"
            self.actions[action_id].proposed_by_ai = False
    
    def complete_action(self, action_id: str, success: bool, summary: str = None, error: str = None):
        """Mark action as complete."""
        if action_id in self.actions:
            self.actions[action_id].state = "success" if success else "error"
            self.actions[action_id].progress = 100.0 if success else 0.0
            self.actions[action_id].result_summary = summary
            self.actions[action_id].error_message = error
