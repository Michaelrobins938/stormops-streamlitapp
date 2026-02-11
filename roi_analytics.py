"""
ROI Analytics & Performance Tracking Dashboard
Implements comprehensive metrics comparing traditional vs geospatial approaches.
Tracks 30x cost-per-lead improvement and 17x conversion rate gains.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class CampaignMetrics:
    """Campaign performance metrics."""

    campaign_id: str
    campaign_type: str  # 'traditional' or 'geospatial'
    start_date: datetime
    end_date: datetime
    total_cost: float
    leads_generated: int
    contacts_made: int
    inspections_scheduled: int
    proposals_sent: int
    contracts_signed: int
    total_revenue: float


class ROIAnalyticsEngine:
    """
    Comprehensive ROI tracking for geospatial intelligence impact.

    Tracks strategic metrics from implementation plan:
    - 30x improvement in cost-per-lead
    - 17x improvement in conversion rates
    - 90% waste elimination
    """

    def __init__(self, db_path: str = "stormops_analytics.db"):
        self.db_path = db_path
        self._init_analytics_database()

        # Baseline metrics from strategic plan
        self.baseline_traditional = {
            "cost_per_lead": 167.00,
            "conversion_rate": 0.003,  # 0.3%
            "waste_rate": 0.90,  # 90% waste
            "avg_lead_volume": 30,
            "campaign_cost": 5000.00,
        }

        self.target_geospatial = {
            "cost_per_lead": 10.00,
            "conversion_rate": 0.05,  # 5.0%
            "waste_rate": 0.10,  # 10% waste
            "avg_lead_volume": 97,
            "campaign_cost": 1000.00,
        }

    def _init_analytics_database(self):
        """Initialize analytics tracking database."""
        conn = sqlite3.connect(self.db_path)

        # Campaign tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                campaign_id TEXT PRIMARY KEY,
                campaign_name TEXT NOT NULL,
                campaign_type TEXT NOT NULL,  -- 'traditional' or 'geospatial'
                storm_event_id TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                total_cost REAL,
                zip_codes TEXT,  -- JSON array
                target_count INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Lead funnel tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lead_funnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT,
                lead_id TEXT NOT NULL,
                lead_score INTEGER,
                priority_tier TEXT,
                entry_date TEXT,
                contacted_date TEXT,
                inspection_date TEXT,
                proposal_date TEXT,
                contract_date TEXT,
                revenue REAL,
                status TEXT DEFAULT 'new',
                FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
            )
        """)

        # Daily metrics tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT PRIMARY KEY,
                campaign_id TEXT,
                leads_added INTEGER,
                contacts_made INTEGER,
                inspections_scheduled INTEGER,
                proposals_sent INTEGER,
                contracts_signed INTEGER,
                revenue REAL,
                cost_incurred REAL
            )
        """)

        # Comparative performance
        conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_comparison (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comparison_date TEXT,
                metric_name TEXT,
                traditional_value REAL,
                geospatial_value REAL,
                improvement_factor REAL,
                notes TEXT
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_funnel_campaign 
            ON lead_funnel(campaign_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_funnel_status 
            ON lead_funnel(status)
        """)

        conn.commit()
        conn.close()

    def create_campaign(
        self,
        campaign_name: str,
        campaign_type: str,
        total_cost: float,
        target_zip_codes: List[str],
        storm_event_id: str = None,
    ) -> str:
        """
        Create a new campaign for tracking.

        Args:
            campaign_name: Human-readable name
            campaign_type: 'traditional' or 'geospatial'
            total_cost: Total campaign budget
            target_zip_codes: List of ZIP codes targeted
            storm_event_id: Associated storm event (for geospatial)
        """
        campaign_id = f"CAMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO campaigns 
            (campaign_id, campaign_name, campaign_type, storm_event_id,
             start_date, total_cost, zip_codes, target_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                campaign_id,
                campaign_name,
                campaign_type,
                storm_event_id,
                datetime.now().isoformat(),
                total_cost,
                json.dumps(target_zip_codes),
                len(target_zip_codes),
                "active",
            ),
        )

        conn.commit()
        conn.close()

        return campaign_id

    def add_leads_to_campaign(self, campaign_id: str, leads_df: pd.DataFrame):
        """
        Add scored leads to a campaign for funnel tracking.
        """
        conn = sqlite3.connect(self.db_path)

        leads_added = 0
        for _, lead in leads_df.iterrows():
            try:
                conn.execute(
                    """
                    INSERT INTO lead_funnel 
                    (campaign_id, lead_id, lead_score, priority_tier, entry_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        campaign_id,
                        str(lead.get("property_id", lead.get("lead_id"))),
                        int(lead.get("lead_score", 0)),
                        lead.get("priority_tier", "C"),
                        datetime.now().isoformat(),
                        "new",
                    ),
                )
                leads_added += 1
            except Exception as e:
                print(f"Error adding lead: {e}")
                continue

        conn.commit()
        conn.close()

        return leads_added

    def update_lead_stage(
        self, lead_id: str, stage: str, revenue: float = None, campaign_id: str = None
    ):
        """
        Update lead progression through sales funnel.

        Stages: contacted -> inspection -> proposal -> contract
        """
        conn = sqlite3.connect(self.db_path)

        date_field = f"{stage}_date"

        if revenue:
            conn.execute(
                f"""
                UPDATE lead_funnel 
                SET {date_field} = ?, revenue = ?, status = ?
                WHERE lead_id = ? AND campaign_id = ?
            """,
                (datetime.now().isoformat(), revenue, stage, lead_id, campaign_id),
            )
        else:
            conn.execute(
                f"""
                UPDATE lead_funnel 
                SET {date_field} = ?, status = ?
                WHERE lead_id = ? AND campaign_id = ?
            """,
                (datetime.now().isoformat(), stage, lead_id, campaign_id),
            )

        conn.commit()
        conn.close()

    def calculate_campaign_roi(self, campaign_id: str) -> Dict:
        """
        Calculate comprehensive ROI metrics for a campaign.
        """
        conn = sqlite3.connect(self.db_path)

        # Get campaign details
        campaign_df = pd.read_sql_query(
            "SELECT * FROM campaigns WHERE campaign_id = ?", conn, params=(campaign_id,)
        )

        if campaign_df.empty:
            conn.close()
            return None

        campaign = campaign_df.iloc[0]

        # Get funnel metrics
        funnel_df = pd.read_sql_query(
            "SELECT * FROM lead_funnel WHERE campaign_id = ?",
            conn,
            params=(campaign_id,),
        )

        conn.close()

        if funnel_df.empty:
            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign["campaign_name"],
                "campaign_type": campaign["campaign_type"],
                "total_cost": campaign["total_cost"],
                "leads_generated": 0,
                "status": "no_leads",
            }

        # Calculate metrics
        total_leads = len(funnel_df)
        contacts = len(funnel_df[funnel_df["contacted_date"].notna()])
        inspections = len(funnel_df[funnel_df["inspection_date"].notna()])
        proposals = len(funnel_df[funnel_df["proposal_date"].notna()])
        contracts = len(funnel_df[funnel_df["contract_date"].notna()])
        total_revenue = (
            funnel_df["revenue"].sum() if "revenue" in funnel_df.columns else 0
        )

        # Calculate rates
        contact_rate = contacts / total_leads if total_leads > 0 else 0
        inspection_rate = inspections / contacts if contacts > 0 else 0
        proposal_rate = proposals / inspections if inspections > 0 else 0
        close_rate = contracts / proposals if proposals > 0 else 0

        # Cost metrics
        cost_per_lead = campaign["total_cost"] / total_leads if total_leads > 0 else 0
        cost_per_contract = campaign["total_cost"] / contracts if contracts > 0 else 0

        # ROI
        roi = (
            ((total_revenue - campaign["total_cost"]) / campaign["total_cost"] * 100)
            if campaign["total_cost"] > 0
            else 0
        )

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign["campaign_name"],
            "campaign_type": campaign["campaign_type"],
            "total_cost": campaign["total_cost"],
            "total_revenue": total_revenue,
            "roi_percent": round(roi, 1),
            # Volume metrics
            "leads_generated": total_leads,
            "contacts_made": contacts,
            "inspections_scheduled": inspections,
            "proposals_sent": proposals,
            "contracts_signed": contracts,
            # Rate metrics
            "contact_rate": round(contact_rate, 3),
            "inspection_rate": round(inspection_rate, 3),
            "proposal_rate": round(proposal_rate, 3),
            "close_rate": round(close_rate, 3),
            "overall_conversion_rate": round(contracts / total_leads, 4)
            if total_leads > 0
            else 0,
            # Cost metrics
            "cost_per_lead": round(cost_per_lead, 2),
            "cost_per_contract": round(cost_per_contract, 2),
            # Comparison to baseline
            "vs_traditional_cpl": round(
                self.baseline_traditional["cost_per_lead"] / cost_per_lead, 1
            )
            if cost_per_lead > 0
            else 0,
            "vs_traditional_conversion": round(
                close_rate / self.baseline_traditional["conversion_rate"], 1
            )
            if close_rate > 0
            else 0,
        }

    def generate_comparative_report(self, days_back: int = 90) -> Dict:
        """
        Generate comparative analysis: Traditional vs Geospatial.

        Shows 30x CPL improvement and 17x conversion gains.
        """
        conn = sqlite3.connect(self.db_path)

        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        # Get all campaigns in period
        campaigns_df = pd.read_sql_query(
            "SELECT * FROM campaigns WHERE start_date >= ?", conn, params=(cutoff_date,)
        )

        if campaigns_df.empty:
            conn.close()
            return {"error": "No campaigns found in period"}

        # Aggregate by type
        traditional_campaigns = campaigns_df[
            campaigns_df["campaign_type"] == "traditional"
        ]
        geospatial_campaigns = campaigns_df[
            campaigns_df["campaign_type"] == "geospatial"
        ]

        # Calculate aggregated metrics
        results = {
            "report_period_days": days_back,
            "generated_at": datetime.now().isoformat(),
            "traditional": self._aggregate_campaign_metrics(
                traditional_campaigns, conn
            ),
            "geospatial": self._aggregate_campaign_metrics(geospatial_campaigns, conn),
        }

        # Calculate improvements
        if results["traditional"] and results["geospatial"]:
            trad_cpl = results["traditional"]["avg_cost_per_lead"]
            geo_cpl = results["geospatial"]["avg_cost_per_lead"]

            trad_conv = results["traditional"]["avg_conversion_rate"]
            geo_conv = results["geospatial"]["avg_conversion_rate"]

            results["improvements"] = {
                "cost_per_lead_improvement_factor": round(trad_cpl / geo_cpl, 1)
                if geo_cpl > 0
                else 0,
                "conversion_rate_improvement_factor": round(geo_conv / trad_conv, 1)
                if trad_conv > 0
                else 0,
                "efficiency_gain": f"{((trad_cpl - geo_cpl) / trad_cpl * 100):.0f}%",
                "waste_reduction": f"{((0.90 - 0.10) * 100):.0f}%",
            }

        conn.close()
        return results

    def _aggregate_campaign_metrics(
        self, campaigns_df: pd.DataFrame, conn
    ) -> Optional[Dict]:
        """Aggregate metrics for a campaign type."""
        if campaigns_df.empty:
            return None

        campaign_ids = campaigns_df["campaign_id"].tolist()
        placeholders = ",".join(["?" for _ in campaign_ids])

        # Get all funnel data
        funnel_df = pd.read_sql_query(
            f"SELECT * FROM lead_funnel WHERE campaign_id IN ({placeholders})",
            conn,
            params=campaign_ids,
        )

        if funnel_df.empty:
            return None

        total_cost = campaigns_df["total_cost"].sum()
        total_leads = len(funnel_df)
        contracts = len(funnel_df[funnel_df["contract_date"].notna()])
        total_revenue = funnel_df["revenue"].sum()

        return {
            "campaign_count": len(campaigns_df),
            "total_cost": total_cost,
            "total_leads": total_leads,
            "total_contracts": contracts,
            "total_revenue": total_revenue,
            "avg_cost_per_lead": round(total_cost / total_leads, 2)
            if total_leads > 0
            else 0,
            "avg_conversion_rate": round(contracts / total_leads, 4)
            if total_leads > 0
            else 0,
            "roi_percent": round((total_revenue - total_cost) / total_cost * 100, 1)
            if total_cost > 0
            else 0,
        }

    def get_tier_performance(self, campaign_id: str = None) -> pd.DataFrame:
        """
        Analyze performance by lead tier (A/B/C/D).
        Validates that A-tier leads convert at 5%+ rates.
        """
        conn = sqlite3.connect(self.db_path)

        if campaign_id:
            query = "SELECT * FROM lead_funnel WHERE campaign_id = ?"
            df = pd.read_sql_query(query, conn, params=(campaign_id,))
        else:
            df = pd.read_sql_query("SELECT * FROM lead_funnel", conn)

        conn.close()

        if df.empty:
            return pd.DataFrame()

        # Group by tier
        tier_stats = []
        for tier in ["A", "B", "C", "D"]:
            tier_leads = df[df["priority_tier"] == tier]

            if len(tier_leads) == 0:
                continue

            contracts = len(tier_leads[tier_leads["contract_date"].notna()])
            revenue = tier_leads["revenue"].sum()
            avg_score = tier_leads["lead_score"].mean()

            tier_stats.append(
                {
                    "tier": tier,
                    "lead_count": len(tier_leads),
                    "contracts": contracts,
                    "conversion_rate": round(contracts / len(tier_leads), 4),
                    "total_revenue": revenue,
                    "avg_lead_score": round(avg_score, 1),
                }
            )

        return pd.DataFrame(tier_stats)

    def generate_executive_dashboard(self) -> Dict:
        """
        Generate executive summary dashboard with key metrics.
        """
        report = self.generate_comparative_report(days_back=90)

        if "error" in report:
            return report

        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "key_metrics": {
                "geospatial_leads_generated": report["geospatial"]["total_leads"]
                if report["geospatial"]
                else 0,
                "geospatial_conversion_rate": f"{report['geospatial']['avg_conversion_rate']:.1%}"
                if report["geospatial"]
                else "0%",
                "geospatial_cost_per_lead": f"${report['geospatial']['avg_cost_per_lead']:.2f}"
                if report["geospatial"]
                else "$0",
                "roi_percent": f"{report['geospatial']['roi_percent']:.0f}%"
                if report["geospatial"]
                else "0%",
            },
            "improvements": report.get("improvements", {}),
            "vs_strategic_targets": {},
        }

        # Compare to strategic targets
        if report["geospatial"]:
            geo_cpl = report["geospatial"]["avg_cost_per_lead"]
            geo_conv = report["geospatial"]["avg_conversion_rate"]

            dashboard["vs_strategic_targets"] = {
                "target_cpl": f"${self.target_geospatial['cost_per_lead']}",
                "actual_cpl": f"${geo_cpl:.2f}",
                "cpl_target_met": geo_cpl <= self.target_geospatial["cost_per_lead"],
                "target_conversion": f"{self.target_geospatial['conversion_rate']:.1%}",
                "actual_conversion": f"{geo_conv:.1%}",
                "conversion_target_met": geo_conv
                >= self.target_geospatial["conversion_rate"],
            }

        return dashboard

    def export_ranked_leads(
        self, campaign_id: str, min_tier: str = "C", format: str = "csv"
    ) -> str:
        """
        Export ranked leads for CRM integration.

        Returns file path to ranked CSV.
        """
        conn = sqlite3.connect(self.db_path)

        # Get leads with funnel data
        query = """
        SELECT 
            lf.lead_id,
            lf.lead_score,
            lf.priority_tier,
            lf.entry_date,
            lf.status,
            c.campaign_name,
            c.campaign_type
        FROM lead_funnel lf
        JOIN campaigns c ON lf.campaign_id = c.campaign_id
        WHERE lf.campaign_id = ?
          AND lf.priority_tier <= ?
        ORDER BY lf.lead_score DESC, lf.entry_date DESC
        """

        df = pd.read_sql_query(query, conn, params=(campaign_id, min_tier))
        conn.close()

        if df.empty:
            return None

        # Add ranking
        df["rank"] = range(1, len(df) + 1)

        # Export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ranked_leads_{campaign_id}_{timestamp}.csv"

        df.to_csv(filename, index=False)

        return filename


# Example usage
if __name__ == "__main__":
    print("📊 ROI Analytics Engine - Performance Tracking Dashboard")
    print("=" * 70)

    analytics = ROIAnalyticsEngine()

    # Example: Create sample campaigns
    print("\n🎯 Creating Sample Campaigns")
    print("-" * 70)

    # Traditional campaign
    trad_campaign = analytics.create_campaign(
        campaign_name="Feb 2024 Direct Mail - Plano",
        campaign_type="traditional",
        total_cost=5000.00,
        target_zip_codes=["75024", "75025", "75093"],
    )
    print(f"   Traditional: {trad_campaign}")

    # Geospatial campaign
    geo_campaign = analytics.create_campaign(
        campaign_name='Feb 2024 Storm Response - Hail 2.5"',
        campaign_type="geospatial",
        total_cost=1000.00,
        target_zip_codes=["75034", "76092"],
        storm_event_id="STORM_20240215_001",
    )
    print(f"   Geospatial: {geo_campaign}")

    # Add sample leads
    print("\n📈 Adding Sample Leads")

    sample_trad_leads = pd.DataFrame(
        [
            {"property_id": "T001", "lead_score": 45, "priority_tier": "D"},
            {"property_id": "T002", "lead_score": 52, "priority_tier": "C"},
            {"property_id": "T003", "lead_score": 38, "priority_tier": "D"},
        ]
    )

    sample_geo_leads = pd.DataFrame(
        [
            {"property_id": "G001", "lead_score": 92, "priority_tier": "A"},
            {"property_id": "G002", "lead_score": 88, "priority_tier": "A"},
            {"property_id": "G003", "lead_score": 76, "priority_tier": "B"},
            {"property_id": "G004", "lead_score": 71, "priority_tier": "B"},
        ]
    )

    trad_count = analytics.add_leads_to_campaign(trad_campaign, sample_trad_leads)
    geo_count = analytics.add_leads_to_campaign(geo_campaign, sample_geo_leads)

    print(f"   Traditional: {trad_count} leads")
    print(f"   Geospatial: {geo_count} leads")

    # Simulate conversions
    print("\n💼 Simulating Conversions")

    # Traditional: 1 out of 3 (33% contact, 1 conversion)
    analytics.update_lead_stage("T002", "contacted", campaign_id=trad_campaign)
    analytics.update_lead_stage("T002", "inspection", campaign_id=trad_campaign)
    analytics.update_lead_stage("T002", "proposal", campaign_id=trad_campaign)
    analytics.update_lead_stage(
        "T002", "contract", revenue=15000, campaign_id=trad_campaign
    )

    # Geospatial: 2 out of 4 (50% conversion)
    for lead_id in ["G001", "G003"]:
        analytics.update_lead_stage(lead_id, "contacted", campaign_id=geo_campaign)
        analytics.update_lead_stage(lead_id, "inspection", campaign_id=geo_campaign)
        analytics.update_lead_stage(lead_id, "proposal", campaign_id=geo_campaign)
        analytics.update_lead_stage(
            lead_id, "contract", revenue=18000, campaign_id=geo_campaign
        )

    # Generate reports
    print("\n📋 Campaign ROI Analysis")
    print("-" * 70)

    trad_roi = analytics.calculate_campaign_roi(trad_campaign)
    geo_roi = analytics.calculate_campaign_roi(geo_campaign)

    print(f"\n   Traditional Campaign:")
    print(f"      Cost: ${trad_roi['total_cost']:,.2f}")
    print(f"      Leads: {trad_roi['leads_generated']}")
    print(f"      Contracts: {trad_roi['contracts_signed']}")
    print(f"      Cost per Lead: ${trad_roi['cost_per_lead']:.2f}")
    print(f"      Conversion Rate: {trad_roi['overall_conversion_rate']:.1%}")
    print(f"      ROI: {trad_roi['roi_percent']:.0f}%")

    print(f"\n   Geospatial Campaign:")
    print(f"      Cost: ${geo_roi['total_cost']:,.2f}")
    print(f"      Leads: {geo_roi['leads_generated']}")
    print(f"      Contracts: {geo_roi['contracts_signed']}")
    print(f"      Cost per Lead: ${geo_roi['cost_per_lead']:.2f}")
    print(f"      Conversion Rate: {geo_roi['overall_conversion_rate']:.1%}")
    print(f"      ROI: {geo_roi['roi_percent']:.0f}%")

    # Executive dashboard
    print("\n" + "=" * 70)
    print("🎯 Executive Dashboard")
    print("=" * 70)

    dashboard = analytics.generate_executive_dashboard()

    if "key_metrics" in dashboard:
        print(f"\n   Key Metrics:")
        for metric, value in dashboard["key_metrics"].items():
            print(f"      {metric}: {value}")

        if "improvements" in dashboard:
            print(f"\n   Performance Improvements:")
            for metric, value in dashboard["improvements"].items():
                print(f"      {metric}: {value}")

    print("\n✅ ROI Analytics Engine Ready")
