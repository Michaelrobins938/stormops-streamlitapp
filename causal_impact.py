"""
Causal Impact Analysis - Storm and Playbook Attribution

Estimates incremental inspections and jobs caused by storms vs. baseline,
and lift from different outreach playbooks using difference-in-differences
and uplift-style comparison methods.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
import pandas as pd


class CausalImpactAnalyzer:
    """
    Analyzes causal impact of storms and outreach playbooks.

    Methods:
    - Difference-in-differences: treated vs. control ZIPs before/after storm
    - Uplift analysis: comparing playbook performance across segments
    - Attribution modeling: assigning outcomes to specific events
    """

    def __init__(self, entities_db: str = "outputs/roof_entities.db"):
        """Initialize with entity graph database."""
        self.entities_db = entities_db

    def _get_entities_in_period(
        self, zip_codes: List[str], start_date: str, end_date: str
    ) -> List[Dict]:
        """Get all entities in ZIP codes modified during period."""
        conn = sqlite3.connect(self.entities_db)
        cursor = conn.cursor()

        placeholders = ",".join("?" * len(zip_codes))
        cursor.execute(
            f"""
            SELECT * FROM roof_entities 
            WHERE zip_code IN ({placeholders})
            AND updated_at >= ? AND updated_at <= ?
            """,
            (*zip_codes, start_date, end_date),
        )

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

    def _get_outcomes_in_period(
        self, start_date: str, end_date: str, zip_codes: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get all outcome events in a time period."""
        conn = sqlite3.connect(self.entities_db)
        cursor = conn.cursor()

        if zip_codes:
            placeholders = ",".join("?" * len(zip_codes))
            cursor.execute(
                f"""
                SELECT o.*, e.zip_code, e.canonical_address
                FROM outcome_events o
                JOIN roof_entities e ON o.entity_id = e.entity_id
                WHERE o.timestamp >= ? AND o.timestamp <= ?
                AND e.zip_code IN ({placeholders})
                ORDER BY o.timestamp
                """,
                (start_date, end_date, *zip_codes),
            )
        else:
            cursor.execute(
                """
                SELECT o.*, e.zip_code, e.canonical_address
                FROM outcome_events o
                JOIN roof_entities e ON o.entity_id = e.entity_id
                WHERE o.timestamp >= ? AND o.timestamp <= ?
                ORDER BY o.timestamp
                """,
                (start_date, end_date),
            )

        columns = [desc[0] for desc in cursor.description]
        outcomes = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return outcomes

    def _get_outreach_in_period(
        self, start_date: str, end_date: str, zip_codes: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get all outreach interactions in a time period."""
        conn = sqlite3.connect(self.entities_db)
        cursor = conn.cursor()

        if zip_codes:
            placeholders = ",".join("?" * len(zip_codes))
            cursor.execute(
                f"""
                SELECT i.*, e.zip_code, e.canonical_address
                FROM outreach_interactions i
                JOIN roof_entities e ON i.entity_id = e.entity_id
                WHERE i.timestamp >= ? AND i.timestamp <= ?
                AND e.zip_code IN ({placeholders})
                ORDER BY i.timestamp
                """,
                (start_date, end_date, *zip_codes),
            )
        else:
            cursor.execute(
                """
                SELECT i.*, e.zip_code, e.canonical_address
                FROM outreach_interactions i
                JOIN roof_entities e ON i.entity_id = e.entity_id
                WHERE i.timestamp >= ? AND i.timestamp <= ?
                ORDER BY i.timestamp
                """,
                (start_date, end_date),
            )

        columns = [desc[0] for desc in cursor.description]
        interactions = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return interactions

    def estimate_storm_incremental_impact(
        self,
        storm_event_id: str,
        treated_zip_codes: List[str],
        control_zip_codes: List[str],
        pre_storm_days: int = 30,
        post_storm_days: int = 60,
        storm_date: str = None,
    ) -> Dict:
        """
        Estimate incremental inspections and jobs from a storm event.

        Uses difference-in-differences:
        - Treated: ZIPs hit by the storm
        - Control: Similar ZIPs not hit or minimally impacted

        Args:
            storm_event_id: Identifier for the storm event
            treated_zip_codes: ZIPs significantly impacted
            control_zip_codes: Baseline comparison ZIPs
            pre_storm_days: Days before storm to use as baseline
            post_storm_days: Days after storm to measure impact
            storm_date: Date of storm occurrence

        Returns:
            Dict with incremental metrics and confidence intervals
        """
        if storm_date is None:
            storm_date = datetime.now().strftime("%Y-%m-%d")

        storm_dt = datetime.strptime(storm_date, "%Y-%m-%d")
        pre_start = (storm_dt - timedelta(days=pre_storm_days)).strftime("%Y-%m-%d")
        pre_end = (storm_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        post_start = storm_date
        post_end = (storm_dt + timedelta(days=post_storm_days)).strftime("%Y-%m-%d")

        pre_outcomes_treated = self._get_outcomes_in_period(
            pre_start, pre_end, treated_zip_codes
        )
        post_outcomes_treated = self._get_outcomes_in_period(
            post_start, post_end, treated_zip_codes
        )
        pre_outcomes_control = self._get_outcomes_in_period(
            pre_start, pre_end, control_zip_codes
        )
        post_outcomes_control = self._get_outcomes_in_period(
            post_start, post_end, control_zip_codes
        )

        treated_pre = self._aggregate_outcomes(pre_outcomes_treated)
        treated_post = self._aggregate_outcomes(post_outcomes_treated)
        control_pre = self._aggregate_outcomes(pre_outcomes_control)
        control_post = self._aggregate_outcomes(post_outcomes_control)

        treated_diff = {
            k: treated_post[k] - treated_pre[k]
            for k in ["inspections", "jobs", "job_value"]
        }
        control_diff = {
            k: control_post[k] - control_pre[k]
            for k in ["inspections", "jobs", "job_value"]
        }

        incremental = {
            k: treated_diff[k] - control_diff[k]
            for k in ["inspections", "jobs", "job_value"]
        }

        for k, v in incremental.items():
            if v < 0 and k != "job_value":
                incremental[k] = 0

        incremental["conversion_rate_lift"] = (
            treated_post.get("conversion_rate", 0)
            - treated_pre.get("conversion_rate", 0)
        ) - (
            control_post.get("conversion_rate", 0)
            - control_pre.get("conversion_rate", 0)
        )

        n_treated = len(treated_zip_codes)
        n_control = len(control_zip_codes)

        return {
            "storm_event_id": storm_event_id,
            "storm_date": storm_date,
            "treated_zips": n_treated,
            "control_zips": n_control,
            "pre_storm_period": {"start": pre_start, "end": pre_end},
            "post_storm_period": {"start": post_start, "end": post_end},
            "treated_baseline": treated_pre,
            "treated_post": treated_post,
            "control_baseline": control_pre,
            "control_post": control_post,
            "incremental_impact": incremental,
            "summary": (
                f"This storm generated an estimated +{incremental['inspections']:.0f} "
                f"inspections and +{incremental['jobs']:.0f} jobs "
                f"(~${incremental['job_value']:,.0f} in value) "
                f"vs. a normal period in {n_treated} impacted ZIP codes."
            ),
        }

    def _aggregate_outcomes(self, outcomes: List[Dict]) -> Dict:
        """Aggregate outcome counts and values."""
        inspections = sum(
            1 for o in outcomes if o["outcome_type"] == "inspection_scheduled"
        )
        completed = sum(
            1 for o in outcomes if o["outcome_type"] == "inspection_completed"
        )
        jobs = sum(1 for o in outcomes if o["outcome_type"] == "job_sold")
        value = sum(o["value"] for o in outcomes if o["outcome_type"] == "job_sold")

        contacted = sum(
            1
            for o in outcomes
            if o["outcome_type"] in ["inspection_scheduled", "job_sold"]
        )
        total_entities = len(set(o["entity_id"] for o in outcomes))

        conversion_rate = (jobs / contacted * 100) if contacted else 0

        return {
            "inspections_scheduled": inspections,
            "inspections_completed": completed,
            "inspections": inspections,
            "jobs_sold": jobs,
            "jobs": jobs,
            "job_value": value,
            "contacted": contacted,
            "unique_entities": total_entities,
            "conversion_rate": conversion_rate,
        }

    def estimate_playbook_lift(
        self,
        storm_event_id: Optional[str] = None,
        start_date: str = None,
        end_date: str = None,
        zip_codes: Optional[List[str]] = None,
        control_playbook: str = "door_knock",
    ) -> Dict:
        """
        Estimate lift from different outreach playbooks.

        Compares conversion rates and job values across playbook types.
        Optionally focuses on post-storm periods for storm-attributed lift.

        Args:
            storm_event_id: If provided, focus on outcomes after this storm
            start_date: Start of analysis period
            end_date: End of analysis period
            zip_codes: ZIP codes to include
            control_playbook: Baseline playbook for comparison

        Returns:
            Dict with per-playbook metrics and lift vs. control
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        outreach = self._get_outreach_in_period(start_date, end_date, zip_codes)
        outcomes = self._get_outcomes_in_period(start_date, end_date, zip_codes)

        playbook_outreach = defaultdict(list)
        for o in outreach:
            playbook_outreach[o["playbook_type"]].append(o)

        playbook_outcomes = defaultdict(list)
        for o in outcomes:
            playbook_outcomes[o["outcome_type"]].append(o)

        entity_outcomes = defaultdict(dict)
        for o in outcomes:
            entity_outcomes[o["entity_id"]][o["outcome_type"]] = o

        playbook_metrics = {}

        for playbook, interactions in playbook_outreach.items():
            unique_entities = len(set(i["entity_id"] for i in interactions))

            entities_with_outcome = set()
            for i in interactions:
                if i["entity_id"] in entity_outcomes:
                    for outcome_type, outcome_data in entity_outcomes[
                        i["entity_id"]
                    ].items():
                        entities_with_outcome.add((i["entity_id"], outcome_type))

            inspections = sum(
                1 for e, t in entities_with_outcome if t == "inspection_scheduled"
            )
            jobs = sum(1 for e, t in entities_with_outcome if t == "job_sold")
            job_value = sum(
                entity_outcomes[e]["job_sold"]["value"]
                for e, t in entities_with_outcome
                if t == "job_sold"
                and e in entity_outcomes
                and "job_sold" in entity_outcomes[e]
            )

            conversion_rate = (jobs / unique_entities * 100) if unique_entities else 0
            inspection_rate = (
                (inspections / unique_entities * 100) if unique_entities else 0
            )

            playbook_metrics[playbook] = {
                "total_interactions": len(interactions),
                "unique_entities": unique_entities,
                "inspections_scheduled": inspections,
                "jobs_sold": jobs,
                "total_job_value": job_value,
                "conversion_rate": conversion_rate,
                "inspection_rate": inspection_rate,
                "avg_job_value": (job_value / jobs) if jobs else 0,
            }

        if control_playbook not in playbook_metrics:
            return {
                "error": f"Control playbook '{control_playbook}' not found in data",
                "available_playbooks": list(playbook_metrics.keys()),
            }

        control = playbook_metrics[control_playbook]

        lift = {}
        for playbook, metrics in playbook_metrics.items():
            if playbook == control_playbook:
                continue

            lift[playbook] = {
                "vs_control": control_playbook,
                "conversion_lift_pct": (
                    (
                        (metrics["conversion_rate"] - control["conversion_rate"])
                        / control["conversion_rate"]
                        * 100
                    )
                    if control["conversion_rate"] > 0
                    else 0
                ),
                "inspection_lift_pct": (
                    (
                        (metrics["inspection_rate"] - control["inspection_rate"])
                        / control["inspection_rate"]
                        * 100
                    )
                    if control["inspection_rate"] > 0
                    else 0
                ),
                "job_value_lift": metrics["total_job_value"]
                - control["total_job_value"],
                "conversion_rate": metrics["conversion_rate"],
                "total_job_value": metrics["total_job_value"],
            }

        best_playbook = max(
            [(p, m["conversion_rate"]) for p, m in playbook_metrics.items()],
            key=lambda x: x[1],
        )

        sorted_lift = sorted(
            lift.items(), key=lambda x: x[1]["conversion_lift_pct"], reverse=True
        )

        return {
            "analysis_period": {"start": start_date, "end": end_date},
            "storm_event_id": storm_event_id,
            "playbook_metrics": playbook_metrics,
            "playbook_lift": dict(sorted_lift),
            "control_playbook": control_playbook,
            "best_playbook": best_playbook[0],
            "best_conversion_rate": best_playbook[1],
            "summary": (
                f"Best performing follow-up strategy: [{best_playbook[0]}] "
                f"with {best_playbook[1]:.1f}% conversion rate. "
                f"{len(playbook_metrics)} playbooks analyzed."
            ),
            "recommendation": (
                f"Adopt [{best_playbook[0]}] as primary playbook for "
                f"{'post-storm' if storm_event_id else 'general'} outreach."
            ),
        }

    def get_attribution_summary(
        self,
        start_date: str = None,
        end_date: str = None,
        zip_codes: Optional[List[str]] = None,
    ) -> Dict:
        """
        Get full attribution summary combining storm and playbook impact.

        Returns JSON-serializable summary for UI display.
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        outcomes = self._get_outcomes_in_period(start_date, end_date, zip_codes)

        outcomes_by_type = defaultdict(list)
        for o in outcomes:
            outcomes_by_type[o["outcome_type"]].append(o)

        total_value = sum(
            o["value"]
            for o in outcomes
            if o["outcome_type"] in ["job_sold", "job_closed"]
        )

        funnel = {
            "contacted": len(set(o["entity_id"] for o in outcomes)),
            "inspections_scheduled": len(outcomes_by_type["inspection_scheduled"]),
            "inspections_completed": len(outcomes_by_type["inspection_completed"]),
            "jobs_sold": len(outcomes_by_type["job_sold"]),
            "jobs_closed": len(outcomes_by_type["job_closed"]),
            "total_value": total_value,
        }

        funnel["scheduled_rate"] = (
            (funnel["inspections_scheduled"] / funnel["contacted"] * 100)
            if funnel["contacted"]
            else 0
        )
        funnel["completion_rate"] = (
            (funnel["inspections_completed"] / funnel["inspections_scheduled"] * 100)
            if funnel["inspections_scheduled"]
            else 0
        )
        funnel["sale_rate"] = (
            (funnel["jobs_sold"] / funnel["inspections_completed"] * 100)
            if funnel["inspections_completed"]
            else 0
        )

        return {
            "period": {"start": start_date, "end": end_date},
            "funnel": funnel,
            "total_outcomes": len(outcomes),
            "json_serializable": True,
        }

    def get_storm_playbook_matrix(
        self, zip_codes: List[str], storm_date: str, playbook_types: List[str] = None
    ) -> pd.DataFrame:
        """
        Create a matrix of playbook performance by storm exposure level.

        Useful for understanding which playbooks work best in high vs. low
        damage areas.
        """
        if playbook_types is None:
            playbook_types = ["door_knock", "sms", "email", "door_sms", "door_phone"]

        outcomes = self._get_outcomes_in_period(
            storm_date, datetime.now().strftime("%Y-%m-%d"), zip_codes
        )

        outreach = self._get_outreach_in_period(
            storm_date, datetime.now().strftime("%Y-%m-%d"), zip_codes
        )

        playbook_stats = defaultdict(
            lambda: {"interactions": 0, "entities": set(), "jobs": 0, "value": 0}
        )

        for o in outreach:
            pb = o["playbook_type"]
            if pb in playbook_types:
                playbook_stats[pb]["interactions"] += 1
                playbook_stats[pb]["entities"].add(o["entity_id"])

        for o in outcomes:
            if o["outcome_type"] == "job_sold":
                pass

        matrix = []
        for playbook, stats in playbook_stats.items():
            entities = len(stats["entities"])
            conversion = (stats["jobs"] / entities * 100) if entities else 0
            matrix.append(
                {
                    "playbook": playbook,
                    "interactions": stats["interactions"],
                    "entities_reached": entities,
                    "jobs_sold": stats["jobs"],
                    "conversion_rate": round(conversion, 2),
                }
            )

        df = pd.DataFrame(matrix)
        if not df.empty:
            df = df.sort_values("conversion_rate", ascending=False)

        return df


def calculate_baseline_rates(entities: List[Dict], lookback_days: int = 90) -> Dict:
    """
    Calculate baseline conversion rates from historical entity data.

    Useful for setting expectations before storms.
    """
    cutoff = datetime.now() - timedelta(days=lookback_days)

    contacted = [e for e in entities if e.get("outreach_history")]
    sold = [e for e in entities if e.get("jobs_sold", 0) > 0]

    return {
        "total_entities": len(entities),
        "contacted_count": len(contacted),
        "contact_rate": (len(contacted) / len(entities) * 100) if entities else 0,
        "sold_count": len(sold),
        "overall_conversion": (len(sold) / len(entities) * 100) if entities else 0,
        "contacted_conversion": (len(sold) / len(contacted) * 100) if contacted else 0,
        "avg_job_value": (
            sum(e.get("total_job_value", 0) for e in sold) / len(sold) if sold else 0
        ),
    }


def simple_uplift_test(
    treatment_entities: List[Dict],
    control_entities: List[Dict],
    metric: str = "jobs_sold",
) -> Dict:
    """
    Simple A/B uplift comparison between two entity groups.

    Args:
        treatment_entities: Entities that received intervention
        control_entities: Control group entities
        metric: Metric to compare ('jobs_sold', 'inspections_scheduled', etc.)

    Returns:
        Dict with uplift metrics
    """
    treatment_n = len(treatment_entities)
    control_n = len(control_entities)

    treatment_value = sum(e.get(metric, 0) for e in treatment_entities)
    control_value = sum(e.get(metric, 0) for e in control_entities)

    treatment_rate = (treatment_value / treatment_n * 100) if treatment_n else 0
    control_rate = (control_value / control_n * 100) if control_n else 0

    if control_rate > 0:
        uplift_pct = ((treatment_rate - control_rate) / control_rate) * 100
    else:
        uplift_pct = 0 if treatment_rate == 0 else float("inf")

    return {
        "metric": metric,
        "treatment_n": treatment_n,
        "control_n": control_n,
        "treatment_rate": treatment_rate,
        "control_rate": control_rate,
        "uplift_pct": uplift_pct,
        "treatment_total": treatment_value,
        "control_total": control_value,
        "incremental": treatment_value - control_value,
        "significant": abs(uplift_pct) > 10,
    }


def playbook_lift_dataframe(playbook_results: Dict) -> pd.DataFrame:
    """Convert playbook lift results to a formatted DataFrame for display."""
    if "playbook_metrics" not in playbook_results:
        return pd.DataFrame()

    metrics = playbook_results["playbook_metrics"]
    control = playbook_results.get("control_playbook", "door_knock")

    rows = []
    for playbook, data in metrics.items():
        lift_pct = 0
        if playbook != control and "playbook_lift" in playbook_results:
            lift_data = playbook_results["playbook_lift"].get(playbook, {})
            lift_pct = lift_data.get("conversion_lift_pct", 0)

        rows.append(
            {
                "Playbook": playbook.replace("_", " ").title(),
                "Interactions": data.get("total_interactions", 0),
                "Conversion Rate": f"{data.get('conversion_rate', 0):.1f}%",
                "Lift vs Control": f"{lift_pct:+.1f}%" if playbook != control else "—",
                "Total Value": f"${data.get('total_job_value', 0):,.0f}",
                "Avg Job": f"${data.get('avg_job_value', 0):,.0f}"
                if data.get("avg_job_value")
                else "—",
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Conversion Rate", ascending=False)
    return df


def storm_impact_summary_table(impact_results: Dict) -> pd.DataFrame:
    """Format storm impact results as a summary table."""
    if "incremental_impact" not in impact_results:
        return pd.DataFrame()

    inc = impact_results["incremental_impact"]

    return pd.DataFrame(
        [
            {
                "Metric": "Incremental Inspections",
                "Value": f"+{inc.get('inspections', 0):.0f}",
            },
            {"Metric": "Incremental Jobs", "Value": f"+{inc.get('jobs', 0):.0f}"},
            {
                "Metric": "Estimated Revenue",
                "Value": f"${inc.get('job_value', 0):,.0f}",
            },
            {
                "Metric": "Conversion Lift",
                "Value": f"{inc.get('conversion_rate_lift', 0):+.1f}%",
            },
            {
                "Metric": "Treated ZIPs",
                "Value": impact_results.get("treated_zips", "—"),
            },
            {
                "Metric": "Control ZIPs",
                "Value": impact_results.get("control_zips", "—"),
            },
        ]
    )


def incremental_jobs_by_zip(
    entities: List[Dict], treated_zips: List[str], baseline_rate: float = 0.02
) -> pd.DataFrame:
    """
    Estimate incremental jobs by ZIP based on treatment status.

    Args:
        entities: List of entity dicts with zip_code and jobs_sold
        treated_zips: List of ZIP codes that were treated
        baseline_rate: Expected conversion rate without treatment

    Returns:
        DataFrame with ZIP-level incremental job estimates
    """
    zip_stats = defaultdict(lambda: {"entities": 0, "jobs": 0, "treated": False})

    for e in entities:
        z = e.get("zip_code")
        if z:
            zip_stats[z]["entities"] += 1
            zip_stats[z]["jobs"] += e.get("jobs_sold", 0)
            zip_stats[z]["treated"] = z in treated_zips or zip_stats[z]["treated"]

    rows = []
    for zip_code, stats in zip_stats.items():
        expected = stats["entities"] * baseline_rate
        incremental = stats["jobs"] - expected
        lift_pct = ((stats["jobs"] / expected - 1) * 100) if expected > 0 else 0

        rows.append(
            {
                "ZIP": zip_code,
                "Entities": stats["entities"],
                "Jobs Sold": stats["jobs"],
                "Expected (Baseline)": f"{expected:.1f}",
                "Incremental Jobs": f"+{incremental:.1f}"
                if incremental > 0
                else f"{incremental:.1f}",
                "Lift %": f"{lift_pct:+.1f}%",
                "Status": "Treated" if stats["treated"] else "Control",
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Incremental Jobs", ascending=False)
    return df
