"""
Roof Risk Index - Cumulative Fatigue Scoring System
Tracks long-term roof stress from multiple storm events over time.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


class RoofRiskIndex:
    """
    Cumulative roof risk scoring system.

    Calculates a 0-100 "Roof Fatigue" score per ZIP code that:
    - Increases with each qualifying storm event
    - Decays slowly over time (roofs "recover" but retain stress history)
    - Considers storm intensity, duration, and frequency
    """

    def __init__(self, db_path: str = "outputs/roof_risk_index.db"):
        """Initialize with database connection."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create tables for risk tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Risk events table - tracks each storm impact
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zip_code TEXT,
                event_date TEXT,
                storm_score_max REAL,
                storm_score_mean REAL,
                max_wind REAL,
                hours_high_risk REAL,
                damage_risk TEXT,
                event_weight REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Risk index history - tracks cumulative score over time
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_index_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zip_code TEXT,
                calculation_date TEXT,
                cumulative_score REAL,
                risk_level TEXT,
                events_count INTEGER,
                last_major_event TEXT,
                trend_30day TEXT
            )
        """)

        # Create index separately (SQLite doesn't allow INDEX in CREATE TABLE)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_zip_date 
            ON risk_index_history(zip_code, calculation_date)
        """)

        # Portfolio summary - aggregated metrics per contractor
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id TEXT,
                calculation_date TEXT,
                total_addresses INTEGER,
                high_risk_count INTEGER,
                medium_risk_count INTEGER,
                low_risk_count INTEGER,
                avg_risk_score REAL,
                trend_direction TEXT
            )
        """)

        conn.commit()
        conn.close()

    def calculate_event_weight(
        self,
        storm_score_max: float,
        max_wind: float,
        hours_high_risk: float,
        damage_risk: str,
    ) -> float:
        """
        Calculate the impact weight of a single storm event (0-40 points).

        Higher intensity + longer duration = higher weight
        """
        # Base weight from storm score (0-20 points)
        score_weight = min(storm_score_max * 20, 20)

        # Wind contribution (0-10 points)
        # 25 m/s is significant, scales up to 40 m/s
        wind_weight = min((max_wind / 40) * 10, 10) if max_wind else 0

        # Duration contribution (0-10 points)
        # 6+ hours at high risk is significant
        duration_weight = min(hours_high_risk / 6 * 5, 10) if hours_high_risk else 0

        # Risk level multiplier
        risk_multiplier = {"High": 1.2, "Medium": 1.0, "Low": 0.8}.get(damage_risk, 1.0)

        total_weight = (score_weight + wind_weight + duration_weight) * risk_multiplier
        return min(total_weight, 40)  # Cap at 40 points per event

    def add_storm_event(
        self, zip_code: str, event_date: str, storm_data: Dict
    ) -> float:
        """
        Record a new storm event and return its weight.

        Args:
            zip_code: 5-digit ZIP code
            event_date: ISO date string (YYYY-MM-DD)
            storm_data: Dict with keys like storm_score_max, max_wind, etc.
        """
        event_weight = self.calculate_event_weight(
            storm_score_max=storm_data.get("storm_score_max", 0),
            max_wind=storm_data.get("max_wind_max", 0),
            hours_high_risk=storm_data.get("hours_high_risk_max", 0),
            damage_risk=storm_data.get("damage_risk", "Low"),
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO risk_events 
            (zip_code, event_date, storm_score_max, storm_score_mean, max_wind, 
             hours_high_risk, damage_risk, event_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                zip_code,
                event_date,
                storm_data.get("storm_score_max", 0),
                storm_data.get("storm_score_mean", 0),
                storm_data.get("max_wind_max", 0),
                storm_data.get("hours_high_risk_max", 0),
                storm_data.get("damage_risk", "Low"),
                event_weight,
            ),
        )

        conn.commit()
        conn.close()

        return event_weight

    def calculate_cumulative_risk(
        self, zip_code: str, as_of_date: Optional[str] = None, lookback_days: int = 365
    ) -> Dict:
        """
        Calculate cumulative roof risk score for a ZIP code.

        Formula: Sum of weighted events with time decay
        - Recent events (0-30 days): 100% weight
        - Medium-term (31-90 days): 70% weight
        - Long-term (91-365 days): 40% weight
        - Events > 1 year: 10% weight (minimal retention)

        Returns dict with score (0-100), risk level, and metadata.
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all events for this ZIP in lookback period
        start_date = (
            datetime.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=lookback_days)
        ).strftime("%Y-%m-%d")

        cursor.execute(
            """
            SELECT event_date, event_weight, damage_risk, max_wind
            FROM risk_events
            WHERE zip_code = ? AND event_date >= ?
            ORDER BY event_date DESC
        """,
            (zip_code, start_date),
        )

        events = cursor.fetchall()
        conn.close()

        if not events:
            return {
                "zip_code": zip_code,
                "cumulative_score": 0,
                "risk_level": "Low",
                "events_count": 0,
                "last_major_event": None,
                "recent_events": [],
                "fatigue_index": "New",
            }

        # Calculate time-decayed cumulative score
        cumulative_score = 0
        recent_events = []
        last_major_event = None

        for event_date_str, weight, risk, max_wind in events:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
            calc_date = datetime.strptime(as_of_date, "%Y-%m-%d")
            days_ago = (calc_date - event_date).days

            # Apply time decay
            if days_ago <= 30:
                decay_factor = 1.0
            elif days_ago <= 90:
                decay_factor = 0.7
            elif days_ago <= 365:
                decay_factor = 0.4
            else:
                decay_factor = 0.1

            weighted_score = weight * decay_factor
            cumulative_score += weighted_score

            # Track major events (High risk or > 20 m/s wind)
            if risk == "High" or (max_wind and max_wind > 20):
                if (
                    last_major_event is None
                    or days_ago
                    < (calc_date - datetime.strptime(last_major_event, "%Y-%m-%d")).days
                ):
                    last_major_event = event_date_str

            recent_events.append(
                {
                    "date": event_date_str,
                    "days_ago": days_ago,
                    "weight": weight,
                    "decayed_weight": weighted_score,
                    "risk": risk,
                }
            )

        # Cap at 100
        cumulative_score = min(cumulative_score, 100)

        # Determine risk level
        if cumulative_score >= 60:
            risk_level = "High"
        elif cumulative_score >= 35:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        # Calculate fatigue index (descriptive)
        if cumulative_score >= 80:
            fatigue_index = "Critical"
        elif cumulative_score >= 60:
            fatigue_index = "Severe"
        elif cumulative_score >= 40:
            fatigue_index = "Elevated"
        elif cumulative_score >= 20:
            fatigue_index = "Moderate"
        else:
            fatigue_index = "Low"

        # Calculate trend (compare to 30 days ago)
        trend = self._calculate_trend(zip_code, as_of_date)

        return {
            "zip_code": zip_code,
            "cumulative_score": round(cumulative_score, 1),
            "risk_level": risk_level,
            "fatigue_index": fatigue_index,
            "events_count": len(events),
            "last_major_event": last_major_event,
            "recent_events": recent_events[:5],  # Last 5 events
            "trend_30day": trend,
            "next_inspection_recommended": cumulative_score > 40,
        }

    def _calculate_trend(self, zip_code: str, as_of_date: str) -> str:
        """Calculate 30-day trend direction."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current score
        current_date = datetime.strptime(as_of_date, "%Y-%m-%d")
        thirty_days_ago = (current_date - timedelta(days=30)).strftime("%Y-%m-%d")
        sixty_days_ago = (current_date - timedelta(days=60)).strftime("%Y-%m-%d")

        # Count events in last 30 days vs previous 30 days
        cursor.execute(
            """
            SELECT 
                SUM(CASE WHEN event_date >= ? THEN event_weight ELSE 0 END) as recent,
                SUM(CASE WHEN event_date < ? AND event_date >= ? THEN event_weight ELSE 0 END) as previous
            FROM risk_events
            WHERE zip_code = ? AND event_date >= ?
        """,
            (
                thirty_days_ago,
                thirty_days_ago,
                sixty_days_ago,
                zip_code,
                sixty_days_ago,
            ),
        )

        result = cursor.fetchone()
        conn.close()

        if result and result[0] is not None and result[1] is not None:
            recent, previous = result
            if recent > previous * 1.5:
                return "Rising ↑"
            elif recent < previous * 0.5:
                return "Falling ↓"
            else:
                return "Stable →"

        return "Insufficient data"

    def get_portfolio_risk_summary(
        self, zip_codes: List[str], as_of_date: Optional[str] = None
    ) -> Dict:
        """
        Get aggregated risk metrics for a portfolio of ZIP codes.

        Args:
            zip_codes: List of ZIP codes in portfolio
            as_of_date: Calculation date

        Returns:
            Dict with portfolio-wide risk statistics
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        risks = []
        for zip_code in zip_codes:
            risk_data = self.calculate_cumulative_risk(zip_code, as_of_date)
            risks.append(risk_data)

        if not risks:
            return {"error": "No ZIP codes provided"}

        df = pd.DataFrame(risks)

        return {
            "total_zips": len(zip_codes),
            "high_risk_count": len(df[df["risk_level"] == "High"]),
            "medium_risk_count": len(df[df["risk_level"] == "Medium"]),
            "low_risk_count": len(df[df["risk_level"] == "Low"]),
            "avg_risk_score": df["cumulative_score"].mean(),
            "max_risk_score": df["cumulative_score"].max(),
            "zips_needing_inspection": len(df[df["cumulative_score"] > 40]),
            "trend_direction": "Mixed",  # Would calculate from individual trends
        }

    def export_risk_report(
        self, zip_codes: List[str], as_of_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Export risk data for all ZIPs as a DataFrame."""
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        data = []
        for zip_code in zip_codes:
            risk = self.calculate_cumulative_risk(zip_code, as_of_date)
            data.append(
                {
                    "zip_code": risk["zip_code"],
                    "cumulative_score": risk["cumulative_score"],
                    "risk_level": risk["risk_level"],
                    "fatigue_index": risk["fatigue_index"],
                    "events_count": risk["events_count"],
                    "last_major_event": risk["last_major_event"],
                    "trend": risk["trend_30day"],
                    "inspection_recommended": risk["next_inspection_recommended"],
                }
            )

        return pd.DataFrame(data)


# Utility functions


def initialize_from_historical_storms(db_path: str, storm_history_df: pd.DataFrame):
    """
    Initialize the risk index database from historical storm data.

    Args:
        db_path: Path to SQLite database
        storm_history_df: DataFrame with columns:
            - zip_code
            - event_date
            - storm_score_max
            - storm_score_mean
            - max_wind_max
            - hours_high_risk_max
            - damage_risk
    """
    risk_index = RoofRiskIndex(db_path)

    for _, row in storm_history_df.iterrows():
        risk_index.add_storm_event(
            zip_code=str(row["zip_code"]),
            event_date=row["event_date"],
            storm_data=row.to_dict(),
        )

    return risk_index


def get_maintenance_recommendation(
    cumulative_score: float, fatigue_index: str, roof_age_years: Optional[int] = None
) -> str:
    """
    Generate maintenance recommendation based on risk score.

    Args:
        cumulative_score: 0-100 risk score
        fatigue_index: Descriptive fatigue level
        roof_age_years: Optional roof age for context

    Returns:
        Recommendation text
    """
    if cumulative_score >= 80:
        base_rec = "URGENT: Full roof inspection recommended within 30 days. High probability of hidden damage."
    elif cumulative_score >= 60:
        base_rec = "Priority inspection recommended within 60 days. Schedule before next storm season."
    elif cumulative_score >= 40:
        base_rec = "Standard inspection recommended within 90 days. Monitor for changes after future storms."
    elif cumulative_score >= 20:
        base_rec = "Routine maintenance check suggested. Good time to clear gutters and check flashing."
    else:
        base_rec = "Low risk. Annual inspection sufficient."

    if roof_age_years:
        if roof_age_years > 20 and cumulative_score > 30:
            base_rec += f" Given roof age ({roof_age_years} years), consider proactive replacement planning."
        elif roof_age_years > 15 and cumulative_score > 50:
            base_rec += f" Roof age ({roof_age_years} years) combined with storm history suggests higher vulnerability."

    return base_rec
