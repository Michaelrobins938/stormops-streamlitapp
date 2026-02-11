"""
Interactive Map Visualization Component
Generates tactical deployment maps for field teams
"""

import folium
from folium.plugins import MarkerCluster, HeatMap
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import json


class LeadMapVisualizer:
    """
    Creates interactive maps for storm paths and target properties.
    Tactical deployment visualization for roofing contractors.
    """

    def __init__(self, center_lat: float = 32.7767, center_lon: float = -96.7970):
        """
        Initialize map centered on DFW region.

        Args:
            center_lat: Center latitude (default: Dallas)
            center_lon: Center longitude (default: Dallas)
        """
        self.center = [center_lat, center_lon]
        self.map = None

    def create_storm_lead_map(
        self,
        leads_df: pd.DataFrame,
        storm_polygons: List[Dict] = None,
        output_file: str = "storm_leads_map.html",
    ) -> str:
        """
        Create interactive map with storm paths and prioritized leads.

        Args:
            leads_df: DataFrame with scored leads (must have lat, lon, priority_tier)
            storm_polygons: List of storm polygon coordinates
            output_file: Output HTML file path

        Returns:
            Path to generated HTML file
        """
        # Create base map
        m = folium.Map(location=self.center, zoom_start=10, tiles="CartoDB positron")

        # Add storm polygons if provided
        if storm_polygons:
            for storm in storm_polygons:
                folium.Polygon(
                    locations=storm["coordinates"],
                    popup=f'Hail: {storm.get("hail_size", "N/A")}"',
                    color="red",
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.2,
                    weight=2,
                ).add_to(m)

        # Color coding by priority tier
        tier_colors = {
            "A": "#d62728",  # Red - Immediate
            "B": "#ff7f0e",  # Orange - Priority
            "C": "#2ca02c",  # Green - Standard
            "D": "#1f77b4",  # Blue - Nurture
        }

        # Group leads by tier for layer control
        tier_groups = {}
        for tier in ["A", "B", "C", "D"]:
            tier_groups[tier] = folium.FeatureGroup(name=f"{tier}-Tier Leads")

        # Add lead markers
        for _, lead in leads_df.iterrows():
            tier = lead.get("priority_tier", "C")
            color = tier_colors.get(tier, "gray")

            # Create popup content
            popup_html = f"""
            <div style='font-family: Arial; min-width: 200px;'>
                <h4 style='margin: 0; color: {color};'>{tier}-Tier Lead</h4>
                <p style='margin: 5px 0;'><strong>Score:</strong> {lead.get("lead_score", "N/A")}/100</p>
                <p style='margin: 5px 0;'><strong>Address:</strong> {lead.get("address", "N/A")}</p>
                <p style='margin: 5px 0;'><strong>ZIP:</strong> {lead.get("zip_code", "N/A")}</p>
                <p style='margin: 5px 0;'><strong>Hail:</strong> {lead.get("hail_size", "N/A")}\"</p>
                <p style='margin: 5px 0;'><strong>Roof Age:</strong> {lead.get("roof_age", "N/A")} years</p>
                <p style='margin: 5px 0;'><strong>Value:</strong> ${lead.get("property_value", 0):,}</p>
                <p style='margin: 5px 0;'><strong>Est. Claim:</strong> ${lead.get("estimated_value", 0):,}</p>
                <p style='margin: 5px 0; font-size: 11px; color: gray;'>
                    Action: {lead.get("recommended_action", "N/A")}
                </p>
            </div>
            """

            folium.CircleMarker(
                location=[lead["lat"], lead["lon"]],
                radius=8,
                popup=folium.Popup(popup_html, max_width=300),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                weight=2,
            ).add_to(tier_groups[tier])

        # Add tier groups to map
        for tier, group in tier_groups.items():
            group.add_to(m)

        # Add heatmap layer for lead density
        if not leads_df.empty:
            heat_data = [
                [row["lat"], row["lon"], row.get("lead_score", 50) / 100]
                for _, row in leads_df.iterrows()
            ]
            HeatMap(heat_data, radius=15, blur=25).add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        # Add legend
        legend_html = """
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; 
                    border:2px solid grey; z-index:9999; 
                    font-size:14px; background-color:white;
                    padding: 10px;
                    border-radius: 5px;">
            <p style="margin: 0;"><strong>Priority Tiers</strong></p>
            <p style="margin: 5px 0;"><span style="color: #d62728;">●</span> A-Tier (Immediate)</p>
            <p style="margin: 5px 0;"><span style="color: #ff7f0e;">●</span> B-Tier (Priority)</p>
            <p style="margin: 5px 0;"><span style="color: #2ca02c;">●</span> C-Tier (Standard)</p>
            <p style="margin: 5px 0;"><span style="color: #1f77b4;">●</span> D-Tier (Nurture)</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # Save map
        m.save(output_file)
        self.map = m

        return output_file

    def create_territory_coverage_map(
        self, routes_df: pd.DataFrame, output_file: str = "territory_coverage.html"
    ) -> str:
        """
        Create map showing sales rep territory coverage.

        Args:
            routes_df: DataFrame with route assignments (rep_name, leads_assigned)
            output_file: Output HTML file path
        """
        m = folium.Map(location=self.center, zoom_start=10)

        # Add county boundaries (simplified)
        # In production, would load GeoJSON for DFW counties

        # Add rep territories
        colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]

        for idx, route in routes_df.iterrows():
            color = colors[idx % len(colors)]

            # Add rep's leads
            if "leads" in route and route["leads"]:
                for lead in route["leads"]:
                    folium.CircleMarker(
                        location=[lead["lat"], lead["lon"]],
                        radius=6,
                        popup=f"Rep: {route.get('rep_name', 'Unassigned')}",
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.6,
                    ).add_to(m)

        m.save(output_file)
        return output_file

    def generate_map_summary(self, leads_df: pd.DataFrame) -> Dict:
        """
        Generate summary statistics for the map view.
        """
        if leads_df.empty:
            return {"error": "No leads to visualize"}

        tier_counts = leads_df["priority_tier"].value_counts().to_dict()

        return {
            "total_leads": len(leads_df),
            "a_tier": tier_counts.get("A", 0),
            "b_tier": tier_counts.get("B", 0),
            "c_tier": tier_counts.get("C", 0),
            "d_tier": tier_counts.get("D", 0),
            "avg_lead_score": round(leads_df["lead_score"].mean(), 1),
            "total_estimated_value": int(leads_df["estimated_value"].sum()),
            "map_bounds": {
                "min_lat": leads_df["lat"].min(),
                "max_lat": leads_df["lat"].max(),
                "min_lon": leads_df["lon"].min(),
                "max_lon": leads_df["lon"].max(),
            },
        }


# Example usage
if __name__ == "__main__":
    print("🗺️  Lead Map Visualizer")
    print("=" * 70)

    # Create sample leads data
    sample_leads = pd.DataFrame(
        [
            {
                "address": "123 Oak St",
                "lat": 32.7767,
                "lon": -96.7970,
                "zip_code": "75201",
                "priority_tier": "A",
                "lead_score": 92,
                "hail_size": 2.5,
                "roof_age": 18,
                "property_value": 550000,
                "estimated_value": 14000,
                "recommended_action": "IMMEDIATE_OUTREACH",
            },
            {
                "address": "456 Maple Ave",
                "lat": 32.7800,
                "lon": -96.8000,
                "zip_code": "75202",
                "priority_tier": "B",
                "lead_score": 76,
                "hail_size": 1.8,
                "roof_age": 15,
                "property_value": 420000,
                "estimated_value": 11000,
                "recommended_action": "PRIORITY_OUTREACH",
            },
            {
                "address": "789 Pine Dr",
                "lat": 32.7750,
                "lon": -96.7950,
                "zip_code": "75201",
                "priority_tier": "A",
                "lead_score": 88,
                "hail_size": 2.2,
                "roof_age": 20,
                "property_value": 380000,
                "estimated_value": 12500,
                "recommended_action": "IMMEDIATE_OUTREACH",
            },
        ]
    )

    # Create visualizer
    visualizer = LeadMapVisualizer()

    # Sample storm polygon (DFW area)
    storm_polygons = [
        {
            "coordinates": [
                [32.77, -96.81],
                [32.78, -96.79],
                [32.78, -96.78],
                [32.77, -96.79],
                [32.77, -96.81],
            ],
            "hail_size": 2.5,
        }
    ]

    # Generate map
    map_file = visualizer.create_storm_lead_map(
        sample_leads,
        storm_polygons=storm_polygons,
        output_file="sample_storm_leads_map.html",
    )

    print(f"\n✅ Map generated: {map_file}")

    # Generate summary
    summary = visualizer.generate_map_summary(sample_leads)
    print(f"\n📊 Map Summary:")
    print(f"   Total Leads: {summary['total_leads']}")
    print(f"   A-Tier: {summary['a_tier']}")
    print(f"   B-Tier: {summary['b_tier']}")
    print(f"   Total Est. Value: ${summary['total_estimated_value']:,}")
    print(f"   Avg Lead Score: {summary['avg_lead_score']}")
