"""
Strategic Lead Scoring Engine
Implements 4-factor probabilistic scoring model from Geospatial Intelligence Framework
Factors: Severe Hail Exposure, Roof Age, Property Value, Claim Status
"""

import math
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from enum import Enum


class ClaimStatus(Enum):
    """Claim status for first-mover advantage detection."""

    NO_CLAIM = "no_claim"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


@dataclass
class LeadScoreFactors:
    """Raw factors for lead scoring."""

    hail_size_inches: float
    roof_age_years: int
    property_value: int
    claim_status: ClaimStatus
    days_since_storm: int = 0
    has_comprehensive_insurance: bool = True


class StrategicLeadScorer:
    """
    High-precision lead scoring based on geospatial intelligence framework.

    Weights from strategic implementation:
    - Severe Hail Exposure (≥1.5 inches): 35 points
    - Roof Age (15+ years): 30 points
    - Property Value (financial capacity): 20 points
    - Claim Status (first-mover advantage): 15 points
    """

    # Hail severity thresholds
    HAIL_SEVERE = 1.5  # inches
    HAIL_MAJOR = 2.0
    HAIL_EXTREME = 2.5

    # Roof age thresholds
    ROOF_END_OF_LIFE = 20
    ROOF_AGING = 15
    ROOF_MATURE = 10

    # Property value thresholds (DFW market adjusted)
    VALUE_LUXURY = 500000
    VALUE_HIGH = 400000
    VALUE_MID = 300000

    def __init__(self, db_path: str = "stormops_cache.db"):
        self.db_path = db_path
        self._init_claims_table()

    def _init_claims_table(self):
        """Initialize claims tracking for first-mover detection."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS property_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id TEXT NOT NULL,
                address TEXT NOT NULL,
                storm_date TEXT,
                claim_status TEXT DEFAULT 'no_claim',
                claim_filed_date TEXT,
                claim_amount INTEGER,
                contractor_assigned TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(property_id, storm_date)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_claims_property 
            ON property_claims(property_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_claims_status 
            ON property_claims(claim_status)
        """)

        conn.commit()
        conn.close()

    def calculate_lead_score(self, factors: LeadScoreFactors) -> Dict:
        """
        Calculate comprehensive lead score using 4-factor model.

        Returns dict with:
        - total_score (0-100)
        - factor_breakdown
        - priority_tier (A/B/C/D)
        - conversion_probability
        - recommended_action
        """
        scores = {}

        # Factor 1: Severe Hail Exposure (35 points max)
        scores["hail"] = self._score_hail_exposure(factors.hail_size_inches)

        # Factor 2: Roof Age Vulnerability (30 points max)
        scores["roof_age"] = self._score_roof_age(factors.roof_age_years)

        # Factor 3: Property Value / Financial Capacity (20 points max)
        scores["property_value"] = self._score_property_value(factors.property_value)

        # Factor 4: Claim Status / First-Mover Advantage (15 points max)
        scores["claim_status"] = self._score_claim_status(
            factors.claim_status, factors.days_since_storm
        )

        # Calculate total score
        total_score = sum(scores.values())

        # Determine priority tier
        priority_tier = self._get_priority_tier(total_score)

        # Calculate conversion probability based on score + factors
        conversion_prob = self._calculate_conversion_probability(factors, total_score)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            total_score, factors, priority_tier
        )

        return {
            "total_score": round(total_score, 1),
            "priority_tier": priority_tier,
            "conversion_probability": round(conversion_prob, 3),
            "factor_breakdown": {k: round(v, 1) for k, v in scores.items()},
            "factors": {
                "hail_size": factors.hail_size_inches,
                "roof_age": factors.roof_age_years,
                "property_value": factors.property_value,
                "claim_status": factors.claim_status.value,
                "days_since_storm": factors.days_since_storm,
            },
            "recommended_action": recommendation["action"],
            "recommended_urgency": recommendation["urgency"],
            "estimated_claim_value": recommendation["estimated_value"],
            "sales_velocity_priority": recommendation["velocity"],
        }

    def _score_hail_exposure(self, hail_size: float) -> float:
        """
        Score hail exposure severity.
        Strategic threshold: ≥1.5 inches indicates severe damage potential.
        """
        if hail_size >= self.HAIL_EXTREME:
            return 35.0  # Extreme damage likely
        elif hail_size >= self.HAIL_MAJOR:
            return 30.0  # Major damage likely
        elif hail_size >= self.HAIL_SEVERE:
            return 25.0  # Severe damage threshold
        elif hail_size >= 1.0:
            return 15.0  # Moderate
        elif hail_size >= 0.75:
            return 8.0  # Light
        else:
            return 0.0

    def _score_roof_age(self, age: int) -> float:
        """
        Score roof age vulnerability.
        Strategic threshold: 15+ years = nearing end of lifecycle.
        """
        if age >= self.ROOF_END_OF_LIFE:
            return 30.0  # End of life - very vulnerable
        elif age >= self.ROOF_AGING:
            return 25.0  # Aging - vulnerable
        elif age >= self.ROOF_MATURE:
            return 18.0  # Mature - moderate vulnerability
        elif age >= 5:
            return 10.0  # Getting older
        else:
            return 5.0  # New roof

    def _score_property_value(self, value: int) -> float:
        """
        Score property value as proxy for financial capacity.
        Higher values indicate better insurance coverage and payment ability.
        """
        if value >= self.VALUE_LUXURY:
            return 20.0  # Luxury - excellent capacity
        elif value >= self.VALUE_HIGH:
            return 17.0  # High value - very good capacity
        elif value >= self.VALUE_MID:
            return 14.0  # Mid-range - good capacity
        elif value >= 200000:
            return 10.0  # Moderate
        else:
            return 6.0  # Lower value - may have financing challenges

    def _score_claim_status(self, status: ClaimStatus, days_since_storm: int) -> float:
        """
        Score claim status for first-mover advantage.

        Strategic value: Properties with no recent claims = unaddressed damage.
        First 30 days after storm = optimal engagement window.
        """
        if status == ClaimStatus.NO_CLAIM:
            # First-mover advantage - highest score
            if days_since_storm <= 7:
                return 15.0  # Fresh opportunity
            elif days_since_storm <= 30:
                return 13.0  # Prime window
            elif days_since_storm <= 60:
                return 10.0  # Still good
            else:
                return 7.0  # Older but unclaimed

        elif status == ClaimStatus.PENDING:
            return 5.0  # Opportunity to be backup contractor

        elif status == ClaimStatus.DENIED:
            return 12.0  # May need help with appeal/replacement

        elif status == ClaimStatus.APPROVED:
            return 3.0  # Contractor likely already assigned

        elif status == ClaimStatus.COMPLETED:
            return 0.0  # Already repaired

        else:  # UNKNOWN
            return 8.0  # Assume no claim, investigate

    def _get_priority_tier(self, score: float) -> str:
        """
        Convert score to priority tier for sales velocity.
        A-tier = immediate outreach (5.0%+ conversion expected)
        """
        if score >= 85:
            return "A"  # Immediate (24-48 hours)
        elif score >= 70:
            return "B"  # Priority (3-5 days)
        elif score >= 55:
            return "C"  # Standard (1-2 weeks)
        else:
            return "D"  # Nurture (long-term)

    def _calculate_conversion_probability(
        self, factors: LeadScoreFactors, score: float
    ) -> float:
        """
        Estimate conversion probability based on historical data model.
        A-tier leads typically convert at 5.0%+ vs 0.3% traditional.
        """
        base_prob = score / 100.0 * 0.06  # Score to probability mapping

        # Adjustments for specific conditions
        if (
            factors.claim_status == ClaimStatus.NO_CLAIM
            and factors.days_since_storm <= 14
        ):
            base_prob *= 1.3  # 30% boost for fresh unclaimed

        if factors.roof_age_years >= 15 and factors.hail_size_inches >= 1.5:
            base_prob *= 1.2  # 20% boost for perfect storm conditions

        return min(base_prob, 0.15)  # Cap at 15%

    def _generate_recommendation(
        self, score: float, factors: LeadScoreFactors, tier: str
    ) -> Dict:
        """Generate actionable sales recommendation."""

        # Calculate estimated claim value
        roof_size_sqft = 2500  # Average
        replacement_cost_per_sqft = 3.50  # DFW average
        estimated_value = int(roof_size_sqft * replacement_cost_per_sqft)

        if tier == "A":
            return {
                "action": "IMMEDIATE_OUTREACH",
                "urgency": "Within 24 hours",
                "estimated_value": estimated_value,
                "velocity": "Critical - Deploy immediately",
            }
        elif tier == "B":
            return {
                "action": "PRIORITY_OUTREACH",
                "urgency": "Within 72 hours",
                "estimated_value": estimated_value,
                "velocity": "High - Add to immediate queue",
            }
        elif tier == "C":
            return {
                "action": "STANDARD_OUTREACH",
                "urgency": "Within 2 weeks",
                "estimated_value": estimated_value,
                "velocity": "Medium - Include in campaign",
            }
        else:
            return {
                "action": "NURTURE_CAMPAIGN",
                "urgency": "Ongoing",
                "estimated_value": estimated_value * 0.7,  # Lower confidence
                "velocity": "Low - Long-term nurture",
            }

    def batch_score_leads(self, leads_data: List[Dict]) -> pd.DataFrame:
        """
        Score multiple leads efficiently.

        Input: List of dicts with keys:
        - property_id, address, hail_size, roof_age, property_value,
        - claim_status, days_since_storm

        Output: DataFrame with scored leads sorted by priority
        """
        results = []

        for lead in leads_data:
            try:
                factors = LeadScoreFactors(
                    hail_size_inches=lead.get("hail_size", 0),
                    roof_age_years=lead.get("roof_age", 0),
                    property_value=lead.get("property_value", 0),
                    claim_status=ClaimStatus(lead.get("claim_status", "unknown")),
                    days_since_storm=lead.get("days_since_storm", 0),
                    has_comprehensive_insurance=lead.get("has_insurance", True),
                )

                score_result = self.calculate_lead_score(factors)

                results.append(
                    {
                        "property_id": lead.get("property_id"),
                        "address": lead.get("address"),
                        "zip_code": lead.get("zip_code"),
                        "lat": lead.get("lat"),
                        "lon": lead.get("lon"),
                        "lead_score": score_result["total_score"],
                        "priority_tier": score_result["priority_tier"],
                        "conversion_probability": score_result[
                            "conversion_probability"
                        ],
                        "hail_score": score_result["factor_breakdown"]["hail"],
                        "roof_age_score": score_result["factor_breakdown"]["roof_age"],
                        "value_score": score_result["factor_breakdown"][
                            "property_value"
                        ],
                        "claim_score": score_result["factor_breakdown"]["claim_status"],
                        "recommended_action": score_result["recommended_action"],
                        "urgency": score_result["recommended_urgency"],
                        "estimated_claim_value": score_result["estimated_claim_value"],
                        "hail_size": lead.get("hail_size"),
                        "storm_date": lead.get("storm_date"),
                    }
                )

            except Exception as e:
                print(f"Error scoring lead {lead.get('property_id')}: {e}")
                continue

        df = pd.DataFrame(results)

        # Sort by score descending (A-tier first)
        df = df.sort_values("lead_score", ascending=False)

        return df

    def update_claim_status(
        self,
        property_id: str,
        storm_date: str,
        status: ClaimStatus,
        claim_amount: int = None,
        contractor: str = None,
    ):
        """Update claim status for first-mover tracking."""
        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            INSERT OR REPLACE INTO property_claims 
            (property_id, storm_date, claim_status, claim_filed_date, 
             claim_amount, contractor_assigned, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (
                property_id,
                storm_date,
                status.value,
                datetime.now().isoformat(),
                claim_amount,
                contractor,
            ),
        )

        conn.commit()
        conn.close()

    def get_first_mover_opportunities(self, days_after_storm: int = 30) -> pd.DataFrame:
        """
        Get properties with no claims filed within X days of storm.
        High-value first-mover opportunities.
        """
        conn = sqlite3.connect(self.db_path)

        query = """
        SELECT * FROM property_claims 
        WHERE claim_status = 'no_claim'
          AND julianday('now') - julianday(storm_date) <= ?
        ORDER BY storm_date DESC
        """

        df = pd.read_sql_query(query, conn, params=(days_after_storm,))
        conn.close()

        return df

    def get_tier_summary(self, scored_leads: pd.DataFrame) -> Dict:
        """Generate summary statistics by tier for ROI tracking."""
        summary = {}

        for tier in ["A", "B", "C", "D"]:
            tier_leads = scored_leads[scored_leads["priority_tier"] == tier]

            summary[tier] = {
                "count": len(tier_leads),
                "avg_score": tier_leads["lead_score"].mean()
                if len(tier_leads) > 0
                else 0,
                "avg_conversion_prob": tier_leads["conversion_probability"].mean()
                if len(tier_leads) > 0
                else 0,
                "total_estimated_value": tier_leads["estimated_claim_value"].sum()
                if len(tier_leads) > 0
                else 0,
                "pct_of_total": len(tier_leads) / len(scored_leads) * 100
                if len(scored_leads) > 0
                else 0,
            }

        return summary


