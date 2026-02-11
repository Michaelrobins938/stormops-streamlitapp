"""
Roof Entity Graph - Identity Resolution and Asset Tracking

Links addresses, storm exposure, outreach history, and outcomes
into unified roof entities for causal impact analysis.
"""

import sqlite3
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class RoofEntity:
    """Unified roof entity combining location, exposure, and outcomes."""

    entity_id: str
    canonical_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zip_code: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Storm exposure history (event IDs)
    storm_events: List[str] = field(default_factory=list)

    # Outreach history (interaction IDs)
    outreach_history: List[str] = field(default_factory=list)

    # Outcomes
    inspections_scheduled: int = 0
    inspections_completed: int = 0
    jobs_sold: int = 0
    total_job_value: float = 0.0
    job_status: str = "uncontacted"  # uncontacted, contacted, scheduled, sold, closed

    # Risk data from RoofRiskIndex
    cumulative_risk_score: float = 0.0
    last_storm_date: Optional[str] = None

    # Source tracking (where this entity came from)
    source_records: Dict[str, str] = field(
        default_factory=dict
    )  # source_id -> entity_id

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if not k.startswith("_")}

    @classmethod
    def from_dict(cls, data: Dict) -> "RoofEntity":
        return cls(**data)


@dataclass
class OutreachInteraction:
    """Record of a single outreach attempt."""

    interaction_id: str
    entity_id: str
    playbook_type: (
        str  # "door_knock", "sms", "email", "phone", "door_sms", "door_phone"
    )
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    outcome: str = "attempted"  # attempted, no_answer, busy, voicemail, contact, callback_requested
    duration_seconds: Optional[int] = None
    notes: Optional[str] = None
    staff_id: Optional[str] = None
    campaign_id: Optional[str] = None


@dataclass
class OutcomeEvent:
    """Record of an outcome (inspection, job, etc.)."""

    outcome_id: str
    entity_id: str
    outcome_type: (
        str  # "inspection_scheduled", "inspection_completed", "job_sold", "job_closed"
    )
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    value: float = 0.0
    notes: Optional[str] = None
    staff_id: Optional[str] = None


