"""
Job Intelligence Module for Causal Attribution
Instruments individual jobs as full funnels for marketing science analysis.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import pandas as pd
import sqlite3
import os


class Stage(Enum):
    LEAD_CREATED = "lead_created"
    INSPECTION_SET = "inspection_set"
    INSPECTION_DONE = "inspection_done"
    ESTIMATE_DELIVERED = "estimate_delivered"
    SIGNED = "signed"
    CLAIM_FILED = "claim_filed"
    ADJUSTER_MEETING = "adjuster_meeting"
    APPROVED = "approved"
    BUILD_SCHEDULED = "build_scheduled"
    BUILD_COMPLETED = "build_completed"
    INVOICED = "invoiced"
    PAID = "paid"


class TouchType(Enum):
    KNOCK = "KNOCK"
    CALL = "CALL"
    TEXT = "TEXT"
    EMAIL = "EMAIL"
    VISIT = "VISIT"
    E_SIGN = "E-SIGN"
    INTERNAL = "INTERNAL"
    PAYMENT = "PAYMENT"
    FACEBOOK = "FACEBOOK"
    REFERRAL = "REFERRAL"
    YARD_SIGN = "YARD_SIGN"
    WEBSITE = "WEBSITE"


@dataclass
class Touchpoint:
    timestamp: str
    touch_type: str
    actor: str
    channel: str
    stage: Optional[str] = None
    notes: str = ""
    duration_min: Optional[int] = None


@dataclass
class StageTransition:
    from_stage: str
    to_stage: str
    timestamp: str
    touches_since: int = 0
    hours_elapsed: float = 0.0
    key_touches: List[str] = field(default_factory=list)


# Default stage order for new jobs
DEFAULT_STAGES = [
    "lead_created",
    "inspection_set",
    "inspection_done",
    "estimate_delivered",
    "claim_filed",
    "adjuster_meeting",
    "approved",
    "signed",
    "build_scheduled",
    "build_completed",
    "invoiced",
    "paid",
]

# Default touch types
DEFAULT_TOUCH_TYPES = [
    "KNOCK",
    "CALL",
    "TEXT",
    "EMAIL",
    "VISIT",
    "E-SIGN",
    "INTERNAL",
    "PAYMENT",
]


class JobIntelligenceDB:
    """
    SQLite-backed job intelligence storage.
    Enables multi-job analysis and rolling averages.
    """

    def __init__(self, db_path: str = "outputs/job_intelligence.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database with schema for jobs, events, and rules."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Jobs table
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                address TEXT,
                job_type TEXT,
                value REAL,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                total_touches INTEGER,
                duration_days INTEGER
            )
        """)

        # Events table
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                timestamp TEXT,
                channel TEXT,
                actor TEXT,
                notes TEXT,
                stage TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        # Stage transitions table
        c.execute("""
            CREATE TABLE IF NOT EXISTS transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                from_stage TEXT,
                to_stage TEXT,
                hours_elapsed REAL,
                key_touches TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        # Playbook rules table
        c.execute("""
            CREATE TABLE IF NOT EXISTS playbook_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule TEXT,
                rationale TEXT,
                priority TEXT,
                source_job TEXT,
                created_at TEXT,
                enabled INTEGER DEFAULT 1
            )
        """)

        conn.commit()
        conn.close()

    def save_job(self, job_data: Dict):
        """Save or update a job."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO jobs (job_id, address, job_type, value, status, created_at, completed_at, total_touches, duration_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                job_data.get("job_id"),
                job_data.get("address"),
                job_data.get("job_type"),
                job_data.get("value"),
                job_data.get("status", "active"),
                job_data.get("created_at"),
                job_data.get("completed_at"),
                job_data.get("total_touches", 0),
                job_data.get("duration_days", 0),
            ),
        )
        conn.commit()
        conn.close()

    def save_event(self, job_id: str, event: Dict):
        """Save an event for a job."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO events (job_id, timestamp, channel, actor, notes, stage)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                job_id,
                event.get("timestamp"),
                event.get("channel"),
                event.get("actor"),
                event.get("notes"),
                event.get("stage"),
            ),
        )
        conn.commit()
        conn.close()

    def save_transition(self, job_id: str, transition: StageTransition):
        """Save a stage transition."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO transitions (job_id, from_stage, to_stage, hours_elapsed, key_touches)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                job_id,
                transition.from_stage,
                transition.to_stage,
                transition.hours_elapsed,
                ",".join(transition.key_touches),
            ),
        )
        conn.commit()
        conn.close()

    def save_rule(self, rule: Dict):
        """Save a playbook rule."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO playbook_rules (rule, rationale, priority, source_job, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                rule.get("rule"),
                rule.get("rationale"),
                rule.get("priority"),
                rule.get("source_job"),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_recent_jobs(self, limit: int = 5) -> pd.DataFrame:
        """Get recent jobs for analysis."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            f"""
            SELECT * FROM jobs ORDER BY created_at DESC LIMIT {limit}
        """,
            conn,
        )
        conn.close()
        return df

    def get_avg_days_by_stage(self) -> Dict[str, float]:
        """Calculate average days between stages from completed jobs."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT from_stage, to_stage, AVG(hours_elapsed / 24) as avg_days
            FROM transitions
            GROUP BY from_stage, to_stage
        """)
        results = c.fetchall()
        conn.close()
        return {f"{r[0]}→{r[1]}": r[2] for r in results if r[2]}

    def get_rule_compliance(self, job_id: str = None) -> Dict[str, int]:
        """Check how many rules were followed for jobs."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if job_id:
            c.execute(
                """
                SELECT COUNT(*) FROM events e
                WHERE e.job_id = ?
            """,
                (job_id,),
            )
        else:
            c.execute("SELECT COUNT(*) FROM events")
        total_events = c.fetchone()[0]
        conn.close()
        return {"total_events": total_events}

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary stats for dashboard widget."""
        jobs_df = self.get_recent_jobs(10)
        stage_avgs = self.get_avg_days_by_stage()

        return {
            "total_jobs": len(jobs_df) if not jobs_df.empty else 0,
            "avg_duration": jobs_df["duration_days"].mean() if not jobs_df.empty else 0,
            "avg_touches": jobs_df["total_touches"].mean() if not jobs_df.empty else 0,
            "stage_averages": stage_avgs,
        }


# Mock job data for JOB-ARK-2026-001
MOCK_JOB_EVENTS = [
    {
        "timestamp": "2026-01-28 17:20",
        "channel": "KNOCK",
        "actor": "Austin",
        "notes": "Initial contact created lead",
    },
    {
        "timestamp": "2026-01-28 19:05",
        "channel": "TEXT",
        "actor": "Austin",
        "notes": "Sent inspection confirmation",
    },
    {
        "timestamp": "2026-01-30 10:02",
        "channel": "CALL",
        "actor": "Austin",
        "notes": "Walked homeowner through filing claim",
    },
    {
        "timestamp": "2026-02-04 11:08",
        "channel": "VISIT",
        "actor": "Austin",
        "notes": "Met adjuster on site, verified damage corridor",
    },
    {
        "timestamp": "2026-02-28 15:42",
        "channel": "PAYMENT",
        "actor": "Office",
        "notes": "Replacement verified, claim paid",
    },
]

# Stage transitions with timestamps
STAGE_TIMELINE = {
    "lead_created": "2026-01-28 17:20",
    "inspection_set": "2026-01-28 19:05",
    "inspection_done": "2026-01-29 16:05",
    "estimate_delivered": "2026-01-29 21:12",
    "signed": "2026-02-07 18:01",
    "claim_filed": "2026-01-30 10:02",
    "adjuster_meeting": "2026-02-04 11:08",
    "approved": "2026-02-07 14:23",
    "build_scheduled": "2026-02-09 08:45",
    "build_completed": "2026-02-13 16:55",
    "invoiced": "2026-02-14 10:18",
    "paid": "2026-02-28 15:42",
}

# Key delays
DELAYS = {
    "claim_filed_to_adjuster": {
        "from": "2026-01-30 10:02",
        "to": "2026-02-04 11:08",
        "days": 5.0,
        "cause": "CARRIER_SCHEDULING",
    },
    "build_completed_to_paid": {
        "from": "2026-02-13 16:55",
        "to": "2026-02-28 15:42",
        "days": 14.9,
        "cause": "CARRIER_CHECK_TIMING",
    },
}


class JobIntelligence:
    """
    Causal attribution engine for individual roofing jobs.
    Tracks touchpoints, stage transitions, and identifies what actually drove progress.
    """

    def __init__(self, job_id: str, events: List[Dict]):
        self.job_id = job_id
        self.events = events
        self.timeline = self._build_timeline()
        self.transitions = self._identify_transitions()
        self.attribution_matrix = self._build_attribution_matrix()
        self.causal_insights = self._analyze_causality()

    def _build_timeline(self) -> pd.DataFrame:
        """Convert events to sorted DataFrame."""
        df = pd.DataFrame(self.events)
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp_dt").reset_index(drop=True)
        return df

    def _identify_transitions(self) -> List[StageTransition]:
        """Identify when jobs moved between stages."""
        transitions = []
        stages_ordered = list(STAGE_TIMELINE.keys())

        for i, from_stage in enumerate(stages_ordered[:-1]):
            to_stage = stages_ordered[i + 1]
            from_time = datetime.fromisoformat(STAGE_TIMELINE[from_stage])
            to_time = datetime.fromisoformat(STAGE_TIMELINE[to_stage])

            # Count touches between stages
            touches_between = self.timeline[
                (self.timeline["timestamp_dt"] >= from_time)
                & (self.timeline["timestamp_dt"] <= to_time)
            ]

            # Identify key touches (most impactful)
            channel_counts = touches_between["channel"].value_counts()
            key_touches = [str(c) for c in channel_counts.head(3).index.tolist()]

            transitions.append(
                StageTransition(
                    from_stage=from_stage,
                    to_stage=to_stage,
                    timestamp=STAGE_TIMELINE[to_stage],
                    touches_since=len(touches_between),
                    hours_elapsed=(to_time - from_time).total_seconds() / 3600,
                    key_touches=key_touches,
                )
            )

        return transitions

    def _build_attribution_matrix(self) -> pd.DataFrame:
        """Build touch → stage transition matrix."""
        touch_types = ["KNOCK", "CALL", "TEXT", "EMAIL", "VISIT", "E-SIGN", "INTERNAL"]
        stage_pairs = [
            ("lead_created", "inspection_set"),
            ("inspection_set", "inspection_done"),
            ("inspection_done", "estimate_delivered"),
            ("estimate_delivered", "claim_filed"),
            ("claim_filed", "adjuster_meeting"),
            ("adjuster_meeting", "approved"),
            ("approved", "signed"),
            ("signed", "build_scheduled"),
            ("build_scheduled", "build_completed"),
            ("build_completed", "invoiced"),
            ("invoiced", "paid"),
        ]

        matrix = pd.DataFrame(
            0, index=touch_types, columns=[f"{p[0]}→{p[1]}" for p in stage_pairs]
        )

        for trans in self.transitions:
            col = f"{trans.from_stage}→{trans.to_stage}"
            if col in matrix.columns:
                for touch in trans.key_touches:
                    if touch in matrix.index:
                        matrix.loc[touch, col] += 1

        return matrix

    def _analyze_causality(self) -> Dict[str, Any]:
        """Generate causal insights and counterfactuals."""
        insights = {
            "critical_touches": [],
            "bottlenecks": [],
            "counterfactuals": [],
            "rules_for_next_jobs": [],
        }

        # Identify critical touches
        critical_touches = [
            (
                "KNOCK",
                "lead_created→inspection_set",
                "Initial contact created the lead",
            ),
            (
                "TEXT",
                "estimate_delivered→claim_filed",
                "Follow-up maintained momentum",
            ),
            (
                "CALL",
                "claim_filed→adjuster_meeting",
                "Filing support accelerated scheduling",
            ),
            (
                "VISIT",
                "adjuster_meeting→approved",
                "On-site technical support ensured approval",
            ),
        ]

        for touch, transition, reasoning in critical_touches:
            if transition in self.attribution_matrix.columns:
                insights["critical_touches"].append(
                    {
                        "touch": touch,
                        "transition": transition,
                        "reasoning": reasoning,
                        "impact_score": int(
                            self.attribution_matrix.loc[touch, transition]
                        )
                        if touch in self.attribution_matrix.index
                        else 0,
                    }
                )

        # Identify bottlenecks
        delays_sorted = sorted(DELAYS.items(), key=lambda x: x[1]["days"], reverse=True)
        for delay_id, delay in delays_sorted:
            insights["bottlenecks"].append(
                {
                    "phase": delay_id,
                    "from": delay["from"],
                    "to": delay["to"],
                    "days": delay["days"],
                    "cause": delay["cause"],
                    "recommendation": self._get_delay_recommendation(delay["cause"]),
                }
            )

        # Generate actionable rules
        insights["rules_for_next_jobs"] = [
            {
                "rule": "Execute confirmation protocol within 2 hours of contact",
                "priority": "HIGH",
            },
            {
                "rule": "Target adjuster verification within 48 hours of filing",
                "priority": "HIGH",
            },
            {
                "rule": "Finalize documentation same-day as approval",
                "priority": "MEDIUM",
            },
        ]

        return insights

    def _get_delay_recommendation(self, cause: str) -> str:
        """Get recommendation for specific delay cause."""
        recommendations = {
            "CARRIER_SCHEDULING": "Request expedited adjuster assignment",
            "CARRIER_CHECK_TIMING": "Coordinate homeowner bank verification",
            "WEATHER": "Activate backup indoor crews",
            "HOMEOWNER_UNAVAILABLE": "Deploy virtual inspection protocol",
            "MATERIAL_DELIVERY": "Pre-stage inventory at approval phase",
        }
        return recommendations.get(cause, "Investigate root cause; update protocol")

    def get_summary(self) -> Dict[str, Any]:
        """Get job summary metrics."""
        return {
            "job_id": self.job_id,
            "total_touches": len(self.timeline),
            "duration_days": (
                datetime.fromisoformat(STAGE_TIMELINE["paid"])
                - datetime.fromisoformat(STAGE_TIMELINE["lead_created"])
            ).days,
            "channels_used": self.timeline["channel"].unique().tolist(),
            "primary_actor": self.timeline["actor"].mode().iloc[0]
            if len(self.timeline) > 0
            else "UNKNOWN",
            "key_bottleneck": DELAYS.get("claim_filed_to_adjuster", {}).get(
                "cause", "UNKNOWN"
            ),
        }


def run_job_intelligence_demo():
    """Run demonstration of job intelligence on mock job."""
    job = JobIntelligence(job_id="JOB-ARK-2026-001", events=MOCK_JOB_EVENTS)

    summary = job.get_summary()
    print(f"ANALYSIS COMPLETE: {summary['job_id']}")
    print(f"DURATION: {summary['duration_days']} DAYS")
    print(f"PRIMARY ACTOR: {summary['primary_actor']}")

    return job


if __name__ == "__main__":
    run_job_intelligence_demo()
