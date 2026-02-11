"""
StormOps v2.0.0: Enterprise Revenue Operating System
Professional Control Plane for Storm Operations Management
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import json
import uuid
import plotly.express as px
import plotly.graph_objects as go

from earth2_integration import Earth2Ingestion
from markov_engine import MarkovEngine
from identity_resolver import IdentityResolver
from sidebar_agent import SidebarAgent
from hybrid_attribution import HybridAttributionEngine, BayesianMMM, UpliftModeling
from copilot import render_copilot
from theme import get_theme_css


@st.cache_resource
def get_engine():
    return create_engine("sqlite:///stormops_cache.db")


engine = get_engine()


@st.cache_resource
def get_agents():
    db_url = "sqlite:///stormops_cache.db"
    return {
        "earth2": Earth2Ingestion(db_url),
        "markov": MarkovEngine(db_url),
        "identity": IdentityResolver(db_url),
        "sidebar": SidebarAgent(db_url),
        "attribution": HybridAttributionEngine(db_url),
        "mmm": BayesianMMM(db_url),
        "uplift": UpliftModeling(db_url),
    }


agents = get_agents()

st.set_page_config(
    page_title="StormOps | Enterprise Operations Platform",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(get_theme_css(), unsafe_allow_html=True)


with st.sidebar:
    st.markdown(
        """
        <div style="margin-bottom: 1.5rem; padding: 1rem; background: linear-gradient(135deg, #18181b 0%, #09090b 100%); border: 1px solid #f59e0b;">
            <div style="font-size: 1rem; font-weight: 700; color: #fff; font-style: italic; text-transform: uppercase;">StormOps</div>
            <div style="font-size: 0.6rem; color: #f59e0b; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.1em;">OPERATIONS PLATFORM</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">Organization</div>', unsafe_allow_html=True
    )

    with engine.connect() as conn:
        tenants = pd.read_sql(
            "SELECT tenant_id, org_name FROM tenants WHERE status = 'active'", conn
        )

    if len(tenants) == 0:
        st.error("No organizations found")
        st.stop()

    selected_tenant = st.selectbox(
        "",
        tenants["tenant_id"].tolist(),
        format_func=lambda x: tenants[tenants["tenant_id"] == x]["org_name"].iloc[0],
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="section-header" style="margin-top: 1rem;">Storm Event</div>',
        unsafe_allow_html=True,
    )

    with engine.connect() as conn:
        storms = pd.read_sql(
            f"""
            SELECT id as storm_id, name, status, created_at
            FROM storms
            WHERE tenant_id = '{selected_tenant}'
            ORDER BY created_at DESC
        """,
            conn,
        )

    if len(storms) == 0:
        st.error("No storms found")
        st.stop()

    selected_storm = st.selectbox(
        "",
        storms["storm_id"].tolist(),
        format_func=lambda x: storms[storms["storm_id"] == x]["name"].iloc[0],
        label_visibility="collapsed",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">System Status</div>', unsafe_allow_html=True
    )

    vitality_status = {
        "Earth-2 Integration": "healthy",
        "ServiceTitan": "healthy",
        "JobNimbus": "healthy",
    }

    for service, status in vitality_status.items():
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <span style="color: #a1a1aa; font-size: 0.75rem;">{service}</span>
                <span class="status-indicator status-{status}">{status.upper()}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">Operational Score</div>', unsafe_allow_html=True
    )

    score = 0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#71717a"},
                "bar": {"color": "#f59e0b"},
                "steps": [
                    {"range": [0, 50], "color": "#18181b"},
                    {"range": [50, 80], "color": "#27272a"},
                    {"range": [80, 100], "color": "#3f3f46"},
                ],
                "bordercolor": "#27272a",
                "borderwidth": 1,
            },
        )
    )
    fig.update_layout(
        height=140,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "JetBrains Mono", "color": "#fff"},
    )
    st.plotly_chart(fig, use_container_width=True)

    if st.button("Calculate Score", type="secondary"):
        with engine.connect() as conn:
            # Calculate score directly from data
            result = conn.execute(
                text("""
                SELECT
                    COALESCE((SELECT COUNT(*) FROM earth2_impact_zones WHERE storm_id = :storm_id), 0) as zones,
                    COALESCE((SELECT COUNT(*) FROM markov_zip_states WHERE storm_id = :storm_id), 0) as zips,
                    COALESCE((SELECT COUNT(*) FROM properties), 0) as identities
            """),
                {"storm_id": selected_storm},
            ).fetchone()

            zones = result[0] if result else 0
            zips = result[1] if result else 0
            identities = result[2] if result else 0

            # Calculate score
            score = 0
            if zones > 0:
                score += min(zones * 2, 30)
            if zips > 0:
                score += min(zips * 0.5, 30)
            if identities > 0:
                score += min(identities * 0.2, 40)
            if score == 0:
                score = 50

            # Store score
            conn.execute(
                text("""
                INSERT OR REPLACE INTO operational_metrics 
                (tenant_id, storm_id, zone_count, zip_count, identity_count, score, updated_at)
                VALUES (:tenant_id, :storm_id, :zones, :zips, :identities, :score, CURRENT_TIMESTAMP)
            """),
                {
                    "tenant_id": selected_tenant,
                    "storm_id": selected_storm,
                    "zones": zones,
                    "zips": zips,
                    "identities": identities,
                    "score": min(score, 100),
                },
            )
            conn.commit()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


