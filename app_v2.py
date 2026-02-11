"""
StormOps v2: NVIDIA-Native Control Plane
3-Pane Architecture with Agentic Sidebar
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import json
import uuid
import plotly.express as px
import plotly.graph_objects as go

# Import new modules
from earth2_integration import Earth2Ingestion
from markov_engine import MarkovEngine
from identity_resolver import IdentityResolver
from sidebar_agent import SidebarAgent
from hybrid_attribution import HybridAttributionEngine, BayesianMMM, UpliftModeling

# DB connection
@st.cache_resource
def get_engine():
    return create_engine('postgresql://stormops:password@localhost:5432/stormops')

engine = get_engine()

# Initialize agents
@st.cache_resource
def get_agents():
    db_url = 'postgresql://stormops:password@localhost:5432/stormops'
    return {
        'earth2': Earth2Ingestion(db_url),
        'markov': MarkovEngine(db_url),
        'identity': IdentityResolver(db_url),
        'sidebar': SidebarAgent(db_url),
        'attribution': HybridAttributionEngine(db_url),
        'mmm': BayesianMMM(db_url),
        'uplift': UpliftModeling(db_url)
    }

agents = get_agents()

# Page config
st.set_page_config(
    page_title="StormOps Control Plane",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for 3-pane layout
from theme import get_theme_css

st.markdown(get_theme_css(), unsafe_allow_html=True)


# ============================================================================
# PANE A: OBSERVABILITY (LEFT SIDEBAR)
# ============================================================================

with st.sidebar:
    st.markdown("### 🎯 CONTROL PLANE")
    
    # Tenant selector
    with engine.connect() as conn:
        tenants = pd.read_sql("SELECT tenant_id, org_name FROM tenants WHERE status = 'active'", conn)
    
    if len(tenants) == 0:
        st.error("No tenants found")
        st.stop()
    
    selected_tenant = st.selectbox(
        "Tenant",
        tenants['tenant_id'].tolist(),
        format_func=lambda x: tenants[tenants['tenant_id']==x]['org_name'].iloc[0]
    )
    
    # Storm selector
    with engine.connect() as conn:
        storms = pd.read_sql(f"""
            SELECT storm_id, name, status
            FROM storms
            WHERE tenant_id = '{selected_tenant}'
            ORDER BY created_at DESC
        """, conn)
    
    if len(storms) == 0:
        st.error("No storms found")
        st.stop()
    
    selected_storm = st.selectbox(
        "Storm",
        storms['storm_id'].tolist(),
        format_func=lambda x: f"{storms[storms['storm_id']==x]['name'].iloc[0]}"
    )
    
    st.markdown("---")
    
    # SYSTEM VITALITY
    st.markdown("### 📡 SYSTEM VITALITY")
    
    with engine.connect() as conn:
        vitality = pd.read_sql(f"""
            SELECT service_name, status, latency_ms, last_success_at
            FROM system_vitality
            WHERE tenant_id = '{selected_tenant}'
            ORDER BY service_name
        """, conn)
    
    if len(vitality) > 0:
        for _, row in vitality.iterrows():
            status_class = f"status-{row['status']}"
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>{row['service_name']}</span>
                <span class="{status_class}">{row['status'].upper()}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Initialize default services
        with engine.connect() as conn:
            for service in ['earth2', 'servicetitan', 'jobnimbus']:
                conn.execute(text("""
                    INSERT INTO system_vitality (tenant_id, service_name, status)
                    VALUES (:tenant_id, :service, 'healthy')
                    ON CONFLICT DO NOTHING
                """), {"tenant_id": selected_tenant, "service": service})
            conn.commit()
        st.rerun()
    
    st.markdown("---")
    
    # OPERATIONAL SCORE
    st.markdown("### 🎯 OPERATIONAL SCORE")
    
    with engine.connect() as conn:
        score_result = conn.execute(text("""
            SELECT total_score, gap_to_100, next_best_action, calculated_at
            FROM operational_scores
            WHERE tenant_id = :tenant_id AND storm_id = :storm_id
            ORDER BY calculated_at DESC
            LIMIT 1
        """), {"tenant_id": selected_tenant, "storm_id": selected_storm})
        
        score_row = score_result.fetchone()
    
    if score_row:
        score = score_row[0]
        gap = score_row[1]
        
        # Circular progress
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#10B981" if score >= 70 else "#F59E0B"},
                'steps': [
                    {'range': [0, 50], 'color': "#FEE2E2"},
                    {'range': [50, 80], 'color': "#FEF3C7"},
                    {'range': [80, 100], 'color': "#D1FAE5"}
                ]
            }
        ))
        fig.update_layout(height=200, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.metric("Gap to 100", f"{gap} points")
        
        if st.button("🔄 Recalculate Score"):
            with engine.connect() as conn:
                conn.execute(text("""
                    SELECT calculate_operational_score(:tenant_id, :storm_id)
                """), {"tenant_id": selected_tenant, "storm_id": selected_storm})
                conn.commit()
            st.success("Score updated")
            st.rerun()
    else:
        st.info("No score calculated yet")
        if st.button("Calculate Initial Score"):
            with engine.connect() as conn:
                conn.execute(text("""
                    SELECT calculate_operational_score(:tenant_id, :storm_id)
                """), {"tenant_id": selected_tenant, "storm_id": selected_storm})
                conn.commit()
            st.rerun()
    
    st.markdown("---")
    
    # MARKET PULSE
    st.markdown("### 📊 MARKET PULSE")
    
    with engine.connect() as conn:
        pulse = conn.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE decision = 'treat') as treat_count,
                COUNT(*) as total_properties,
                COUNT(DISTINCT zip_code) as active_zips
            FROM policy_decisions_log pdl
            JOIN properties p ON pdl.property_id = p.property_id
            WHERE pdl.storm_id = :storm_id
        """), {"storm_id": selected_storm}).fetchone()
    
    if pulse:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Treat", pulse[0] or 0)
            st.metric("Active ZIPs", pulse[2] or 0)
        with col2:
            st.metric("Total", pulse[1] or 0)

