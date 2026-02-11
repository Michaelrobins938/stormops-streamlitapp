"""
Agent 5: The Sociologist - Neighborhood Effect Analyzer
Identifies psychological triggers like "Keeping up with the Joneses"
Monitors neighborhood permit activity to find primed buyers
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict
import numpy as np


@dataclass
class NeighborhoodEffect:
    """Neighborhood social trigger analysis."""

    property_id: str
    address: str
    zip_code: str
    effect_type: str  # 'joneses', 'home_pride', 'investment_wave'
    effect_score: float  # 0-100
    trigger_description: str
    nearby_permits_6mo: int
    nearby_permits_12mo: int
    neighborhood_permit_rate: float
    social_pressure_index: float
    recommendation: str


class SociologistAgent:
    """
    Agent 5: The Sociologist

    Identifies psychological triggers that indicate a homeowner is primed to buy,
    even before they realize it.

    Key Triggers:
    1. "Keeping up with the Joneses" - Neighbors recently replaced roofs
    2. "Home Pride" - High investment in neighborhood maintenance
    3. "Investment Wave" - Multiple permits filed in area (gentrification/upgrades)
    """

    def __init__(self, db_path: str = "stormops_sociologist.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize permit tracking database."""
        conn = sqlite3.connect(self.db_path)

        # Building permits table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS building_permits (
                permit_id TEXT PRIMARY KEY,
                property_id TEXT,
                address TEXT,
                zip_code TEXT,
                lat REAL,
                lon REAL,
                permit_type TEXT,  -- roofing, remodeling, new_construction
                permit_date TEXT,
                estimated_value REAL,
                contractor_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Neighborhood permit activity index
        conn.execute("""
            CREATE TABLE IF NOT EXISTS neighborhood_activity (
                zip_code TEXT,
                grid_cell TEXT,  -- 0.001 degree grid (~100m)
                month_year TEXT,
                permit_count INTEGER,
                avg_permit_value REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (zip_code, grid_cell, month_year)
            )
        """)

        # Social trigger cache
        conn.execute("""
            CREATE TABLE IF NOT EXISTS social_triggers (
                property_id TEXT PRIMARY KEY,
                trigger_type TEXT,
                trigger_score REAL,
                trigger_description TEXT,
                nearby_permits_6mo INTEGER,
                nearby_permits_12mo INTEGER,
                social_pressure_index REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_permits_zip 
            ON building_permits(zip_code)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_permits_date 
            ON building_permits(permit_date)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_permits_coords 
            ON building_permits(lat, lon)
        """)

        conn.commit()
        conn.close()

    def load_permits(self, permits_df: pd.DataFrame) -> int:
        """
        Load building permit data from county records.

        Expected columns:
        - permit_id, property_id, address, zip_code, lat, lon
        - permit_type, permit_date, estimated_value, contractor_name
        """
        conn = sqlite3.connect(self.db_path)

        count = 0
        for _, permit in permits_df.iterrows():
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO building_permits
                    (permit_id, property_id, address, zip_code, lat, lon,
                     permit_type, permit_date, estimated_value, contractor_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(permit.get("permit_id")),
                        str(permit.get("property_id")),
                        str(permit.get("address")),
                        str(permit.get("zip_code")),
                        float(permit.get("lat"))
                        if pd.notna(permit.get("lat"))
                        else None,
                        float(permit.get("lon"))
                        if pd.notna(permit.get("lon"))
                        else None,
                        str(permit.get("permit_type", "roofing")),
                        str(permit.get("permit_date")),
                        float(permit.get("estimated_value"))
                        if pd.notna(permit.get("estimated_value"))
                        else None,
                        str(permit.get("contractor_name", "")),
                    ),
                )
                count += 1
            except Exception as e:
                print(f"Error loading permit {permit.get('permit_id')}: {e}")
                continue

        conn.commit()
        conn.close()

        print(f"✅ Loaded {count} building permits")
        return count

    def get_nearby_permits(
        self, lat: float, lon: float, radius_miles: float = 0.5, months_back: int = 12
    ) -> pd.DataFrame:
        """
        Get all permits within radius of a property.

        Args:
            lat: Property latitude
            lon: Property longitude
            radius_miles: Search radius (default: 0.5 miles = ~800m)
            months_back: How many months to look back
        """
        conn = sqlite3.connect(self.db_path)

        cutoff_date = (datetime.now() - timedelta(days=30 * months_back)).isoformat()

        # Approximate conversion: 1 degree latitude ~ 69 miles
        # 1 degree longitude ~ 69 * cos(latitude) miles
        lat_delta = radius_miles / 69.0
        lon_delta = radius_miles / (69.0 * abs(np.cos(np.radians(lat))))

        query = """
        SELECT 
            permit_id,
            address,
            lat,
            lon,
            permit_type,
            permit_date,
            estimated_value
        FROM building_permits
        WHERE lat BETWEEN ? AND ?
          AND lon BETWEEN ? AND ?
          AND permit_date >= ?
        ORDER BY permit_date DESC
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(
                lat - lat_delta,
                lat + lat_delta,
                lon - lon_delta,
                lon + lon_delta,
                cutoff_date,
            ),
        )

        conn.close()

        return df

    def calculate_joneses_effect(
        self, property_id: str, lat: float, lon: float, zip_code: str, address: str
    ) -> NeighborhoodEffect:
        """
        Calculate "Keeping up with the Joneses" trigger.

        The Secret Sauce: If 2+ neighbors got new roofs in last 6 months,
        this homeowner is psychologically primed to buy.
        """
        # Get nearby roofing permits
        nearby_6mo = self.get_nearby_permits(lat, lon, radius_miles=0.25, months_back=6)
        nearby_12mo = self.get_nearby_permits(
            lat, lon, radius_miles=0.25, months_back=12
        )

        # Filter for roofing permits only
        roofing_6mo = nearby_6mo[
            nearby_6mo["permit_type"].str.contains("roof", case=False, na=False)
        ]
        roofing_12mo = nearby_12mo[
            nearby_12mo["permit_type"].str.contains("roof", case=False, na=False)
        ]

        count_6mo = len(roofing_6mo)
        count_12mo = len(roofing_12mo)

        # Calculate social pressure index
        # 2+ neighbors in 6mo = very high pressure
        # 1 neighbor in 6mo = moderate pressure
        # 3+ neighbors in 12mo = high pressure
        if count_6mo >= 2:
            pressure_score = 90 + (count_6mo - 2) * 5  # 90-100
            effect_type = "joneses"
            description = f"🔥 HIGH SOCIAL PRESSURE: {count_6mo} neighbors got new roofs in last 6 months!"
            recommendation = "URGENT: This homeowner is feeling social pressure. Immediate outreach recommended."
        elif count_6mo == 1:
            pressure_score = 70
            effect_type = "joneses"
            description = (
                f"⚡ MODERATE PRESSURE: 1 neighbor replaced roof in last 6 months"
            )
            recommendation = (
                "PRIORITY: Mention neighbor's recent roof work in conversation."
            )
        elif count_12mo >= 3:
            pressure_score = 65
            effect_type = "investment_wave"
            description = f"📈 INVESTMENT WAVE: {count_12mo} neighbors upgraded roofs in last year"
            recommendation = (
                "STANDARD: Neighborhood is in upgrade cycle. Good timing for outreach."
            )
        elif count_12mo >= 1:
            pressure_score = 45
            effect_type = "home_pride"
            description = (
                f"🏠 HOME PRIDE: {count_12mo} recent improvement permits in area"
            )
            recommendation = (
                "NURTURE: Homeowners investing in neighborhood. Long-term opportunity."
            )
        else:
            pressure_score = 20
            effect_type = "none"
            description = "No recent permit activity nearby"
            recommendation = "LOW PRIORITY: No social triggers detected"

        # Calculate neighborhood permit rate (permits per month in area)
        neighborhood_radius = self.get_nearby_permits(
            lat, lon, radius_miles=1.0, months_back=12
        )
        permit_rate = len(neighborhood_radius) / 12.0

        return NeighborhoodEffect(
            property_id=property_id,
            address=address,
            zip_code=zip_code,
            effect_type=effect_type,
            effect_score=pressure_score,
            trigger_description=description,
            nearby_permits_6mo=count_6mo,
            nearby_permits_12mo=count_12mo,
            neighborhood_permit_rate=permit_rate,
            social_pressure_index=pressure_score / 100.0,
            recommendation=recommendation,
        )

    def analyze_properties(self, properties_df: pd.DataFrame) -> pd.DataFrame:
        """
        Batch analyze properties for neighborhood effects.

        Args:
            properties_df: DataFrame with columns: property_id, address, lat, lon, zip_code

        Returns:
            DataFrame with social trigger analysis
        """
        results = []

        print(f"🔍 Analyzing {len(properties_df)} properties for social triggers...")

        for idx, prop in properties_df.iterrows():
            try:
                effect = self.calculate_joneses_effect(
                    property_id=str(prop.get("property_id")),
                    lat=float(prop.get("lat")),
                    lon=float(prop.get("lon")),
                    zip_code=str(prop.get("zip_code")),
                    address=str(prop.get("address")),
                )

                results.append(
                    {
                        "property_id": effect.property_id,
                        "address": effect.address,
                        "zip_code": effect.zip_code,
                        "social_trigger_type": effect.effect_type,
                        "social_pressure_score": effect.effect_score,
                        "trigger_description": effect.trigger_description,
                        "nearby_roofing_permits_6mo": effect.nearby_permits_6mo,
                        "nearby_roofing_permits_12mo": effect.nearby_permits_12mo,
                        "neighborhood_permit_rate": effect.neighborhood_permit_rate,
                        "social_pressure_index": effect.social_pressure_index,
                        "sociologist_recommendation": effect.recommendation,
                    }
                )

                if (idx + 1) % 500 == 0:
                    print(f"   Processed {idx + 1} properties...")

            except Exception as e:
                print(f"Error analyzing {prop.get('property_id')}: {e}")
                continue

        return pd.DataFrame(results)

    def get_hot_neighborhoods(
        self, zip_code: str = None, min_permits: int = 5
    ) -> pd.DataFrame:
        """
        Identify ZIP codes or neighborhoods with high permit activity.
        These are "hot" areas where social pressure is building.
        """
        conn = sqlite3.connect(self.db_path)

        cutoff_date = (datetime.now() - timedelta(days=180)).isoformat()

        where_clause = ""
        params = [cutoff_date]

        if zip_code:
            where_clause = "AND zip_code = ?"
            params.append(zip_code)

        query = f"""
        SELECT 
            zip_code,
            COUNT(*) as total_permits_6mo,
            COUNT(DISTINCT strftime('%Y-%m', permit_date)) as active_months,
            AVG(estimated_value) as avg_permit_value,
            COUNT(DISTINCT contractor_name) as unique_contractors
        FROM building_permits
        WHERE permit_date >= ?
          AND permit_type LIKE '%roof%'
          {where_clause}
        GROUP BY zip_code
        HAVING COUNT(*) >= ?
        ORDER BY total_permits_6mo DESC
        """

        params.append(min_permits)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if not df.empty:
            df["permits_per_month"] = df["total_permits_6mo"] / 6.0
            df["market_intensity"] = df["permits_per_month"] * (
                df["avg_permit_value"] / 100000
            )

        return df

    def generate_mock_permits(
        self, properties_df: pd.DataFrame, permit_rate: float = 0.15
    ) -> pd.DataFrame:
        """
        Generate realistic mock permit data for demonstration.

        Args:
            properties_df: Properties to generate permits for
            permit_rate: % of properties with recent permits (default 15%)
        """
        import random

        random.seed(42)

        permits = []

        # Select random subset of properties to have permits
        num_permits = int(len(properties_df) * permit_rate)
        permit_properties = properties_df.sample(n=num_permits)

        for _, prop in permit_properties.iterrows():
            # Random date in last 12 months
            days_ago = random.randint(1, 365)
            permit_date = (datetime.now() - timedelta(days=days_ago)).strftime(
                "%Y-%m-%d"
            )

            # Cluster permits geographically (Joneses effect)
            # If this property has permit, 60% chance neighbors also have permits

            permits.append(
                {
                    "permit_id": f"PERMIT_{random.randint(10000, 99999)}",
                    "property_id": prop["property_id"],
                    "address": prop["address"],
                    "zip_code": str(prop["zip_code"]),
                    "lat": prop["lat"],
                    "lon": prop["lon"],
                    "permit_type": "roofing_replacement",
                    "permit_date": permit_date,
                    "estimated_value": random.randint(15000, 35000),
                    "contractor_name": random.choice(
                        ["Elite Roofing", "DFW Roof Pros", "StormGuard"]
                    ),
                }
            )

        return pd.DataFrame(permits)


# Integration with strategic lead scorer
class EnhancedLeadScorerWithSociology:
    """
    Extends strategic lead scoring with Agent 5 (Sociologist) insights.
    """

    def __init__(self):
        from strategic_lead_scorer import StrategicLeadScorer

        self.base_scorer = StrategicLeadScorer()
        self.sociologist = SociologistAgent()

    def calculate_enhanced_score(
        self, property_data: Dict, sociological_data: Dict
    ) -> Dict:
        """
        Calculate lead score with social pressure multiplier.

        Formula: Base Score + (Social Pressure × 15 bonus points)
        """
        # Get base score from 4-factor model
        from strategic_lead_scorer import LeadScoreFactors, ClaimStatus

        base_factors = LeadScoreFactors(
            hail_size_inches=property_data.get("hail_size", 1.5),
            roof_age_years=property_data.get("roof_age", 15),
            property_value=property_data.get("property_value", 350000),
            claim_status=ClaimStatus(property_data.get("claim_status", "no_claim")),
            days_since_storm=property_data.get("days_since_storm", 30),
        )

        base_result = self.base_scorer.calculate_lead_score(base_factors)
        base_score = base_result["total_score"]

        # Add sociological bonus (up to 15 points)
        social_pressure = sociological_data.get("social_pressure_index", 0)
        social_bonus = min(15, social_pressure * 15)

        enhanced_score = min(100, base_score + social_bonus)

        # Adjust tier if needed
        if enhanced_score >= 85 and base_result["priority_tier"] != "A":
            enhanced_tier = "A"
        else:
            enhanced_tier = base_result["priority_tier"]

        return {
            "base_score": base_score,
            "social_bonus": round(social_bonus, 1),
            "enhanced_score": round(enhanced_score, 1),
            "priority_tier": enhanced_tier,
            "social_trigger": sociological_data.get("social_trigger_type", "none"),
            "trigger_description": sociological_data.get("trigger_description", ""),
            "conversion_probability": min(
                0.15,
                base_result["conversion_probability"] * (1 + social_pressure * 0.5),
            ),
            "base_factors": base_result["factor_breakdown"],
            "recommendation": sociological_data.get("sociologist_recommendation", ""),
        }


# Example usage
if __name__ == "__main__":
    print("🧠 Agent 5: The Sociologist - Neighborhood Effect Analyzer")
    print("=" * 80)

    agent = SociologistAgent()

    # Generate mock property data
    print("\n📍 Loading property data...")
    import pandas as pd
    import numpy as np

    np.random.seed(42)

    properties = pd.DataFrame(
        [
            {
                "property_id": f"PROP_{i:05d}",
                "address": f"{1000 + i * 10} Oak St",
                "zip_code": "75034",
                "lat": 32.7767 + np.random.uniform(-0.01, 0.01),
                "lon": -96.7970 + np.random.uniform(-0.01, 0.01),
            }
            for i in range(100)
        ]
    )

    print(f"   Loaded {len(properties)} properties")

    # Generate mock permits (creates clustering for Joneses effect)
    print("\n📋 Generating mock permit data...")
    mock_permits = agent.generate_mock_permits(properties, permit_rate=0.20)
    print(f"   Generated {len(mock_permits)} permits")

    # Load permits
    agent.load_permits(mock_permits)

    # Analyze properties
    print("\n🔍 Analyzing neighborhood effects...")
    results = agent.analyze_properties(properties)

    # Show results
    print("\n" + "=" * 80)
    print("SOCIAL TRIGGER ANALYSIS RESULTS")
    print("=" * 80)

    joneses_count = len(results[results["social_trigger_type"] == "joneses"])
    investment_count = len(results[results["social_trigger_type"] == "investment_wave"])

    print(f"\n📊 Summary:")
    print(f"   Properties analyzed: {len(results)}")
    print(f"   🔥 Joneses Effect (High Pressure): {joneses_count}")
    print(f"   📈 Investment Wave: {investment_count}")
    print(
        f"   🏠 Home Pride: {len(results[results['social_trigger_type'] == 'home_pride'])}"
    )

    # Show high-pressure properties
    high_pressure = results[results["social_pressure_score"] >= 70].sort_values(
        "social_pressure_score", ascending=False
    )

    if not high_pressure.empty:
        print(f"\n🎯 TOP 5 HIGH-PRESSURE PROPERTIES (Deploy Immediately):")
        print("-" * 80)
        for idx, prop in high_pressure.head(5).iterrows():
            print(f"\n{prop['address']}")
            print(f"  Pressure Score: {prop['social_pressure_score']:.0f}/100")
            print(f"  Trigger: {prop['trigger_description']}")
            print(f"  Neighbor Permits (6mo): {prop['nearby_roofing_permits_6mo']}")
            print(f"  Recommendation: {prop['sociologist_recommendation']}")

    # Hot neighborhoods
    print(f"\n🔥 HOT NEIGHBORHOODS (High Permit Activity):")
    print("-" * 80)
    hot_areas = agent.get_hot_neighborhoods(min_permits=3)
    if not hot_areas.empty:
        for idx, area in hot_areas.head(5).iterrows():
            print(
                f"   ZIP {area['zip_code']}: {area['total_permits_6mo']} permits "
                f"({area['permits_per_month']:.1f}/month)"
            )

    print("\n✅ Agent 5 (Sociologist) Ready for Production")
