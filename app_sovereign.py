"""
StormOps v2.0: Physics-Native Control Plane
Enterprise-grade 3-pane industrial OS
"""
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Initialize session state
if 'moe_state' not in st.session_state:
    st.session_state.moe_state = 'S2_IMPACT'
if 'operational_score' not in st.session_state:
    st.session_state.operational_score = 73
if 'active_proposals' not in st.session_state:
    st.session_state.active_proposals = []

engine = create_engine('sqlite:///stormops_cache.db')

st.set_page_config(page_title="StormOps Control Plane", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS
from theme import get_theme_css

st.markdown(get_theme_css(), unsafe_allow_html=True)

# Header
def render_sovereign_header():
    st.markdown("""
    <div class="main-header">
        <h2 style="color: white; margin: 0;">⚡ StormOps Control Plane</h2>
        <p style="color: #93c5fd; margin: 0; font-size: 0.875rem;">Physics-Native Revenue Operating System | DFW Digital Twin</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown("**Storm Event**")
        st.markdown("🌪️ DFW_STORM_24")
    
    with col2:
        st.markdown("**MOE State**")
        moe_class = st.session_state.moe_state.lower().replace('_', '-')
        st.markdown(f'<span class="moe-badge moe-{moe_class.split("-")[1]}">{st.session_state.moe_state}</span>', unsafe_allow_html=True)
    
    with col3:
        st.markdown("**Operational Score**")
        score = st.session_state.operational_score
        color = "🟢" if score > 70 else "🟡" if score > 40 else "🔴"
        st.markdown(f"{color} **{score}/100**")
    
    with col4:
        st.markdown("**Active Sectors**")
        st.markdown("**12** / 18 DFW")
    
    with col5:
        st.markdown("**Environment**")
        st.markdown("🟢 **PROD**")

# Pane A: Market Observability
def render_market_observability():
    st.markdown("### 📊 Market Observability")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Impact Zones", "127", "+12 (1h)")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("High-SII Properties", "342", "+28")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Expected Claims", "89", "±12")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Pipeline Value", "$2.1M", "+$340K")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sector breakdown
    sectors = pd.DataFrame({
        'Sector': ['Frisco', 'Plano', 'McKinney', 'Allen', 'Richardson'],
        'Score': [87, 73, 68, 62, 54],
        'State': ['S2_IMPACT', 'S3_RECOVERY', 'S2_IMPACT', 'S1_RISK', 'S0_BASELINE'],
        'Properties': [892, 1240, 678, 543, 421],
        'Expected_Claims': [24, 18, 15, 8, 3]
    })
    
    fig = px.bar(sectors, x='Sector', y='Score', color='State',
                 title="Sector Operational Scores",
                 color_discrete_map={
                     'S2_IMPACT': '#ef4444',
                     'S3_RECOVERY': '#f97316',
                     'S1_RISK': '#eab308',
                     'S0_BASELINE': '#22c55e'
                 })
    st.plotly_chart(fig, use_container_width=True)

# Pane B: Field Operations Map
def render_field_operations():
    st.markdown("### 🗺️ Field Operations Map")
    
    # Map controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.selectbox("Overlay", ["Hail Intensity", "SII Heatmap", "MOE States", "Route Density"])
    
    with col2:
        st.number_input("Min SII", 0, 100, 60)
    
    with col3:
        st.multiselect("Sectors", ["Frisco", "Plano", "McKinney"], default=["Frisco"])
    
    # Simulated map data
    df_props = pd.read_sql_query("""
        SELECT zip, COUNT(*) as count, AVG(roof_age) as avg_age
        FROM properties
        GROUP BY zip
        LIMIT 10
    """, engine)
    
    if not df_props.empty:
        fig = px.scatter(df_props, x='zip', y='count', size='avg_age',
                        title="Property Distribution (1km² blocks)",
                        labels={'count': 'Properties', 'avg_age': 'Avg Roof Age'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Parcel detail
    with st.expander("📍 Selected Parcel: 123 Main St, Frisco 75034"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("SII", "87", "High Risk")
        with col2:
            st.metric("Hail Size", "2.8\"", "50mm")
        with col3:
            st.metric("Roof Age", "18 yrs", "Asphalt")
        
        st.markdown("**CRM Status:** Lead → Contacted (2h ago)")
        st.markdown("**MOE Trajectory:** S2_IMPACT → S3_RECOVERY (est. 6h)")

# Pane C: Agentic Control Rail
def render_agentic_control():
    st.markdown("### 🤖 Agentic Control Rail")
    
    proposals = [
        {
            'id': 'P001',
            'title': '🚗 Deploy Frisco-Alpha Route',
            'description': '18 high-SII properties, est. $340K pipeline',
            'preconditions': '✅ All met',
            'blast_radius': 'Low (1 crew, 4h)',
            'expected_value': '+$340K',
            'action': 'create_route'
        },
        {
            'id': 'P002',
            'title': '📱 Launch "Recovery Window" SMS Campaign',
            'description': 'Target 127 past customers in impact zones',
            'preconditions': '✅ All met',
            'blast_radius': 'Medium (127 contacts)',
            'expected_value': '+$180K',
            'action': 'send_sms'
        },
        {
            'id': 'P003',
            'title': '⚠️ SLA Breach Alert',
            'description': '3 leads >15min without contact',
            'preconditions': '⚠️ Breach active',
            'blast_radius': 'Low (3 leads)',
            'expected_value': 'Risk mitigation',
            'action': 'alert'
        }
    ]
    
    for prop in proposals:
        st.markdown(f"""
        <div class="proposal-card">
            <h4 style="margin: 0 0 0.5rem 0;">{prop['title']}</h4>
            <p style="margin: 0 0 0.5rem 0; font-size: 0.875rem;">{prop['description']}</p>
            <div style="display: flex; gap: 1rem; font-size: 0.75rem; color: #64748b;">
                <span>Preconditions: {prop['preconditions']}</span>
                <span>Blast Radius: {prop['blast_radius']}</span>
                <span>Expected Value: {prop['expected_value']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("✅ Approve", key=f"approve_{prop['id']}"):
                st.success(f"Executing {prop['id']}...")
        with col2:
            if st.button("✏️ Amend", key=f"amend_{prop['id']}"):
                st.info("Opening amendment dialog...")
        with col3:
            pass

# Main layout
def main():
    render_sovereign_header()
    st.divider()
    
    # Three-pane layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_market_observability()
        st.divider()
        render_field_operations()
    
    with col2:
        render_agentic_control()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.75rem;">
        StormOps v2.0 | Physics-Native Control Plane | Powered by NVIDIA Earth-2 Digital Twin
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