# ============================================================================
# PANE B: DIGITAL TWIN MAP (CENTER)
# ============================================================================

st.markdown('<div class="main-header">🌪️ StormOps Control Plane</div>', unsafe_allow_html=True)
st.caption(f"Storm: {storms[storms['storm_id']==selected_storm]['name'].iloc[0]}")

# Tab navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Tactical Map",
    "🎯 Markov States",
    "📊 Hybrid Attribution",
    "👤 Identity Graph",
    "📋 Job Intelligence"
])

# TAB 1: TACTICAL MAP
with tab1:
    st.subheader("Live Geospatial Intelligence")
    
    # Load Earth-2 zones
    with engine.connect() as conn:
        zones = pd.read_sql(f"""
            SELECT
                zone_id,
                center_lat,
                center_lon,
                hail_size_inches as hail_size,
                damage_propensity_score,
                ST_AsGeoJSON(polygon) as polygon_geojson
            FROM earth2_impact_zones
            WHERE storm_id = '{selected_storm}'
        """, conn)
    
    if len(zones) > 0:
        # Create map
        fig = px.scatter_mapbox(
            zones,
            lat='center_lat',
            lon='center_lon',
            size='hail_size',
            color='damage_propensity_score',
            color_continuous_scale='Reds',
            hover_data=['hail_size', 'damage_propensity_score'],
            zoom=9,
            height=500
        )
        fig.update_layout(mapbox_style="open-street-map")
        st.plotly_chart(fig, use_container_width=True)
        
        # Zone stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Impact Zones", len(zones))
        with col2:
            st.metric("Max Hail", f"{zones['hail_size'].max():.1f}\"")
        with col3:
            st.metric("Avg Damage Score", f"{zones['damage_propensity_score'].mean():.2%}")
    
    else:
        st.info("No Earth-2 data loaded yet")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            center_lat = st.number_input("Center Lat", value=32.7767)
        with col2:
            center_lon = st.number_input("Center Lon", value=-96.7970)
        with col3:
            radius_km = st.number_input("Radius (km)", value=50)
        
        if st.button("🛰️ Load Earth-2 Swath", type="primary"):
            with st.spinner("Fetching Earth-2 data..."):
                zones_created = agents['earth2'].ingest_storm_swath(
                    uuid.UUID(selected_tenant),
                    uuid.UUID(selected_storm),
                    center_lat, center_lon, radius_km
                )
                enriched = agents['earth2'].enrich_properties_with_damage(
                    uuid.UUID(selected_tenant),
                    uuid.UUID(selected_storm)
                )
            st.success(f"✅ Created {zones_created} zones, enriched {enriched} properties")
            st.rerun()

