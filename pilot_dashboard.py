"""
Pilot Dashboard - Track onboarding and success metrics for pilot tenants
Run with: streamlit run pilot_dashboard.py
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import plotly.graph_objects as go

st.set_page_config(page_title="StormOps Pilot Dashboard", layout="wide")

# Connect to DB
engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

st.title("🚀 StormOps Pilot Dashboard")

# Get all pilot tenants
with engine.connect() as conn:
    pilots = pd.read_sql("""
        SELECT 
            t.tenant_id,
            t.org_name,
            t.pilot_start_date,
            t.tier,
            t.status,
            COUNT(DISTINCT s.storm_id) as storms,
            COUNT(DISTINCT r.route_id) as routes,
            COUNT(DISTINCT j.job_id) as total_jobs,
            SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END) as completed_jobs
        FROM tenants t
        LEFT JOIN storms s ON t.tenant_id = s.tenant_id
        LEFT JOIN routes r ON t.tenant_id = r.tenant_id
        LEFT JOIN jobs j ON t.tenant_id = j.tenant_id
        WHERE t.tier = 'pilot' AND t.status = 'active'
        GROUP BY t.tenant_id, t.org_name, t.pilot_start_date, t.tier, t.status
        ORDER BY t.pilot_start_date DESC
    """, conn)

if len(pilots) == 0:
    st.info("No active pilots. Create one below.")
    
    with st.form("new_pilot"):
        st.subheader("Create New Pilot")
        org_name = st.text_input("Organization Name")
        contact_email = st.text_input("Contact Email")
        contact_name = st.text_input("Contact Name")
        
        if st.form_submit_button("Create Pilot"):
            import uuid
            tenant_id = uuid.uuid4()
            
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO tenants 
                    (tenant_id, org_name, contact_email, contact_name, status, tier, pilot_start_date)
                    VALUES (:tid, :org, :email, :name, 'active', 'pilot', NOW())
                """), {
                    'tid': tenant_id,
                    'org': org_name,
                    'email': contact_email,
                    'name': contact_name
                })
            
            st.success(f"✅ Created pilot for {org_name}")
            st.rerun()

else:
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Pilots", len(pilots))
    col2.metric("Total Storms", pilots['storms'].sum())
    col3.metric("Total Routes", pilots['routes'].sum())
    col4.metric("Jobs Completed", pilots['completed_jobs'].sum())
    
    st.divider()
    
    # Pilot details
    for _, pilot in pilots.iterrows():
        with st.expander(f"📊 {pilot['org_name']}", expanded=True):
            # Calculate days in pilot
            if pilot['pilot_start_date']:
                days = (datetime.now() - pilot['pilot_start_date']).days
            else:
                days = 0
            
            # Metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Days in Pilot", days)
            col2.metric("Storms", pilot['storms'])
            col3.metric("Routes", pilot['routes'])
            col4.metric("Total Jobs", pilot['total_jobs'])
            col5.metric("Completed", pilot['completed_jobs'])
            
            # Get detailed metrics
            with engine.connect() as conn:
                # Outcomes
                outcomes = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN actual_converted THEN 1 ELSE 0 END) as converted,
                        AVG(conversion_value) as avg_value
                    FROM policy_outcomes
                    WHERE tenant_id = :tid
                """), {'tid': pilot['tenant_id']}).fetchone()
                
                # Recent activity
                activity = conn.execute(text("""
                    SELECT COUNT(*) FROM tenant_usage
                    WHERE tenant_id = :tid 
                      AND created_at > NOW() - INTERVAL '7 days'
                """), {'tid': pilot['tenant_id']}).fetchone()[0]
            
            # Conversion metrics
            if outcomes[0] > 0:
                conv_rate = (outcomes[1] / outcomes[0] * 100) if outcomes[0] else 0
                avg_value = outcomes[2] or 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Conversion Rate", f"{conv_rate:.1f}%")
                col2.metric("Avg Claim Value", f"${avg_value:,.0f}")
                col3.metric("7-Day Activity", activity)
            
            # Health score
            health = 0
            if activity > 5:
                health += 40
            if pilot['storms'] > 0:
                health += 20
            if pilot['routes'] > 0:
                health += 20
            if pilot['completed_jobs'] > 5:
                health += 20
            
            # Health indicator
            if health >= 80:
                st.success(f"🟢 Health Score: {health}/100 - Excellent")
            elif health >= 50:
                st.warning(f"🟡 Health Score: {health}/100 - Good")
            else:
                st.error(f"🔴 Health Score: {health}/100 - Needs Attention")
            
            # Actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"View Details", key=f"view_{pilot['tenant_id']}"):
                    st.info(f"Tenant ID: {pilot['tenant_id']}")
            with col2:
                if st.button(f"Send Update", key=f"email_{pilot['tenant_id']}"):
                    st.success(f"Email sent to {pilot['org_name']}")

st.divider()

# Pilot success criteria
st.subheader("📈 Success Criteria")

criteria = {
    "Routes per Storm": {"target": 3, "current": pilots['routes'].sum() / max(pilots['storms'].sum(), 1)},
    "Jobs Completed": {"target": 50, "current": pilots['completed_jobs'].sum()},
    "Completion Rate": {"target": 80, "current": (pilots['completed_jobs'].sum() / max(pilots['total_jobs'].sum(), 1) * 100)},
}

for metric, values in criteria.items():
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.write(f"**{metric}**")
    col2.metric("Target", f"{values['target']:.1f}")
    col3.metric("Current", f"{values['current']:.1f}", 
                delta=f"{values['current'] - values['target']:.1f}")
