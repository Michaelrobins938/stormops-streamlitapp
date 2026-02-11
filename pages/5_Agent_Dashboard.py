"""
5-Agent Multi-Agent System Dashboard
Streamlit interface for the autonomous roofing lead generation system
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theme import get_theme_css

st.set_page_config(
    page_title="5-Agent System | StormOps",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_theme_css(), unsafe_allow_html=True)

st.markdown("## Autonomous Multi-Agent System")
st.markdown("5-Agent Intelligence for Roofing Market Dominance")


# Load data
@st.cache_data
def load_lead_data():
    """Load the latest 5-agent lead data"""
    import glob

    csv_files = glob.glob("5AGENT_STRATEGIC_LEADS_*.csv")
    if csv_files:
        latest = max(csv_files)
        return pd.read_csv(latest)
    return None


df = load_lead_data()

if df is not None:
    st.success(f" Loaded {len(df):,} leads from latest analysis")

    # Top Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Properties Analyzed", f"{len(df):,}", "100% coverage")

    with col2:
        a_tier = len(df[df["priority_tier"] == "A"])
        st.metric(
            "A-Tier Leads (Immediate)",
            f"{a_tier:,}",
            f"{a_tier / len(df) * 100:.1f}% of total",
        )

    with col3:
        avg_score = df["lead_score"].mean()
        st.metric("Average Lead Score", f"{avg_score:.1f}/100", "Excellent quality")

    with col4:
        avg_conv = df["conversion_probability"].mean()
        st.metric(
            "Avg Conversion Probability", f"{avg_conv:.1%}", "vs 0.3% traditional"
        )

    st.divider()

    # 5-Agent Breakdown
    st.header(" 5-Agent System Breakdown")

    agent_cols = st.columns(5)

    with agent_cols[0]:
        st.markdown(
            """
        <div class="agent-card">
            <h4> Agent 1</h4>
            <h5>Weather Watcher</h5>
            <p style="font-size: 0.8rem;">NOAA storm tracking<br>Cumulative risk scoring</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with agent_cols[1]:
        st.markdown(
            """
        <div class="agent-card">
            <h4> Agent 2</h4>
            <h5>Scout (Vision)</h5>
            <p style="font-size: 0.8rem;">AI damage detection<br>Code Red/Orange/Yellow</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with agent_cols[2]:
        st.markdown(
            """
        <div class="agent-card">
            <h4> Agent 3</h4>
            <h5>Historian</h5>
            <p style="font-size: 0.8rem;">Permit records<br>Property age validation</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with agent_cols[3]:
        st.markdown(
            """
        <div class="agent-card">
            <h4> Agent 4</h4>
            <h5>Profiler</h5>
            <p style="font-size: 0.8rem;">Economic qualification<br>4-factor scoring</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with agent_cols[4]:
        st.markdown(
            """
        <div class="agent-card">
            <h4> Agent 5</h4>
            <h5>Sociologist</h5>
            <p style="font-size: 0.8rem;"><span class="highlight">SECRET SAUCE</span><br>Joneses Effect detection</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.divider()

    # Agent 5: The Secret Sauce
    st.header(" Agent 5: The Sociologist - Secret Sauce")

    if "social_trigger" in df.columns:
        col1, col2 = st.columns([2, 1])

        with col1:
            # Social trigger distribution
            trigger_counts = df["social_trigger"].value_counts()

            fig = px.pie(
                values=trigger_counts.values,
                names=trigger_counts.index,
                title="Social Trigger Distribution",
                color_discrete_map={
                    "joneses": "#f59e0b",
                    "investment_wave": "#3b82f6",
                    "home_pride": "#10b981",
                    "none": "#6b7280",
                },
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader(" Agent 5 Results")

            joneses_count = len(df[df["social_trigger"] == "joneses"])
            investment_count = len(df[df["social_trigger"] == "investment_wave"])
            high_pressure = len(df[df["social_pressure_score"] >= 70])

            st.markdown(
                f"""
            <div class="metric-card">
                <h4> Joneses Effect</h4>
                <h2>{joneses_count:,}</h2>
                <p>Properties with neighbor pressure</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
            <div class="metric-card">
                <h4> Investment Waves</h4>
                <h2>{investment_count:,}</h2>
                <p>Neighborhood upgrade cycles</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
            <div class="metric-card">
                <h4> High Pressure</h4>
                <h2>{high_pressure:,}</h2>
                <p>Immediate deployment targets</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.divider()

    # Lead Quality Distribution
    st.header(" Lead Quality Analysis")

    tab1, tab2, tab3 = st.tabs(["Score Distribution", "Geographic View", "Top Targets"])

    with tab1:
        fig = px.histogram(
            df,
            x="lead_score",
            color="priority_tier",
            nbins=20,
            title="Lead Score Distribution by Tier",
            labels={"lead_score": "Lead Score", "count": "Number of Properties"},
            color_discrete_map={
                "A": "#ef4444",
                "B": "#f97316",
                "C": "#22c55e",
                "D": "#3b82f6",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if "lat" in df.columns and "lon" in df.columns:
            # Sample for performance
            sample_df = df.sample(min(1000, len(df)))

            fig = px.scatter_mapbox(
                sample_df,
                lat="lat",
                lon="lon",
                color="priority_tier",
                size="lead_score",
                hover_data=["address", "lead_score", "social_trigger"],
                title="Geographic Lead Distribution (Sample)",
                color_discrete_map={
                    "A": "#ef4444",
                    "B": "#f97316",
                    "C": "#22c55e",
                    "D": "#3b82f6",
                },
                zoom=9,
                height=600,
            )
            fig.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Show top 20 A-tier leads
        top_leads = df[df["priority_tier"] == "A"].head(20)

        st.dataframe(
            top_leads[
                [
                    "rank",
                    "address",
                    "city",
                    "zip_code",
                    "lead_score",
                    "conversion_probability",
                    "hail_size",
                    "roof_age",
                    "property_value",
                    "social_trigger",
                    "trigger_description",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ROI Analysis
    st.header(" ROI Analysis")

    roi_col1, roi_col2 = st.columns(2)

    with roi_col1:
        st.subheader("Cost Comparison")

        traditional_cpl = 167
        our_cpl = 1000 / len(df)
        improvement = traditional_cpl / our_cpl

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="Traditional",
                x=["Cost Per Lead"],
                y=[traditional_cpl],
                marker_color="#6b7280",
            )
        )
        fig.add_trace(
            go.Bar(
                name="5-Agent System",
                x=["Cost Per Lead"],
                y=[our_cpl],
                marker_color="#10b981",
            )
        )
        fig.update_layout(
            title=f"{improvement:.1f}x Cost Improvement",
            yaxis_title="Cost ($)",
            barmode="group",
        )
        st.plotly_chart(fig, use_container_width=True)

    with roi_col2:
        st.subheader("Economic Impact")

        total_value = df["property_value"].sum()
        est_claims = df["property_value"].sum() * 0.025  # Assume 2.5% claim rate

        st.metric("Total Property Value Analyzed", f"${total_value:,.0f}")
        st.metric("Estimated Total Claims", f"${est_claims:,.0f}")
        st.metric("Campaign Cost", "$1,000.00")
        st.metric("Potential ROI", f"{est_claims / 1000:.0f}x")

    st.divider()

    # Export Section
    st.header(" Export Lead List")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="Download All Leads (CSV)",
            data=df.to_csv(index=False),
            file_name=f"stormops_5agent_leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    with col2:
        a_tier_df = df[df["priority_tier"] == "A"]
        st.download_button(
            label=f"Download A-Tier Only ({len(a_tier_df)} leads)",
            data=a_tier_df.to_csv(index=False),
            file_name=f"stormops_atier_leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

else:
    st.error(" No lead data found. Please run the 5-agent pipeline first.")

    st.code("""
# Run the pipeline:
python3 automated_lead_pipeline.py --run --state TX
    """)

# Footer
st.divider()
st.caption("StormOps 5-Agent Autonomous System | Production Ready v1.0")