# TAB 2: MARKOV STATES
with tab2:
    st.subheader("ZIP-Code Opportunity Windows")
    
    with engine.connect() as conn:
        markov_states = pd.read_sql(f"""
            SELECT 
                zip_code,
                current_state,
                estimated_tam_usd,
                prob_to_recovery,
                state_entered_at
            FROM markov_zip_states
            WHERE storm_id = '{selected_storm}'
            ORDER BY estimated_tam_usd DESC NULLS LAST
        """, conn)
    
    if len(markov_states) > 0:
        # State distribution
        state_counts = markov_states['current_state'].value_counts()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### State Distribution")
            for state, count in state_counts.items():
                st.metric(state.upper(), count)
        
        with col2:
            # TAM by state
            fig = px.bar(
                markov_states.groupby('current_state')['estimated_tam_usd'].sum().reset_index(),
                x='current_state',
                y='estimated_tam_usd',
                title="TAM by State",
                color='current_state'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Top ZIPs
        st.markdown("### Top Opportunity ZIPs")
        st.dataframe(
            markov_states[['zip_code', 'current_state', 'estimated_tam_usd', 'prob_to_recovery']].head(10),
            use_container_width=True
        )
        
        # Transition controls
        st.markdown("### State Transitions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚡ Trigger Earth-2 Transitions"):
                transitions = agents['markov'].trigger_earth2_transitions(
                    uuid.UUID(selected_tenant),
                    uuid.UUID(selected_storm)
                )
                st.success(f"✅ {transitions}")
                st.rerun()
        
        with col2:
            if st.button("🕐 Trigger Recovery Window"):
                count = agents['markov'].trigger_recovery_window(
                    uuid.UUID(selected_tenant),
                    uuid.UUID(selected_storm),
                    hours_since_impact=24
                )
                st.success(f"✅ {count} ZIPs moved to recovery")
                st.rerun()
    
    else:
        st.info("No Markov states initialized")
        
        # Get unique ZIPs from properties
        with engine.connect() as conn:
            zips = pd.read_sql(f"""
                SELECT DISTINCT zip_code
                FROM properties
                WHERE tenant_id = '{selected_tenant}'
            """, conn)
        
        if len(zips) > 0 and st.button("Initialize Markov States"):
            count = agents['markov'].initialize_zip_states(
                uuid.UUID(selected_tenant),
                uuid.UUID(selected_storm),
                zips['zip_code'].tolist()
            )
            st.success(f"✅ Initialized {count} ZIPs")
            st.rerun()

# TAB 3: HYBRID ATTRIBUTION
with tab3:
    st.subheader("Causal Revenue Attribution")
    
    # α-Sweep Control
    st.markdown("### Attribution Model Control")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        alpha = st.slider(
            "α Parameter (Markov ← → Shapley)",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="0 = Pure Causal (Markov), 1 = Pure Fair (Shapley)"
        )
        
        if alpha < 0.3:
            st.info("🔬 **Causal Mode**: Prioritizing removal effects and incremental lift")
        elif alpha > 0.7:
            st.info("⚖️ **Fairness Mode**: Prioritizing axiomatic credit distribution")
        else:
            st.info("🎯 **Hybrid Mode**: Balanced causal and fair attribution")
    
    with col2:
        st.metric("Current α", f"{alpha:.2f}")
        
        if st.button("Save as Default"):
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO attribution_configs (tenant_id, config_name, alpha_markov, alpha_shapley, is_active)
                    VALUES (:tenant_id, 'default', :alpha, :alpha_inv, TRUE)
                    ON CONFLICT (tenant_id, config_name) 
                    DO UPDATE SET alpha_markov = :alpha, alpha_shapley = :alpha_inv, is_active = TRUE
                """), {
                    "tenant_id": selected_tenant,
                    "alpha": alpha,
                    "alpha_inv": 1 - alpha
                })
                conn.commit()
            st.success("✅ Saved")
    
    # Channel Attribution Summary
    st.markdown("### Channel Attribution")
    
    summary = agents['attribution'].get_channel_attribution_summary(
        uuid.UUID(selected_storm),
        alpha=alpha
    )
    
    if summary:
        df = pd.DataFrame(summary)
        
        # Visualization
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                df,
                x='channel',
                y='total_hybrid',
                title=f"Hybrid Credit by Channel (α={alpha})",
                color='total_hybrid',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Comparison: Markov vs Shapley
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Markov',
                x=df['channel'],
                y=df['avg_markov'],
                marker_color='#F59E0B'
            ))
            fig.add_trace(go.Bar(
                name='Shapley',
                x=df['channel'],
                y=df['avg_shapley'],
                marker_color='#10B981'
            ))
            fig.update_layout(
                title="Markov vs Shapley Credit",
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Data table
        st.dataframe(df, use_container_width=True)
    
    else:
        st.info("No attribution data yet. Journeys will be attributed as conversions occur.")
    
    # α-Sweep Analysis
    st.markdown("### α-Sweep Analysis")
    
    if st.button("Run α-Sweep"):
        with st.spinner("Running sensitivity analysis..."):
            sweep_results = agents['attribution'].alpha_sweep(
                uuid.UUID(selected_storm),
                alpha_range=[0.0, 0.25, 0.5, 0.75, 1.0]
            )
        
        # Visualize how credit changes with α
        sweep_df = pd.DataFrame(sweep_results).T
        sweep_df.index.name = 'alpha'
        sweep_df = sweep_df.reset_index()
        
        fig = go.Figure()
        for channel in sweep_df.columns[1:]:
            fig.add_trace(go.Scatter(
                x=sweep_df['alpha'],
                y=sweep_df[channel],
                mode='lines+markers',
                name=channel
            ))
        
        fig.update_layout(
            title="Channel Credit Sensitivity to α",
            xaxis_title="α (0=Markov, 1=Shapley)",
            yaxis_title="Total Credit",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # MMM Saturation Analysis
    st.markdown("---")
    st.markdown("### Market Saturation Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        channel_name = st.selectbox(
            "Channel",
            ['door_knock', 'sms', 'google_ads', 'facebook']
        )
    
    with col2:
        with engine.connect() as conn:
            zips = pd.read_sql(f"""
                SELECT DISTINCT zip_code
                FROM properties
                WHERE tenant_id = '{selected_tenant}'
            """, conn)
        
        zip_code = st.selectbox("ZIP Code", zips['zip_code'].tolist() if len(zips) > 0 else [])
    
    if st.button("Check Saturation"):
        saturation = agents['mmm'].detect_saturation(
            uuid.UUID(selected_tenant),
            uuid.UUID(selected_storm),
            channel_name,
            zip_code
        )
        
        if 'error' not in saturation:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Touches", saturation['total_touches'])
            with col2:
                st.metric("Saturation Score", f"{saturation['saturation_score']:.2%}")
            with col3:
                status_color = {
                    'saturated': '🔴',
                    'optimal': '🟢',
                    'undersaturated': '🟡'
                }
                st.metric("Status", f"{status_color[saturation['status']]} {saturation['status'].upper()}")
            
            st.info(f"💡 **Recommendation:** {saturation['recommendation']}")
        else:
            st.error(saturation['error'])

# TAB 4: IDENTITY GRAPH
with tab4:
    st.subheader("Property Identity Resolution")
    
    with engine.connect() as conn:
        identities = pd.read_sql(f"""
            SELECT 
                pi.identity_id,
                pi.property_id,
                pi.confidence_score,
                pi.decision_maker_name,
                pi.web_sessions,
                pi.form_submissions,
                p.address,
                p.zip_code
            FROM property_identities pi
            JOIN properties p ON pi.property_id = p.property_id
            WHERE p.tenant_id = '{selected_tenant}'
            ORDER BY pi.confidence_score DESC
            LIMIT 50
        """, conn)
    
    if len(identities) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Identities", len(identities))
        with col2:
            st.metric("Avg Confidence", f"{identities['confidence_score'].mean():.2%}")
        with col3:
            high_conf = (identities['confidence_score'] > 0.8).sum()
            st.metric("High Confidence", high_conf)
        
        st.dataframe(identities, use_container_width=True)
    else:
        st.info("No identities resolved yet")

# TAB 5: JOB INTELLIGENCE
with tab5:
    st.subheader("Field Operations")
    
    with engine.connect() as conn:
        jobs = pd.read_sql(f"""
            SELECT 
                j.job_id,
                j.property_id,
                j.status,
                j.notes,
                p.address,
                p.zip_code,
                r.route_name
            FROM jobs j
            JOIN properties p ON j.property_id = p.property_id
            LEFT JOIN routes r ON j.route_id = r.route_id
            WHERE j.storm_id = '{selected_storm}'
            ORDER BY j.created_at DESC
            LIMIT 50
        """, conn)
    
    if len(jobs) > 0:
        status_counts = jobs['status'].value_counts()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Jobs", len(jobs))
        with col2:
            st.metric("Pending", status_counts.get('pending', 0))
        with col3:
            st.metric("In Progress", status_counts.get('in_progress', 0))
        with col4:
            st.metric("Completed", status_counts.get('completed', 0))
        
        st.dataframe(jobs, use_container_width=True)
    else:
        st.info("No jobs created yet")

# ============================================================================
# PANE C: AGENTIC SIDEBAR (RIGHT)
# ============================================================================

st.markdown("---")
st.markdown("## 🤖 AI ACTION QUEUE")

# Get action queue
action_queue = agents['sidebar'].get_action_queue(
    uuid.UUID(selected_tenant),
    uuid.UUID(selected_storm),
    limit=10
)

if len(action_queue) > 0:
    for action in action_queue:
        confidence = action['ai_confidence']
        card_class = "action-card-high" if confidence > 0.8 else "action-card-medium"
        
        with st.container():
            st.markdown(f'<div class="action-card {card_class}">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{action['action_type'].upper()}**")
                st.caption(action['ai_reasoning'])
            
            with col2:
                st.metric("Confidence", f"{confidence:.0%}")
            
            with col3:
                if action['action_status'] == 'proposed':
                    if st.button("✅ Approve", key=f"approve_{action['action_id']}"):
                        agents['sidebar'].approve_action(uuid.UUID(action['action_id']), "user")
                        st.rerun()
                    if st.button("❌ Reject", key=f"reject_{action['action_id']}"):
                        agents['sidebar'].reject_action(uuid.UUID(action['action_id']))
                        st.rerun()
                
                elif action['action_status'] == 'approved':
                    if st.button("▶️ Execute", key=f"exec_{action['action_id']}"):
                        with st.spinner("Executing..."):
                            result = agents['sidebar'].execute_action(uuid.UUID(action['action_id']))
                        st.success(f"✅ {result}")
                        st.rerun()
                
                elif action['action_status'] == 'executing':
                    st.info("Running...")
            
            st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("No pending actions")
    
    # Auto-propose button
    if st.button("🧠 AI: Analyze & Propose Actions"):
        with st.spinner("AI analyzing storm data..."):
            action_ids = agents['sidebar'].auto_propose_from_markov(
                uuid.UUID(selected_tenant),
                uuid.UUID(selected_storm)
            )
        st.success(f"✅ AI proposed {len(action_ids)} actions")
        st.rerun()

# Footer
st.markdown("---")
st.caption(f"StormOps v2.0 | NVIDIA Earth-2 Powered | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