# Example usage and testing
if __name__ == "__main__":
    scorer = StrategicLeadScorer()

    # Test cases demonstrating 4-factor model
    test_cases = [
        {
            "property_id": "PROP001",
            "address": "123 Oak St",
            "zip_code": "75034",
            "hail_size": 2.5,  # Extreme
            "roof_age": 18,  # End of life
            "property_value": 550000,  # Luxury
            "claim_status": "no_claim",  # First-mover!
            "days_since_storm": 5,
        },
        {
            "property_id": "PROP002",
            "address": "456 Maple Ave",
            "zip_code": "75024",
            "hail_size": 1.5,  # Severe threshold
            "roof_age": 12,  # Mature
            "property_value": 350000,  # Mid
            "claim_status": "no_claim",
            "days_since_storm": 21,
        },
        {
            "property_id": "PROP003",
            "address": "789 Pine Dr",
            "zip_code": "76092",
            "hail_size": 1.0,  # Moderate
            "roof_age": 8,  # Getting older
            "property_value": 280000,  # Lower
            "claim_status": "pending",  # Already in process
            "days_since_storm": 45,
        },
    ]

    print("🎯 Strategic Lead Scoring Engine - 4-Factor Model")
    print("=" * 70)

    scored_df = scorer.batch_score_leads(test_cases)

    print("\n📊 Scored Leads (sorted by priority):")
    print("-" * 70)

    for _, row in scored_df.iterrows():
        print(f"\n🏠 {row['address']} (ZIP: {row['zip_code']})")
        print(
            f"   Priority: {row['priority_tier']}-Tier | Score: {row['lead_score']}/100"
        )
        print(f"   Conversion Probability: {row['conversion_probability']:.1%}")
        print(f"   Action: {row['recommended_action']} | {row['urgency']}")
        print(f"   Est. Value: ${row['estimated_claim_value']:,}")

    # Tier summary
    print("\n" + "=" * 70)
    print("📈 Tier Summary:")
    summary = scorer.get_tier_summary(scored_df)

    for tier, stats in summary.items():
        if stats["count"] > 0:
            print(
                f"   {tier}-Tier: {stats['count']} leads | "
                f"Avg Score: {stats['avg_score']:.1f} | "
                f"Total Value: ${stats['total_estimated_value']:,.0f}"
            )
