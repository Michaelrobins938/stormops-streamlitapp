"""
StormOps Tactical Control Plane
Military-grade industrial interface
"""
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.graph_objects as go
from datetime import datetime
from copilot import render_copilot
from theme import get_theme_css

engine = create_engine('sqlite:///stormops_cache.db')

st.set_page_config(
    page_title="StormOps Tactical",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(get_theme_css(), unsafe_allow_html=True)

# Using shared theme from theme.py

def render_header():
    st.markdown("""
    <div class="tactical-header">
        <div class="header-title">STORMOPS TACTICAL</div>
        <div class="header-meta">
            <div class="header-meta-item">
                <div class="header-meta-label">EVENT</div>
                <div class="header-meta-value">DFW_STORM_24</div>
            </div>
            <div class="header-meta-item">
                <div class="header-meta-label">STATE</div>
                <div class="header-meta-value status-critical">S2_IMPACT</div>
            </div>
            <div class="header-meta-item">
                <div class="header-meta-label">SCORE</div>
                <div class="header-meta-value">73/100</div>
            </div>
            <div class="header-meta-item">
                <div class="header-meta-label">SECTORS</div>
                <div class="header-meta-value">12 ACTIVE</div>
            </div>
            <div class="header-meta-item">
                <div class="header-meta-label">ENV</div>
                <div class="header-meta-value status-live">PROD</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_metrics():
    st.markdown("""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">IMPACT ZONES</div>
            <div class="metric-value">127</div>
            <div class="metric-delta">↑ 12 (1H)</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">HIGH-SII PROPERTIES</div>
            <div class="metric-value">342</div>
            <div class="metric-delta">↑ 28</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">EXPECTED CLAIMS</div>
            <div class="metric-value">89</div>
            <div class="metric-delta">± 12</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">PIPELINE VALUE</div>
            <div class="metric-value">$2.1M</div>
            <div class="metric-delta">↑ $340K</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_proposals():
    proposals = [
        {
            'id': 'P001',
            'title': 'DEPLOY FRISCO-ALPHA ROUTE',
            'body': '18 high-SII properties, 4h window, est. $340K pipeline',
            'preconditions': 'ALL MET',
            'blast': 'LOW (1 CREW)',
            'value': '+$340K'
        },
        {
            'id': 'P002',
            'title': 'LAUNCH RECOVERY SMS CAMPAIGN',
            'body': '127 past customers in impact zones, 24h optimal window',
            'preconditions': 'ALL MET',
            'blast': 'MEDIUM (127 CONTACTS)',
            'value': '+$180K'
        },
        {
            'id': 'P003',
            'title': 'SLA BREACH ALERT',
            'body': '3 leads >15min without contact, immediate action required',
            'preconditions': 'BREACH ACTIVE',
            'blast': 'LOW (3 LEADS)',
            'value': 'RISK MITIGATION'
        }
    ]
    
    for p in proposals:
        st.markdown(f"""
        <div class="proposal">
            <div class="proposal-header">
                <div class="proposal-title">{p['title']}</div>
                <div class="proposal-id">{p['id']}</div>
            </div>
            <div class="proposal-body">{p['body']}</div>
            <div class="proposal-meta">
                <span>PRECONDITIONS: {p['preconditions']}</span>
                <span>BLAST: {p['blast']}</span>
                <span>VALUE: {p['value']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            st.button("APPROVE", key=f"app_{p['id']}", type="primary")
        with col2:
            st.button("AMEND", key=f"amd_{p['id']}")

def render_sectors():
    sectors = pd.DataFrame({
        'SECTOR': ['FRISCO', 'PLANO', 'MCKINNEY', 'ALLEN', 'RICHARDSON'],
        'SCORE': [87, 73, 68, 62, 54],
        'STATE': ['S2_IMPACT', 'S3_RECOVERY', 'S2_IMPACT', 'S1_RISK', 'S0_BASELINE'],
        'PROPS': [892, 1240, 678, 543, 421],
        'CLAIMS': [24, 18, 15, 8, 3]
    })
    
    fig = go.Figure()
    
    colors = {
        'S2_IMPACT': '#ef4444',
        'S3_RECOVERY': '#f97316',
        'S1_RISK': '#eab308',
        'S0_BASELINE': '#22c55e'
    }
    
    for state in sectors['STATE'].unique():
        df_state = sectors[sectors['STATE'] == state]
        fig.add_trace(go.Bar(
            x=df_state['SECTOR'],
            y=df_state['SCORE'],
            name=state,
            marker_color=colors[state],
            text=df_state['SCORE'],
            textposition='outside'
        ))
    
    fig.update_layout(
        title='SECTOR OPERATIONAL SCORES',
        plot_bgcolor='#0f172a',
        paper_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', family='monospace', size=10),
        xaxis=dict(gridcolor='#334155', title=''),
        yaxis=dict(gridcolor='#334155', title='SCORE', range=[0, 100]),
        showlegend=True,
        legend=dict(bgcolor='#1e293b', bordercolor='#334155', borderwidth=1),
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_map_controls():
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.selectbox("OVERLAY", ["HAIL INTENSITY", "SII HEATMAP", "MOE STATES", "ROUTE DENSITY"], label_visibility="visible")
    
    with col2:
        st.number_input("MIN SII", 0, 100, 60, label_visibility="visible")
    
    with col3:
        st.multiselect("SECTORS", ["FRISCO", "PLANO", "MCKINNEY"], default=["FRISCO"], label_visibility="visible")
    
    with col4:
        st.button("REFRESH MAP", type="primary", use_container_width=True)

def main():
    render_header()
    
    # Two-column layout
    col_main, col_rail = st.columns([2, 1])
    
    with col_main:
        render_metrics()
        
        st.markdown("### SECTOR STATUS")
        render_sectors()
        
        st.markdown("### TACTICAL MAP")
        render_map_controls()
        
        # Map placeholder
        df_props = pd.read_sql_query("""
            SELECT zip, COUNT(*) as count
            FROM properties
            GROUP BY zip
            LIMIT 10
        """, engine)
        
        if not df_props.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_props['zip'],
                y=df_props['count'],
                mode='markers',
                marker=dict(size=15, color='#0ea5e9', line=dict(width=1, color='#0284c7')),
                text=df_props['zip'],
                textposition='top center'
            ))
            
            fig.update_layout(
                plot_bgcolor='#0f172a',
                paper_bgcolor='#1e293b',
                font=dict(color='#e2e8f0', family='monospace', size=10),
                xaxis=dict(gridcolor='#334155', title='ZIP CODE'),
                yaxis=dict(gridcolor='#334155', title='PROPERTIES'),
                margin=dict(l=40, r=40, t=20, b=40),
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Copilot integration
        st.markdown("### TACTICAL COPILOT")
        render_copilot()
    
    with col_rail:
        st.markdown("### AGENTIC CONTROL")
        render_proposals()

if __name__ == "__main__":
    main()