class RoofEntityGraph:
    """
    Manages roof entities with identity resolution and relationship tracking.

    Supports probabilistic matching to merge records from multiple sources
    (CRM, spreadsheets, uploaded leads) into unified entities.
    """

    def __init__(self, db_path: str = "outputs/roof_entities.db"):
        """Initialize the entity graph with SQLite backing."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create all necessary tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roof_entities (
                entity_id TEXT PRIMARY KEY,
                canonical_address TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                zip_code TEXT,
                created_at TEXT,
                updated_at TEXT,
                storm_events TEXT,  -- JSON array of event IDs
                outreach_history TEXT,  -- JSON array of interaction IDs
                inspections_scheduled INTEGER DEFAULT 0,
                inspections_completed INTEGER DEFAULT 0,
                jobs_sold INTEGER DEFAULT 0,
                total_job_value REAL DEFAULT 0.0,
                job_status TEXT DEFAULT 'uncontacted',
                cumulative_risk_score REAL DEFAULT 0.0,
                last_storm_date TEXT,
                source_records TEXT  -- JSON dict mapping source_id -> merged_entity_id
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outreach_interactions (
                interaction_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                playbook_type TEXT NOT NULL,
                timestamp TEXT,
                outcome TEXT,
                duration_seconds INTEGER,
                notes TEXT,
                staff_id TEXT,
                campaign_id TEXT,
                FOREIGN KEY (entity_id) REFERENCES roof_entities(entity_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcome_events (
                outcome_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                outcome_type TEXT NOT NULL,
                timestamp TEXT,
                value REAL,
                notes TEXT,
                staff_id TEXT,
                FOREIGN KEY (entity_id) REFERENCES roof_entities(entity_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_merges (
                merge_id TEXT PRIMARY KEY,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                merge_type TEXT,
                confidence REAL,
                timestamp TEXT,
                reason TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_zip ON roof_entities(zip_code)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_address ON roof_entities(canonical_address)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_outreach_entity ON outreach_interactions(entity_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_outcomes_entity ON outcome_events(entity_id)
        """)

        conn.commit()
        conn.close()

    def _normalize_address(self, address: str) -> str:
        """Normalize address for matching."""
        if not address:
            return ""

        addr = address.lower().strip()
        addr = re.sub(r"\s+", " ", addr)
        addr = re.sub(r"[,\.]", "", addr)
        addr = re.sub(r"\bst\b\.?", "street", addr)
        addr = re.sub(r"\bave\b\.?", "avenue", addr)
        addr = re.sub(r"\brd\b\.?", "road", addr)
        addr = re.sub(r"\bdr\b\.?", "drive", addr)
        addr = re.sub(r"\bln\b\.?", "lane", addr)
        addr = re.sub(r"\bn\.?\s?", "north ", addr)
        addr = re.sub(r"\bs\.?\s?", "south ", addr)
        addr = re.sub(r"\be\.?\s?", "east ", addr)
        addr = re.sub(r"\bw\.?\s?", "west ", addr)
        return addr.strip()

    def _generate_entity_id(self) -> str:
        """Generate a unique entity ID."""
        return f"RE-{uuid.uuid4().hex[:12].upper()}"

    def upsert_from_record(
        self,
        address: str,
        zip_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        source_id: Optional[str] = None,
        risk_score: float = 0.0,
        last_storm_date: Optional[str] = None,
    ) -> Tuple[RoofEntity, bool]:
        """
        Insert or update a roof entity from a record.

        Returns:
            Tuple of (entity, was_merged) - was_merged=True if merged with existing
        """
        normalized = self._normalize_address(address)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT entity_id FROM roof_entities WHERE canonical_address = ?",
            (normalized,),
        )
        existing = cursor.fetchone()

        if existing:
            entity_id = existing[0]
            cursor.execute(
                """
                UPDATE roof_entities 
                SET updated_at = ?, cumulative_risk_score = ?, last_storm_date = ?,
                    source_records = ?
                WHERE entity_id = ?
                """,
                (
                    datetime.now().isoformat(),
                    risk_score,
                    last_storm_date,
                    json.dumps(
                        {
                            **(
                                json.loads(
                                    cursor.execute(
                                        "SELECT source_records FROM roof_entities WHERE entity_id = ?",
                                        (entity_id,),
                                    ).fetchone()[0]
                                    or "{}"
                                )
                            ),
                            source_id or "unknown": entity_id,
                        }
                    ),
                    entity_id,
                ),
            )
            conn.commit()
            entity = self.get_entity(entity_id)
            conn.close()
            return entity, True

        entity_id = self._generate_entity_id()
        entity = RoofEntity(
            entity_id=entity_id,
            canonical_address=normalized,
            latitude=latitude,
            longitude=longitude,
            zip_code=zip_code,
            cumulative_risk_score=risk_score,
            last_storm_date=last_storm_date,
            source_records={source_id or "unknown": entity_id} if source_id else {},
        )

        cursor.execute(
            """
            INSERT INTO roof_entities 
            (entity_id, canonical_address, latitude, longitude, zip_code, 
             created_at, updated_at, storm_events, outreach_history,
             inspections_scheduled, inspections_completed, jobs_sold, total_job_value,
             job_status, cumulative_risk_score, last_storm_date, source_records)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.entity_id,
                entity.canonical_address,
                entity.latitude,
                entity.longitude,
                entity.zip_code,
                entity.created_at,
                entity.updated_at,
                json.dumps(entity.storm_events),
                json.dumps(entity.outreach_history),
                entity.inspections_scheduled,
                entity.inspections_completed,
                entity.jobs_sold,
                entity.total_job_value,
                entity.job_status,
                entity.cumulative_risk_score,
                entity.last_storm_date,
                json.dumps(entity.source_records),
            ),
        )

        conn.commit()
        conn.close()
        return entity, False

    def find_potential_matches(
        self,
        address: str,
        zip_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        threshold: float = 0.85,
    ) -> List[Tuple[RoofEntity, float]]:
        """
        Find potential matching entities using fuzzy matching.

        Uses address normalization and optional geo-proximity.
        """
        normalized = self._normalize_address(address)
        potential = []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT entity_id, canonical_address FROM roof_entities WHERE zip_code = ?",
            (zip_code,),
        )
        zip_matches = cursor.fetchall()

        for entity_id, existing_addr in zip_matches:
            similarity = self._address_similarity(
                normalized, self._normalize_address(existing_addr)
            )
            if similarity >= threshold:
                entity = self.get_entity(entity_id)
                if entity:
                    potential.append((entity, similarity))

        if latitude and longitude:
            cursor.execute(
                "SELECT entity_id, latitude, longitude FROM roof_entities WHERE latitude IS NOT NULL"
            )
            geo_matches = cursor.fetchall()
            for entity_id, lat, lon in geo_matches:
                if entity_id in [e[0].entity_id for e in potential]:
                    continue
                dist = self._haversine_distance(latitude, longitude, lat, lon)
                if dist < 100:  # Within 100 meters
                    entity = self.get_entity(entity_id)
                    if entity:
                        potential.append((entity, max(0.9, 1.0 - dist / 1000)))

        conn.close()
        return sorted(potential, key=lambda x: x[1], reverse=True)

    def _address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate simple string similarity."""
        if addr1 == addr2:
            return 1.0
        if not addr1 or not addr2:
            return 0.0

        words1 = set(addr1.split())
        words2 = set(addr2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance in meters between two points."""
        import math

        R = 6371000  # Earth radius in meters

        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def merge_entities(
        self,
        source_entity_id: str,
        target_entity_id: str,
        merge_type: str = "manual",
        reason: str = "",
    ) -> RoofEntity:
        """
        Merge source entity into target entity.

        Combines storm events, outreach history, and outcomes.
        """
        source = self.get_entity(source_entity_id)
        target = self.get_entity(target_entity_id)

        if not source or not target:
            raise ValueError("Both entities must exist")

        combined_events = list(set(target.storm_events + source.storm_events))
        combined_outreach = list(set(target.outreach_history + source.outreach_history))

        merged_outcomes = {
            "inspections_scheduled": target.inspections_scheduled
            + source.inspections_scheduled,
            "inspections_completed": target.inspections_completed
            + source.inspections_completed,
            "jobs_sold": target.jobs_sold + source.jobs_sold,
            "total_job_value": target.total_job_value + source.total_job_value,
        }

        best_status_order = ["uncontacted", "contacted", "scheduled", "sold", "closed"]
        merged_status = max(
            [target.job_status, source.job_status],
            key=lambda x: best_status_order.index(x) if x in best_status_order else 0,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE roof_entities 
            SET storm_events = ?, outreach_history = ?,
                inspections_scheduled = ?, inspections_completed = ?,
                jobs_sold = ?, total_job_value = ?, job_status = ?,
                updated_at = ?, source_records = ?
            WHERE entity_id = ?
            """,
            (
                json.dumps(combined_events),
                json.dumps(combined_outreach),
                merged_outcomes["inspections_scheduled"],
                merged_outcomes["inspections_completed"],
                merged_outcomes["jobs_sold"],
                merged_outcomes["total_job_value"],
                merged_status,
                datetime.now().isoformat(),
                json.dumps(
                    {
                        **target.source_records,
                        **source.source_records,
                        f"merged_{source.entity_id}": target.entity_id,
                    }
                ),
                target.entity_id,
            ),
        )

        cursor.execute(
            """
            INSERT INTO entity_merges 
            (merge_id, source_entity_id, target_entity_id, merge_type, confidence, timestamp, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"MERGE-{uuid.uuid4().hex[:8].upper()}",
                source.entity_id,
                target.entity_id,
                merge_type,
                1.0,
                datetime.now().isoformat(),
                reason,
            ),
        )

        cursor.execute(
            "DELETE FROM roof_entities WHERE entity_id = ?", (source.entity_id,)
        )

        conn.commit()
        conn.close()

        return self.get_entity(target.entity_id)

    def add_outreach(
        self,
        entity_id: str,
        playbook_type: str,
        outcome: str = "attempted",
        staff_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> OutreachInteraction:
        """Record an outreach interaction."""
        interaction = OutreachInteraction(
            interaction_id=f"INT-{uuid.uuid4().hex[:8].upper()}",
            entity_id=entity_id,
            playbook_type=playbook_type,
            outcome=outcome,
            staff_id=staff_id,
            notes=notes,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO outreach_interactions 
            (interaction_id, entity_id, playbook_type, timestamp, outcome, 
             duration_seconds, notes, staff_id, campaign_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.interaction_id,
                interaction.entity_id,
                interaction.playbook_type,
                interaction.timestamp,
                interaction.outcome,
                interaction.duration_seconds,
                interaction.notes,
                interaction.staff_id,
                interaction.campaign_id,
            ),
        )

        cursor.execute(
            "UPDATE roof_entities SET outreach_history = ?, updated_at = ? WHERE entity_id = ?",
            (
                json.dumps([interaction.interaction_id]),
                datetime.now().isoformat(),
                entity_id,
            ),
        )

        conn.commit()
        conn.close()

        return interaction

    def record_outcome(
        self,
        entity_id: str,
        outcome_type: str,
        value: float = 0.0,
        staff_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> OutcomeEvent:
        """Record an outcome event."""
        outcome = OutcomeEvent(
            outcome_id=f"OUT-{uuid.uuid4().hex[:8].upper()}",
            entity_id=entity_id,
            outcome_type=outcome_type,
            value=value,
            staff_id=staff_id,
            notes=notes,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO outcome_events 
            (outcome_id, entity_id, outcome_type, timestamp, value, notes, staff_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome.outcome_id,
                outcome.entity_id,
                outcome.outcome_type,
                outcome.timestamp,
                outcome.value,
                outcome.notes,
                outcome.staff_id,
            ),
        )

        if outcome_type == "inspection_scheduled":
            cursor.execute(
                "UPDATE roof_entities SET inspections_scheduled = inspections_scheduled + 1, "
                "job_status = ?, updated_at = ? WHERE entity_id = ?",
                ("scheduled", datetime.now().isoformat(), entity_id),
            )
        elif outcome_type == "inspection_completed":
            cursor.execute(
                "UPDATE roof_entities SET inspections_completed = inspections_completed + 1, "
                "updated_at = ? WHERE entity_id = ?",
                (datetime.now().isoformat(), entity_id),
            )
        elif outcome_type == "job_sold":
            cursor.execute(
                "UPDATE roof_entities SET jobs_sold = jobs_sold + 1, "
                "total_job_value = total_job_value + ?, job_status = ?, updated_at = ? "
                "WHERE entity_id = ?",
                (value, "sold", datetime.now().isoformat(), entity_id),
            )
        elif outcome_type == "job_closed":
            cursor.execute(
                "UPDATE roof_entities SET job_status = 'closed', updated_at = ? "
                "WHERE entity_id = ?",
                (datetime.now().isoformat(), entity_id),
            )

        conn.commit()
        conn.close()

        return outcome

    def link_storm_event(self, entity_id: str, event_id: str):
        """Link a storm event to an entity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT storm_events FROM roof_entities WHERE entity_id = ?", (entity_id,)
        )
        result = cursor.fetchone()

        if result:
            events = json.loads(result[0] or "[]")
            if event_id not in events:
                events.append(event_id)
                cursor.execute(
                    "UPDATE roof_entities SET storm_events = ?, updated_at = ? WHERE entity_id = ?",
                    (json.dumps(events), datetime.now().isoformat(), entity_id),
                )

        conn.commit()
        conn.close()

    def get_entity(self, entity_id: str) -> Optional[RoofEntity]:
        """Retrieve an entity by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM roof_entities WHERE entity_id = ?", (entity_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))

        conn.close()

        return RoofEntity(
            entity_id=data["entity_id"],
            canonical_address=data["canonical_address"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            zip_code=data["zip_code"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            storm_events=json.loads(data["storm_events"] or "[]"),
            outreach_history=json.loads(data["outreach_history"] or "[]"),
            inspections_scheduled=data["inspections_scheduled"],
            inspections_completed=data["inspections_completed"],
            jobs_sold=data["jobs_sold"],
            total_job_value=data["total_job_value"],
            job_status=data["job_status"],
            cumulative_risk_score=data["cumulative_risk_score"],
            last_storm_date=data["last_storm_date"],
            source_records=json.loads(data["source_records"] or "{}"),
        )

    def get_entities_by_zip(self, zip_code: str) -> List[RoofEntity]:
        """Get all entities in a ZIP code."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT entity_id FROM roof_entities WHERE zip_code = ?", (zip_code,)
        )
        entity_ids = [row[0] for row in cursor.fetchall()]

        conn.close()

        return [e for e in [self.get_entity(eid) for eid in entity_ids] if e]

    def get_portfolio_stats(self, zip_codes: Optional[List[str]] = None) -> Dict:
        """Get aggregated statistics for the entity portfolio."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if zip_codes:
            placeholders = ",".join("?" * len(zip_codes))
            cursor.execute(
                f"""
                SELECT COUNT(*) as total,
                       SUM(inspections_scheduled) as total_scheduled,
                       SUM(inspections_completed) as total_completed,
                       SUM(jobs_sold) as total_sold,
                       SUM(total_job_value) as total_value,
                       AVG(cumulative_risk_score) as avg_risk
                FROM roof_entities WHERE zip_code IN ({placeholders})
                """,
                zip_codes,
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(inspections_scheduled) as total_scheduled,
                       SUM(inspections_completed) as total_completed,
                       SUM(jobs_sold) as total_sold,
                       SUM(total_job_value) as total_value,
                       AVG(cumulative_risk_score) as avg_risk
                FROM roof_entities
                """
            )

        row = cursor.fetchone()
        conn.close()

        return {
            "total_entities": row[0] or 0,
            "inspections_scheduled": row[1] or 0,
            "inspections_completed": row[2] or 0,
            "jobs_sold": row[3] or 0,
            "total_job_value": row[4] or 0.0,
            "avg_risk_score": row[5] or 0.0,
            "conversion_rate": (row[3] / row[0] * 100) if row[0] and row[3] else 0.0,
        }

    def export_entities(self, zip_codes: Optional[List[str]] = None) -> List[Dict]:
        """Export entities as list of dicts for analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if zip_codes:
            placeholders = ",".join("?" * len(zip_codes))
            cursor.execute(
                f"SELECT * FROM roof_entities WHERE zip_code IN ({placeholders})",
                zip_codes,
            )
        else:
            cursor.execute("SELECT * FROM roof_entities")

        columns = [desc[0] for desc in cursor.description]
        entities = []

        for row in cursor.fetchall():
            data = dict(zip(columns, row))
            data["storm_events"] = json.loads(data["storm_events"] or "[]")
            data["outreach_history"] = json.loads(data["outreach_history"] or "[]")
            data["source_records"] = json.loads(data["source_records"] or "{}")
            entities.append(data)

        conn.close()
        return entities


def batch_import(
    graph: RoofEntityGraph, records: List[Dict], source_name: str = "import"
) -> Dict:
    """
    Batch import records into the entity graph.

    Returns summary of imports, merges, and conflicts.
    """
    stats = {"imported": 0, "merged": 0, "conflicts": 0, "entities": []}

    for record in records:
        address = (
            record.get("address")
            or record.get("street")
            or record.get("property_address")
        )
        if not address:
            continue

        zip_code = record.get("zip") or record.get("zip_code")
        lat = record.get("latitude") or record.get("lat")
        lon = record.get("longitude") or record.get("lon")
        risk = record.get("risk_score") or record.get("cumulative_risk") or 0.0

        entity, was_merged = graph.upsert_from_record(
            address=address,
            zip_code=str(zip_code) if zip_code else None,
            latitude=float(lat) if lat else None,
            longitude=float(lon) if lon else None,
            source_id=f"{source_name}_{len(stats['entities'])}",
            risk_score=float(risk),
        )

        stats["entities"].append(entity.entity_id)
        if was_merged:
            stats["merged"] += 1
        else:
            stats["imported"] += 1

    return stats