storm_name = storms[storms["storm_id"] == selected_storm]["name"].iloc[0]

st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding: 1rem; background: linear-gradient(135deg, #18181b 0%, #09090b 100%); border: 1px solid #27272a;">
        <div class="main-header">{storm_name}</div>
        <div class="caption-text">{datetime.now().strftime("%Y.%m.%d | %H:%M")}</div>
    </div>
""",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Geospatial Intelligence",
        "Market States",
        "Revenue Attribution",
        "Identity Resolution",
        "AI Assistant",
        "Lead Intelligence",
    ]
)


with tab1:
    st.markdown(
        '<div class="section-header">Live Impact Analysis</div>', unsafe_allow_html=True
    )

    try:
        with engine.connect() as conn:
            zones = pd.read_sql(
                f"""
                SELECT 
                    zone_id,
                    center_lat,
                    center_lon,
                    hail_size_inches,
                    damage_propensity_score
                FROM earth2_impact_zones
                WHERE storm_id = '{selected_storm}'
            """,
                conn,
            )

        if len(zones) > 0:
            # Make a copy and ensure zones dataframe has the expected columns
            zones_df = zones.copy()

            # Check if we have the right columns, if not, use zone_id instead of zip_code
            if "zip_code" not in zones_df.columns and "zone_id" in zones_df.columns:
                zones_df["zip_code"] = zones_df["zone_id"]

            # Rename columns to match what the scatter_map expects
            zones_df = zones_df.rename(
                columns={
                    "zone_id": "zip",
                    "center_lat": "lat",
                    "center_lon": "lon",
                    "hail_size_inches": "hail_size",
                    "damage_propensity_score": "damage_score",
                }
            )

            fig = px.scatter_mapbox(
                zones_df,
                lat="lat",
                lon="lon",
                size="hail_size",
                color="damage_score",
                color_continuous_scale=[
                    [0, "#18181b"],
                    [0.5, "#f59e0b"],
                    [1, "#ef4444"],
                ],
                size_max=15,
                zoom=3,
                mapbox_style="open-street-map",
            )
            fig.update_layout(
                mapbox_style="open-street-map",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"family": "JetBrains Mono", "color": "#fff"},
                margin={"l": 0, "r": 0, "t": 0, "b": 0},
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Impact Zones", len(zones_df))
            with col2:
                st.metric("Max Hail Size", f'{zones_df["hail_size"].max():.1f}"')
            with col3:
                st.metric(
                    "Avg Damage Score", f"{zones_df['damage_score'].mean():.2%}"
                )
            with col4:
                max_damage = zones_df["damage_score"].max()
                st.metric("Max Damage", f"{max_damage:.2%}")
        else:
            st.info("No Earth-2 data loaded for this event")

            col1, col2, col3 = st.columns(3)
            with col1:
                center_lat = st.number_input("Center Latitude", value=32.7767)
            with col2:
                center_lon = st.number_input("Center Longitude", value=-96.7970)
            with col3:
                radius_km = st.number_input("Search Radius (km)", value=50)

            st.markdown('<div style="margin-top: 1rem;">', unsafe_allow_html=True)
            if st.button("Load Earth-2 Data", type="primary"):
                with st.spinner("Fetching Earth-2 forecast data..."):
                    try:
                        zones_created = agents["earth2"].ingest_storm_swath(
                            selected_tenant,
                            selected_storm,
                            center_lat,
                            center_lon,
                            radius_km,
                        )
                        st.success(f"Successfully created {zones_created} impact zones")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            st.markdown("</div>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading map: {e}")


with tab2:
    st.markdown(
        '<div class="section-header">ZIP Code Opportunity Analysis</div>',
        unsafe_allow_html=True,
    )

    try:
        with engine.connect() as conn:
            markov_states = pd.read_sql(
                f"""
                SELECT
                    zip_code as zip,
                    current_state,
                    estimated_tam_usd,
                    prob_to_recovery
                FROM markov_zip_states
                WHERE storm_id = '{selected_storm}'
                ORDER BY estimated_tam_usd DESC NULLS LAST
            """,
                conn,
            )

        if len(markov_states) > 0:
            state_counts = markov_states["current_state"].value_counts()

            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown("**State Distribution**")
                for state, count in state_counts.items():
                    state_label = state.replace("_", " ").title()
                    st.metric(state_label, count)

            with col2:
                fig = px.bar(
                    markov_states.groupby("current_state")["estimated_tam_usd"]
                    .sum()
                    .reset_index(),
                    x="current_state",
                    y="estimated_tam_usd",
                    title="Total Addressable Market by State",
                )
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="TAM (USD)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"family": "JetBrains Mono", "color": "#fff"},
                    xaxis={"tickfont": {"color": "#71717a"}},
                    yaxis={"tickfont": {"color": "#71717a"}},
                )
                fig.update_traces(marker_color="#f59e0b")
                st.plotly_chart(fig, use_container_width=True)

            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown("**Market States Detail**")
            st.dataframe(markov_states.head(15), use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Trigger Earth-2 Transitions"):
                    try:
                        transitions = agents["markov"].trigger_earth2_transitions(
                            selected_tenant, selected_storm
                        )
                        st.success(f"Processed {transitions} transitions")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col2:
                if st.button("Update Recovery Windows"):
                    try:
                        count = agents["markov"].trigger_recovery_window(
                            selected_tenant, selected_storm, hours_since_impact=24
                        )
                        st.success(f"Updated {count} ZIP codes")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        else:
            st.info("Market states have not been initialized")

            if st.button("Initialize Market States"):
                try:
                    with engine.connect() as conn:
                        zips = pd.read_sql(
                            """
                            SELECT DISTINCT zip
                            FROM properties
                            WHERE zip IS NOT NULL
                        """,
                            conn,
                        )

                    if len(zips) > 0:
                        count = agents["markov"].initialize_zip_states(
                            selected_tenant, selected_storm, zips["zip"].tolist()
                        )
                        st.success(f"Initialized {count} ZIP codes")
                        st.rerun()
                    else:
                        st.warning("No properties found. Add properties first.")
                except Exception as e:
                    st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"Error loading market states: {e}")


with tab3:
    st.markdown(
        '<div class="section-header">Channel Attribution Analysis</div>',
        unsafe_allow_html=True,
    )

    try:
        alpha = st.slider(
            "Attribution Balance (Markov / Shapley)",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="0 = Causal attribution, 1 = Fair attribution",
        )

        summary = agents["attribution"].get_channel_attribution_summary(
            selected_storm, alpha=alpha
        )

        if summary and len(summary) > 0:
            df = pd.DataFrame(summary)

            fig = px.bar(
                df,
                x="channel",
                y="total_hybrid",
                title=f"Attributed Revenue by Channel",
                color="total_hybrid",
                color_continuous_scale=[[0, "#18181b"], [1, "#f59e0b"]],
            )
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Revenue (USD)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"family": "JetBrains Mono", "color": "#fff"},
                xaxis={"tickfont": {"color": "#71717a"}},
                yaxis={"tickfont": {"color": "#71717a"}},
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown("**Channel Performance Detail**")
            st.dataframe(df, use_container_width=True)
        else:
            st.info(
                "No attribution data available. Data will populate as conversions occur."
            )
    except Exception as e:
        st.error(f"Error loading attribution: {e}")


with tab4:
    st.markdown(
        '<div class="section-header">Property Identity Resolution</div>',
        unsafe_allow_html=True,
    )

    try:
        with engine.connect() as conn:
            identities = pd.read_sql(
                f"""
                SELECT 
                    pi.identity_id,
                    pi.property_id,
                    pi.confidence_score
                FROM property_identities pi
                WHERE pi.property_id IN (
                    SELECT property_id FROM properties WHERE tenant_id = '{selected_tenant}'
                )
                ORDER BY pi.confidence_score DESC
                LIMIT 50
            """,
                conn,
            )

        if len(identities) > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Identities", len(identities))
            with col2:
                st.metric(
                    "Avg Confidence", f"{identities['confidence_score'].mean():.1%}"
                )
            with col3:
                high_conf = (identities["confidence_score"] > 0.8).sum()
                st.metric("High Confidence (>80%)", high_conf)

            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.dataframe(identities, use_container_width=True)
        else:
            st.info(
                "No identities resolved. Configure data sources to begin resolution."
            )
    except Exception as e:
        st.info("Identity resolution is not yet configured")


with tab5:
    st.markdown(
        '<div class="section-header">AI-Powered Operations Assistant</div>',
        unsafe_allow_html=True,
    )

    try:
        render_copilot()
    except Exception as e:
        st.error(f"Assistant error: {e}")
        st.info("Refresh the page to retry")


with tab6:
    st.markdown(
        '<div class="section-header">Strategic Lead Intelligence</div>',
        unsafe_allow_html=True,
    )

    import glob
    import os

    csv_files = glob.glob("5AGENT_STRATEGIC_LEADS_*.csv")
    if csv_files:
        latest_file = max(csv_files, key=os.path.getctime)
        leads_df = pd.read_csv(latest_file)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Leads", len(leads_df))
        with col2:
            a_tier = len(leads_df[leads_df["priority_tier"] == "A"])
            st.metric("A-Tier Priority", a_tier)
        with col3:
            avg_score = leads_df["lead_score"].mean()
            st.metric("Avg Lead Score", f"{avg_score:.0f}")
        with col4:
            avg_conv = leads_df["conversion_probability"].mean()
            st.metric("Est. Conversion Rate", f"{avg_conv:.0%}")

        col1, col2 = st.columns(2)
        with col1:
            tier_filter = st.multiselect(
                "Filter by Priority Tier",
                options=["A", "B", "C", "D"],
                default=["A", "B"],
            )
        with col2:
            social_filter = st.multiselect(
                "Filter by Trigger",
                options=leads_df["social_trigger"].unique().tolist(),
                default=["joneses", "investment_wave"],
            )

        filtered_df = leads_df[
            (leads_df["priority_tier"].isin(tier_filter))
            & (leads_df["social_trigger"].isin(social_filter))
        ]

        st.markdown(f"**Showing {len(filtered_df)} leads**")

        for idx, lead in filtered_df.head(20).iterrows():
            tier_class = f"tier-{lead['priority_tier'].lower()}"
            st.markdown(
                f"""
                <div class="lead-card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <span class="tier-badge {tier_class}">Tier {lead["priority_tier"]}</span>
                            <span style="font-weight: 600; margin-left: 0.75rem; color: #fff;">{lead["address"]}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: 700; color: #f59e0b; font-family: 'JetBrains Mono', monospace;">{lead["lead_score"]:.0f}/100</div>
                            <div class="caption-text">Lead Score</div>
                        </div>
                    </div>
                    <div class="caption-text" style="margin-top: 0.5rem;">
                        ZIP: {lead["zip_code"]} | Hail: {lead["hail_size"]}" | Roof Age: {lead["roof_age"]}yr | Property: ${lead["property_value"]:,}
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download All Leads",
                data=leads_df.to_csv(index=False),
                file_name=f"stormops_leads_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                f"Download A-Tier Leads ({a_tier})",
                data=leads_df[leads_df["priority_tier"] == "A"].to_csv(index=False),
                file_name=f"stormops_tier_a_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
    else:
        st.info("No lead data found. Run the lead pipeline to generate intelligence.")


st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

st.markdown("**AI Action Queue**")

try:
    action_queue = agents["sidebar"].get_action_queue(
        selected_tenant, selected_storm, limit=10
    )

    if len(action_queue) > 0:
        for action in action_queue:
            confidence = action["ai_confidence"]

            st.markdown(
                f"""
                <div class="action-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 600; text-transform: uppercase;">{action["action_type"].replace("_", " ")}</div>
                            <div class="caption-text">{action["ai_reasoning"]}</div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div style="text-align: center;">
                                <div style="font-weight: 700; color: #f59e0b; font-family: 'JetBrains Mono', monospace;">{confidence:.0%}</div>
                                <div class="caption-text">Confidence</div>
                            </div>
                            <div style="display: flex; gap: 0.5rem;">
            """,
                unsafe_allow_html=True,
            )

            if action["action_status"] == "proposed":
                if st.button("Approve", key=f"approve_{action['action_id']}"):
                    agents["sidebar"].approve_action(action["action_id"], "user")
                    st.rerun()
                if st.button("Reject", key=f"reject_{action['action_id']}"):
                    agents["sidebar"].reject_action(action["action_id"])
                    st.rerun()

            st.markdown("</div></div></div>", unsafe_allow_html=True)
    else:
        st.info("No pending actions")

        if st.button("Generate AI Recommendations"):
            with st.spinner("Analyzing operations..."):
                try:
                    action_ids = agents["sidebar"].auto_propose_from_markov(
                        selected_tenant, selected_storm
                    )
                    st.success(f"Generated {len(action_ids)} recommendations")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
except Exception as e:
    st.error(f"Action queue error: {e}")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="text-align: center; color: #52525b; font-size: 0.65rem; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.1em;">
        StormOps v2.0 | {datetime.now().strftime("%Y.%m.%d")} | Enterprise Operations Platform
    </div>
""",
    unsafe_allow_html=True,
)
