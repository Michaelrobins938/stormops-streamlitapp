"""
NOAA Historical Storm Data Pipeline
Automated ingestion of severe weather events with hail ≥1.5 inch filtering.
Integrates with Storm Events Database for comprehensive historical analysis.
"""

import requests
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import time
from dataclasses import dataclass


@dataclass
class StormEvent:
    """NOAA Storm Event record."""

    event_id: str
    event_date: datetime
    event_type: str
    state: str
    county: str
    hail_size: float  # inches
    wind_speed: float  # mph
    lat: float
    lon: float
    property_damage: Optional[float] = None
    crop_damage: Optional[float] = None
    source: str = "NOAA"


class NOAAStormPipeline:
    """
    Automated pipeline for NOAA Storm Events Database ingestion.

    Features:
    - Historical data retrieval (1950-present)
    - Severe hail filtering (≥1.5 inches strategic threshold)
    - County-level property damage tracking
    - Automated monthly refresh capability
    """

    NOAA_API_BASE = "https://www.ncdc.noaa.gov/stormevents/v1"
    HAIL_THRESHOLD = 1.5  # Strategic threshold: severe damage potential

    def __init__(self, db_path: str = "stormops_noaa.db"):
        self.db_path = db_path
        self._init_database()
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "StormOps-Geospatial-Intelligence/1.0"}
        )

    def _init_database(self):
        """Initialize NOAA storm events database."""
        conn = sqlite3.connect(self.db_path)

        # Storm events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS noaa_storm_events (
                event_id TEXT PRIMARY KEY,
                event_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                state TEXT NOT NULL,
                county TEXT,
                hail_size REAL,
                wind_speed REAL,
                lat REAL,
                lon REAL,
                property_damage REAL,
                crop_damage REAL,
                source TEXT DEFAULT 'NOAA',
                severity TEXT,
                ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Severe events index (≥1.5 inch hail)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_severe_hail 
            ON noaa_storm_events(hail_size) WHERE hail_size >= 1.5
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_date 
            ON noaa_storm_events(event_date)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_location 
            ON noaa_storm_events(state, county)
        """)

        # Ingestion log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT,
                end_date TEXT,
                state TEXT,
                events_ingested INTEGER,
                severe_events INTEGER,
                status TEXT,
                error_message TEXT,
                ingestion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def fetch_storm_events(
        self,
        start_date: str,
        end_date: str,
        state: str = None,
        event_types: List[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch storm events from NOAA API.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            state: State abbreviation (e.g., 'TX')
            event_types: List of event types ['Hail', 'Thunderstorm Wind', 'Tornado']

        Returns:
            DataFrame of storm events
        """
        if event_types is None:
            event_types = ["Hail", "Thunderstorm Wind", "Tornado"]

        all_events = []

        for event_type in event_types:
            print(f"   Fetching {event_type} events...")

            try:
                # NOAA Storm Events API v1
                url = f"{self.NOAA_API_BASE}/events"
                params = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "eventType": event_type,
                }

                if state:
                    params["state"] = state

                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    events = data.get("results", [])

                    for event in events:
                        parsed_event = self._parse_noaa_event(event)
                        if parsed_event:
                            all_events.append(parsed_event)

                    print(f"      Found {len(events)} events")

                else:
                    print(f"      Error: HTTP {response.status_code}")

            except Exception as e:
                print(f"      Error fetching {event_type}: {e}")

            # Rate limiting
            time.sleep(0.5)

        if all_events:
            df = pd.DataFrame([e.__dict__ for e in all_events])
            return df

        return pd.DataFrame()

    def _parse_noaa_event(self, raw_event: Dict) -> Optional[StormEvent]:
        """Parse raw NOAA event data into StormEvent object."""
        try:
            # Extract event date
            begin_date = raw_event.get("begin_date_time")
            if begin_date:
                event_date = datetime.strptime(begin_date, "%Y-%m-%dT%H:%M:%S")
            else:
                return None

            # Extract hail size (convert from inches if needed)
            hail_size = 0
            if "hail_size" in raw_event and raw_event["hail_size"]:
                try:
                    hail_size = float(raw_event["hail_size"])
                    # Convert from mm to inches if value seems too large
                    if hail_size > 100:
                        hail_size = hail_size / 25.4
                except:
                    pass

            # Extract wind speed
            wind_speed = 0
            if "magnitude" in raw_event and raw_event["magnitude"]:
                try:
                    wind_speed = float(raw_event["magnitude"])
                except:
                    pass

            # Extract damage amounts
            property_damage = self._parse_damage(raw_event.get("damage_property", "0"))
            crop_damage = self._parse_damage(raw_event.get("damage_crops", "0"))

            # Extract coordinates
            lat = raw_event.get("begin_lat", 0)
            lon = raw_event.get("begin_lon", 0)

            return StormEvent(
                event_id=str(raw_event.get("event_id", "")),
                event_date=event_date,
                event_type=raw_event.get("event_type", "Unknown"),
                state=raw_event.get("state", ""),
                county=raw_event.get("county", ""),
                hail_size=hail_size,
                wind_speed=wind_speed,
                lat=float(lat) if lat else 0,
                lon=float(lon) if lon else 0,
                property_damage=property_damage,
                crop_damage=crop_damage,
            )

        except Exception as e:
            print(f"Error parsing event: {e}")
            return None

    def _parse_damage(self, damage_str: str) -> float:
        """Parse damage string (e.g., '10.00K', '1.50M') to float."""
        if not damage_str or damage_str == "0":
            return 0.0

        damage_str = str(damage_str).upper().replace("$", "").replace(",", "")

        try:
            if "K" in damage_str:
                return float(damage_str.replace("K", "")) * 1000
            elif "M" in damage_str:
                return float(damage_str.replace("M", "")) * 1000000
            elif "B" in damage_str:
                return float(damage_str.replace("B", "")) * 1000000000
            else:
                return float(damage_str)
        except:
            return 0.0

    def ingest_storm_events(
        self,
        start_date: str,
        end_date: str,
        state: str = None,
        severity_threshold: float = 1.5,
    ) -> Dict:
        """
        Ingest storm events and save to database.

        Returns ingestion statistics.
        """
        print(f"\n🌩️  NOAA Storm Data Ingestion")
        print(f"   Period: {start_date} to {end_date}")
        print(f"   State: {state or 'All'}")
        print(f"   Hail Threshold: ≥{severity_threshold} inches")
        print("-" * 60)

        start_time = datetime.now()

        try:
            # Fetch events
            events_df = self.fetch_storm_events(start_date, end_date, state)

            if events_df.empty:
                print("   No events found")
                return {"status": "success", "events_ingested": 0, "severe_events": 0}

            # Filter severe events
            severe_mask = (events_df["hail_size"] >= severity_threshold) | (
                events_df["wind_speed"] >= 50
            )
            severe_events = events_df[severe_mask]

            # Save to database
            conn = sqlite3.connect(self.db_path)

            events_saved = 0
            for _, event in events_df.iterrows():
                try:
                    # Determine severity
                    if event["hail_size"] >= 2.5 or event["wind_speed"] >= 80:
                        severity = "EXTREME"
                    elif event["hail_size"] >= 2.0 or event["wind_speed"] >= 60:
                        severity = "MAJOR"
                    elif event["hail_size"] >= 1.5 or event["wind_speed"] >= 50:
                        severity = "SEVERE"
                    elif event["hail_size"] >= 1.0 or event["wind_speed"] >= 40:
                        severity = "MODERATE"
                    else:
                        severity = "MINOR"

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO noaa_storm_events
                        (event_id, event_date, event_type, state, county, 
                         hail_size, wind_speed, lat, lon, 
                         property_damage, crop_damage, severity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            event["event_id"],
                            event["event_date"].isoformat(),
                            event["event_type"],
                            event["state"],
                            event["county"],
                            event["hail_size"],
                            event["wind_speed"],
                            event["lat"],
                            event["lon"],
                            event["property_damage"],
                            event["crop_damage"],
                            severity,
                        ),
                    )
                    events_saved += 1

                except Exception as e:
                    print(f"   Error saving event {event['event_id']}: {e}")
                    continue

            conn.commit()

            # Log ingestion
            conn.execute(
                """
                INSERT INTO ingestion_log 
                (start_date, end_date, state, events_ingested, severe_events, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    start_date,
                    end_date,
                    state,
                    events_saved,
                    len(severe_events),
                    "success",
                ),
            )

            conn.commit()
            conn.close()

            duration = (datetime.now() - start_time).total_seconds()

            print(f"\n✅ Ingestion Complete")
            print(f"   Total Events: {events_saved:,}")
            print(f'   Severe Events (≥{severity_threshold}"): {len(severe_events):,}')
            print(f"   Duration: {duration:.1f}s")

            return {
                "status": "success",
                "events_ingested": events_saved,
                "severe_events": len(severe_events),
                "duration_seconds": duration,
            }

        except Exception as e:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                INSERT INTO ingestion_log 
                (start_date, end_date, state, events_ingested, severe_events, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (start_date, end_date, state, 0, 0, "error", str(e)),
            )
            conn.commit()
            conn.close()

            print(f"\n❌ Ingestion Failed: {e}")
            return {"status": "error", "error": str(e)}

    def get_severe_hail_events(
        self, state: str = None, days_back: int = 90
    ) -> pd.DataFrame:
        """
        Get severe hail events (≥1.5 inches) within date range.

        This is the primary feed for high-precision lead generation.
        """
        conn = sqlite3.connect(self.db_path)

        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        query = """
        SELECT 
            event_id,
            event_date,
            event_type,
            state,
            county,
            hail_size,
            wind_speed,
            lat,
            lon,
            property_damage,
            severity
        FROM noaa_storm_events
        WHERE hail_size >= 1.5
          AND event_date >= ?
        """

        params = [cutoff_date]

        if state:
            query += " AND state = ?"
            params.append(state)

        query += " ORDER BY event_date DESC, hail_size DESC"

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def get_storm_summary_by_county(self, state: str, years: int = 5) -> pd.DataFrame:
        """
        Get multi-year storm summary by county for risk analysis.
        """
        conn = sqlite3.connect(self.db_path)

        cutoff_date = (datetime.now() - timedelta(days=365 * years)).isoformat()

        query = """
        SELECT 
            county,
            COUNT(*) as total_events,
            SUM(CASE WHEN hail_size >= 1.5 THEN 1 ELSE 0 END) as severe_hail_events,
            SUM(CASE WHEN wind_speed >= 50 THEN 1 ELSE 0 END) as severe_wind_events,
            MAX(hail_size) as max_hail_recorded,
            MAX(wind_speed) as max_wind_recorded,
            SUM(property_damage) as total_property_damage,
            AVG(hail_size) as avg_hail_size,
            COUNT(DISTINCT strftime('%Y', event_date)) as years_with_events
        FROM noaa_storm_events
        WHERE state = ?
          AND event_date >= ?
          AND county IS NOT NULL
        GROUP BY county
        ORDER BY severe_hail_events DESC, total_property_damage DESC
        """

        df = pd.read_sql_query(query, conn, params=(state, cutoff_date))
        conn.close()

        return df

    def identify_high_risk_zip_codes(
        self, state: str, min_severe_events: int = 3
    ) -> pd.DataFrame:
        """
        Identify ZIP codes with frequent severe hail exposure.
        Requires spatial intersection with building footprints for precision.
        """
        # This would require spatial join with ZIP code boundaries
        # For now, return county-level data as proxy

        county_data = self.get_storm_summary_by_county(state, years=3)

        high_risk = county_data[county_data["severe_hail_events"] >= min_severe_events]

        return high_risk[
            [
                "county",
                "severe_hail_events",
                "max_hail_recorded",
                "total_property_damage",
                "years_with_events",
            ]
        ]

    def generate_monthly_refresh(self, state: str = "TX") -> Dict:
        """
        Automated monthly data refresh pipeline.

        Ingests last 30 days of storm activity and updates lead database.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        print(f"\n🔄 Monthly Refresh: {start_date.date()} to {end_date.date()}")

        # Ingest recent events
        result = self.ingest_storm_events(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            state=state,
            severity_threshold=1.0,  # Include moderate for completeness
        )

        # Get severe events for lead generation
        severe_events = self.get_severe_hail_events(state=state, days_back=30)

        return {
            "ingestion_result": result,
            "new_severe_events": len(severe_events),
            "last_refresh": datetime.now().isoformat(),
        }


# Integration with lead scoring
class StormLeadGenerator:
    """
        Combines NOAA storm data with building footprints and property records
    to generate precision-targeted leads.
    """

    def __init__(
        self,
        noaa_pipeline: NOAAStormPipeline,
        spatial_db_path: str = "stormops_spatial.db",
    ):
        self.noaa = noaa_pipeline
        self.spatial_db = spatial_db_path

    def generate_leads_from_storm(
        self, storm_event_id: str, min_score: int = 70
    ) -> pd.DataFrame:
        """
        Generate high-precision leads from a specific storm event.

        Combines:
        1. NOAA storm polygon/intensity
        2. Building footprints in affected area
        3. Property records (age, value)
        4. Claim status (first-mover detection)
        """
        # Get storm details
        conn = sqlite3.connect(self.noaa.db_path)
        storm_df = pd.read_sql_query(
            "SELECT * FROM noaa_storm_events WHERE event_id = ?",
            conn,
            params=(storm_event_id,),
        )
        conn.close()

        if storm_df.empty:
            return pd.DataFrame()

        storm = storm_df.iloc[0]

        # Get buildings within impact radius
        # In production, this would use precise polygon intersection
        impact_radius_miles = self._calculate_impact_radius(
            storm["hail_size"], storm["wind_speed"]
        )

        print(f"\n🎯 Storm: {storm_event_id}")
        print(f'   Hail: {storm["hail_size"]}" | Wind: {storm["wind_speed"]}mph')
        print(f"   Impact Radius: {impact_radius_miles} miles")
        print(f"   Location: {storm['county']}, {storm['state']}")

        # This would query the spatial database for affected buildings
        # For now, return storm metadata

        return storm_df

    def _calculate_impact_radius(self, hail_size: float, wind_speed: float) -> int:
        """Estimate storm impact radius based on severity."""
        if hail_size >= 2.5 or wind_speed >= 80:
            return 15  # miles
        elif hail_size >= 2.0 or wind_speed >= 60:
            return 12
        elif hail_size >= 1.5 or wind_speed >= 50:
            return 10
        elif hail_size >= 1.0 or wind_speed >= 40:
            return 7
        else:
            return 5


# Example usage
if __name__ == "__main__":
    print("🌩️  NOAA Storm Data Pipeline - Automated Severe Weather Ingestion")
    print("=" * 70)

    pipeline = NOAAStormPipeline()

    # Example: Get recent severe hail events in Texas
    print('\n📊 Recent Severe Hail Events (≥1.5") in Texas')
    print("-" * 70)

    recent_events = pipeline.get_severe_hail_events(state="TX", days_back=365)

    if not recent_events.empty:
        print(f"\n   Found {len(recent_events)} severe events")
        print("\n   Top 5 by hail size:")

        top_events = recent_events.nlargest(5, "hail_size")[
            ["event_date", "county", "hail_size", "wind_speed", "severity"]
        ]

        for _, event in top_events.iterrows():
            print(
                f"      {event['event_date'][:10]} | {event['county']} | "
                f'{event["hail_size"]}" hail | {event["severity"]}'
            )
    else:
        print("   No severe events found (database may be empty)")

    # County risk summary
    print("\n📈 County Risk Summary (5-year)")
    print("-" * 70)

    county_summary = pipeline.get_storm_summary_by_county("TX", years=5)

    if not county_summary.empty:
        top_counties = county_summary.head(5)
        for _, county in top_counties.iterrows():
            print(
                f"   {county['county']}: {county['severe_hail_events']} severe events | "
                f'Max: {county["max_hail_recorded"]}" | '
                f"${county['total_property_damage']:,.0f} damage"
            )

    print("\n✅ NOAA Pipeline Ready for Production")
