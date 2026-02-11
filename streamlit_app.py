"""
Streamlit Sharing Compatible Version of StormOps
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import json
import uuid
import plotly.express as px
import plotly.graph_objects as go

# Use in-memory SQLite database for Streamlit Sharing compatibility
from sqlalchemy import create_engine, text

# Create in-memory database
@st.cache_resource
def get_engine():
    # Using in-memory SQLite database for Streamlit Sharing
    return create_engine("sqlite+pysqlite:///:memory:", echo=True)

# Initialize the database with sample data
@st.cache_resource
def init_db():
    engine = get_engine()
    with engine.connect() as conn:
        trans = conn.begin()
        # Create tables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT UNIQUE,
                org_name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS storms (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                storm_type TEXT,
                severity TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                affected_zips TEXT,
                tenant_id TEXT DEFAULT 'demo-tenant',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS earth2_impact_zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id TEXT UNIQUE,
                storm_id TEXT,
                zip_code TEXT NOT NULL,
                hail_size_inches REAL DEFAULT 0,
                wind_speed_mph REAL DEFAULT 0,
                damage_propensity_score REAL DEFAULT 0,
                estimated_roofs INTEGER DEFAULT 0,
                lead_value DECIMAL(12,2) DEFAULT 0,
                risk_level TEXT DEFAULT 'Medium',
                latitude REAL,
                longitude REAL,
                center_lat REAL DEFAULT 0,
                center_lon REAL DEFAULT 0
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id TEXT UNIQUE,
                storm_id TEXT,
                address TEXT,
                city TEXT,
                zip_code TEXT,
                hail_size REAL,
                roof_age INTEGER,
                property_value DECIMAL(12,2),
                lead_score REAL DEFAULT 0,
                conversion_probability REAL DEFAULT 0,
                priority_tier TEXT DEFAULT 'C',
                trigger_description TEXT,
                phone TEXT,
                email TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_contact TIMESTAMP,
                persona TEXT DEFAULT 'realist',
                voice_ready BOOLEAN DEFAULT 0,
                ai_confidence REAL DEFAULT 0,
                ai_reasoning TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT UNIQUE,
                storm_id TEXT,
                tenant_id TEXT,
                name TEXT,
                zip_code TEXT,
                property_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                assigned_crew TEXT,
                total_doors INTEGER DEFAULT 0,
                completed_doors INTEGER DEFAULT 0,
                estimated_value DECIMAL(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                lead_id INTEGER,
                route_id INTEGER,
                address TEXT,
                status TEXT DEFAULT 'pending',
                claim_amount DECIMAL(12,2) DEFAULT 0,
                damage_type TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """))
        
        # Insert sample data
        conn.execute(text("""
            INSERT OR IGNORE INTO tenants (tenant_id, org_name, status) 
            VALUES ('demo-tenant', 'Demo Roofing Company', 'active')
        """))
        
        conn.execute(text("""
            INSERT OR IGNORE INTO storms (id, name, status, storm_type, severity, affected_zips, tenant_id)
            VALUES ('demo-storm', 'DFW Storm-24', 'active', 'hail', 'severe', '75001,75002,75007,75010,75024,75034,75035,75093,75201,75204,75205,75225,75230,75234,75240,75248,75287', 'demo-tenant')
        """))
        
        # Add more sample data as needed
        trans.commit()
    return engine

# Initialize database
engine = init_db()

# Set page config
st.set_page_config(
    page_title="StormOps | Demo Version",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">StormOps v2.0.0 - Demo</div>', unsafe_allow_html=True)

# Main dashboard
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric(label="Active Storms", value=1, delta=0)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric(label="Total Leads", value=24, delta=5)
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric(label="Active Routes", value=7, delta=2)
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric(label="Completion Rate", value="45%", delta="5%")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["Overview", "Leads", "Routes"])

with tab1:
    st.subheader("Storm Impact Overview")
    
    # Sample data for visualization
    df_impact = pd.DataFrame({
        'Zip Code': ['75201', '75204', '75024', '75230', '75240'],
        'Hail Size (in)': [2.5, 2.1, 2.25, 2.375, 2.0],
        'Damage Probability': [0.95, 0.89, 0.91, 0.93, 0.88],
        'Estimated Value': [71736, 55228, 54252, 68288, 53625]
    })
    
    fig = px.scatter(df_impact, x='Hail Size (in)', y='Damage Probability', 
                     size='Estimated Value', color='Zip Code',
                     title='Storm Impact Analysis')
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Recent Leads")
    
    # Get leads data
    with engine.connect() as conn:
        leads_df = pd.read_sql("SELECT * FROM leads LIMIT 10", conn)
    
    if not leads_df.empty:
        st.dataframe(leads_df[['lead_id', 'address', 'city', 'zip_code', 'lead_score', 'status']], 
                     use_container_width=True)
    else:
        st.info("No leads data available in the demo database")

with tab3:
    st.subheader("Active Routes")
    
    # Get routes data
    with engine.connect() as conn:
        routes_df = pd.read_sql("SELECT * FROM routes LIMIT 10", conn)
    
    if not routes_df.empty:
        st.dataframe(routes_df[['route_id', 'name', 'status', 'total_doors', 'estimated_value']], 
                     use_container_width=True)
    else:
        st.info("No routes data available in the demo database")

# Footer
st.divider()
st.caption("Demo version for Streamlit Sharing - Data is reset on each rerun")