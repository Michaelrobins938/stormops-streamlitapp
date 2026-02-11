"""
Property Data Integration Module
Hooks for 3rd-party property and roof data sources.
Enables per-building risk scoring when data is available.
"""

import pandas as pd
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PropertyData:
    """Property data structure."""

    address: str
    zip_code: str
    roof_age: Optional[int] = None
    roof_type: Optional[str] = None
    roof_size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    has_pool: bool = False
    has_solar: bool = False
    elevation: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "address": self.address,
            "zip_code": self.zip_code,
            "roof_age": self.roof_age,
            "roof_type": self.roof_type,
            "roof_size_sqft": self.roof_size_sqft,
            "year_built": self.year_built,
            "has_pool": self.has_pool,
            "has_solar": self.has_solar,
            "elevation": self.elevation,
        }


class PropertyDataIntegrator:
    """
    Integration layer for property/roof data.
    Supports multiple data sources and provides unified access.
    """

    def __init__(self, db_path: str = "outputs/property_data.db"):
        """Initialize property data integrator."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create property data tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                zip_code TEXT,
                roof_age INTEGER,
                roof_type TEXT,
                roof_size_sqft INTEGER,
                year_built INTEGER,
                has_pool BOOLEAN,
                has_solar BOOLEAN,
                elevation REAL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS property_risk_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER,
                calculation_date TEXT,
                storm_score REAL,
                cumulative_risk REAL,
                vulnerability_score REAL,
                recommendation TEXT,
                FOREIGN KEY (property_id) REFERENCES properties(id)
            )
        """)

        conn.commit()
        conn.close()

    def load_csv(self, file_path: str, source: str = "csv") -> int:
        """
        Load property data from CSV file.

        Args:
            file_path: Path to CSV file
            source: Source identifier

        Returns:
            Number of properties loaded
        """
        try:
            df = pd.read_csv(file_path)

            # Map CSV columns to property fields
            column_mapping = {
                "address": ["address", "property_address", "street"],
                "zip": ["zip", "zip_code", "postal_code"],
                "roof_age": ["roof_age", "age", "years_old"],
                "roof_type": ["roof_type", "material", "roofing"],
                "roof_size": ["roof_size", "size_sqft", "square_feet"],
                "year_built": ["year_built", "year", "built_year"],
            }

            # Insert properties
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            count = 0
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO properties 
                        (address, zip_code, roof_age, roof_type, roof_size_sqft, 
                         year_built, has_pool, has_solar, elevation, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            str(row.get("address", "")),
                            str(row.get("zip", "")),
                            int(row.get("roof_age", 0))
                            if pd.notna(row.get("roof_age"))
                            else None,
                            str(row.get("roof_type", ""))
                            if pd.notna(row.get("roof_type"))
                            else None,
                            int(row.get("roof_size", 0))
                            if pd.notna(row.get("roof_size"))
                            else None,
                            int(row.get("year_built", 0))
                            if pd.notna(row.get("year_built"))
                            else None,
                            bool(row.get("has_pool", False)),
                            bool(row.get("has_solar", False)),
                            float(row.get("elevation", 0))
                            if pd.notna(row.get("elevation"))
                            else None,
                            source,
                        ),
                    )
                    count += 1
                except Exception:
                    continue

            conn.commit()
            conn.close()

            return count

        except Exception as e:
            print(f"Error loading property data: {e}")
            return 0

    def load_csv_from_df(self, df: pd.DataFrame, source: str = "dataframe") -> int:
        """
        Load property data from an in-memory DataFrame.

        Args:
            df: DataFrame with property data
            source: Source identifier

        Returns:
            Number of properties loaded
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        count = 0
        for _, row in df.iterrows():
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO properties
                    (address, zip_code, roof_age, roof_type, roof_size_sqft,
                     year_built, has_pool, has_solar, elevation, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(row.get("address", "")),
                        str(row.get("zip", "")),
                        int(row.get("roof_age", 0))
                        if pd.notna(row.get("roof_age"))
                        else None,
                        str(row.get("roof_type", ""))
                        if pd.notna(row.get("roof_type"))
                        else None,
                        int(row.get("roof_size", 0))
                        if pd.notna(row.get("roof_size"))
                        else None,
                        int(row.get("year_built", 0))
                        if pd.notna(row.get("year_built"))
                        else None,
                        bool(row.get("has_pool", False)),
                        bool(row.get("has_solar", False)),
                        float(row.get("elevation", 0))
                        if pd.notna(row.get("elevation"))
                        else None,
                        source,
                    ),
                )
                count += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return count

    def get_properties_by_zip(self, zip_code: str) -> List[PropertyData]:
        """Get all properties in a ZIP code."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT address, zip_code, roof_age, roof_type, roof_size_sqft,
                   year_built, has_pool, has_solar, elevation
            FROM properties WHERE zip_code = ?
        """,
            (zip_code,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            PropertyData(
                address=row[0],
                zip_code=row[1],
                roof_age=row[2],
                roof_type=row[3],
                roof_size_sqft=row[4],
                year_built=row[5],
                has_pool=bool(row[6]),
                has_solar=bool(row[7]),
                elevation=row[8],
            )
            for row in rows
        ]

    def calculate_vulnerability_score(
        self, property_data: PropertyData, storm_score: float, cumulative_risk: float
    ) -> Dict:
        """
        Calculate property vulnerability score.

        Combines:
        - Storm score (current event)
        - Cumulative risk (historical)
        - Property factors (age, type, etc.)

        Returns:
            Dict with scores and recommendations
        """
        # Base vulnerability from storm
        base_vulnerability = storm_score * 0.4

        # Property age factor (older = more vulnerable)
        age_factor = 0
        if property_data.roof_age:
            if property_data.roof_age > 20:
                age_factor = 0.3
            elif property_data.roof_age > 15:
                age_factor = 0.2
            elif property_data.roof_age > 10:
                age_factor = 0.1
            elif property_data.roof_age > 5:
                age_factor = 0.05

        # Roof type factor
        type_factor = 0
        if property_data.roof_type:
            roof_type = property_data.roof_type.lower()
            if "flat" in roof_type or "membrane" in roof_type:
                type_factor = 0.15  # More vulnerable to wind
            elif "tile" in roof_type or "slate" in roof_type:
                type_factor = 0.1  # Heavy, less uplift risk
            elif "shingle" in roof_type:
                type_factor = 0.05  # Standard

        # Pool factor (wind exposure around pools)
        pool_factor = 0.05 if property_data.has_pool else 0

        # Solar factor (mounting points)
        solar_factor = 0.1 if property_data.has_solar else 0

        # Cumulative risk weight
        cumulative_weight = cumulative_risk * 0.2

        # Calculate final vulnerability
        vulnerability = (
            base_vulnerability
            + age_factor
            + type_factor
            + pool_factor
            + solar_factor
            + cumulative_weight
        )
        vulnerability = min(vulnerability, 1.0)  # Cap at 1.0

        # Generate recommendation
        if vulnerability > 0.8:
            recommendation = "URGENT: Full inspection required. High vulnerability."
            action = "Schedule inspection within 7 days"
        elif vulnerability > 0.6:
            recommendation = "Priority inspection recommended"
            action = "Schedule within 14 days"
        elif vulnerability > 0.4:
            recommendation = "Standard inspection advised"
            action = "Schedule within 30 days"
        elif vulnerability > 0.2:
            recommendation = "Routine monitoring"
            action = "Annual inspection sufficient"
        else:
            recommendation = "Low vulnerability"
            action = "No immediate action needed"

        return {
            "vulnerability_score": round(vulnerability, 3),
            "base_storm_impact": round(base_vulnerability, 3),
            "age_factor": age_factor,
            "type_factor": type_factor,
            "cumulative_weight": cumulative_weight,
            "recommendation": recommendation,
            "recommended_action": action,
            "priority": "Critical"
            if vulnerability > 0.8
            else "High"
            if vulnerability > 0.6
            else "Medium"
            if vulnerability > 0.4
            else "Low",
        }

    def get_property_stats(self, zip_code: str) -> Dict:
        """Get aggregated property statistics for a ZIP."""
        properties = self.get_properties_by_zip(zip_code)

        if not properties:
            return {"count": 0}

        ages = [p.roof_age for p in properties if p.roof_age]
        types = [p.roof_type for p in properties if p.roof_type]

        return {
            "count": len(properties),
            "avg_roof_age": sum(ages) / len(ages) if ages else None,
            "oldest_roof": max(ages) if ages else None,
            "roof_types": dict((t, types.count(t)) for t in set(types))
            if types
            else {},
            "pools": sum(1 for p in properties if p.has_pool),
            "solar": sum(1 for p in properties if p.has_solar),
        }


# Mock data generator for demo purposes


def generate_mock_properties(
    zip_codes: List[str], count_per_zip: int = 50
) -> pd.DataFrame:
    """
    Generate mock property data for demo.

    Args:
        zip_codes: List of ZIP codes to generate properties for
        count_per_zip: Number of properties per ZIP

    Returns:
        DataFrame with mock property data
    """
    import random
    import numpy as np

    streets = [
        "Oak St",
        "Maple Ave",
        "Cedar Ln",
        "Pine Dr",
        "Elm Way",
        "Birch Blvd",
        "Willow Ct",
        "Ash Dr",
        "Spruce Path",
        "Walnut St",
    ]

    roof_types = ["Shingle", "Tile", "Slate", "Flat/Membrane", "Metal"]

    data = []

    for zip_code in zip_codes:
        for i in range(count_per_zip):
            street = random.choice(streets)
            number = random.randint(100, 9999)

            data.append(
                {
                    "address": f"{number} {street}",
                    "zip": zip_code,
                    "roof_age": random.randint(1, 30),
                    "roof_type": random.choice(roof_types),
                    "roof_size": random.randint(1500, 4000),
                    "year_built": random.randint(1980, 2020),
                    "has_pool": random.random() < 0.1,
                    "has_solar": random.random() < 0.05,
                }
            )

    return pd.DataFrame(data)


# Risk scoring utilities


def estimate_roof_age_from_year_built(year_built: int) -> Optional[int]:
    """Estimate roof age from year built."""
    current_year = datetime.now().year
    if year_built and year_built < current_year:
        return current_year - year_built
    return None


def estimate_roof_type_from_age(age: int) -> str:
    """Estimate roof type from approximate age."""
    if age > 25:
        return "Shingle (likely original)"
    elif age > 15:
        return "Shingle (likely replaced)"
    else:
        return "Shingle (recent)"


# Integration with roof risk index


def merge_property_with_risk(
    properties: List[PropertyData], risk_index_data: Dict[str, float]
) -> pd.DataFrame:
    """
    Merge property data with risk scores.

    Args:
        properties: List of PropertyData objects
        risk_index_data: Dict mapping ZIP codes to cumulative risk scores

    Returns:
        DataFrame with merged property + risk data
    """
    data = []

    for prop in properties:
        row = prop.to_dict()
        row["cumulative_risk"] = risk_index_data.get(prop.zip_code, 0)
        data.append(row)

    return pd.DataFrame(data)


# Sample integration workflow


def run_integration_demo():
    """Demonstrate property data integration."""

    # Generate mock properties for demo ZIPs
    demo_zips = ["75021", "75050", "75462"]
    properties = generate_mock_properties(demo_zips, count_per_zip=30)

    # Save to database
    integrator = PropertyDataIntegrator()
    count = integrator.load_csv_from_df(properties, "demo")
    print(f"Loaded {count} demo properties")

    # Get stats for a ZIP
    stats = integrator.get_property_stats("75021")
    print(f"ZIP 75021: {stats}")

    # Calculate vulnerability for a sample property
    sample = PropertyData(
        address="123 Oak St",
        zip_code="75021",
        roof_age=18,
        roof_type="Shingle",
        roof_size_sqft=2500,
        year_built=2005,
    )

    vulnerability = integrator.calculate_vulnerability_score(
        sample, storm_score=0.85, cumulative_risk=0.65
    )

    print(f"Vulnerability: {vulnerability}")

    return integrator


if __name__ == "__main__":
    run_integration_demo()
