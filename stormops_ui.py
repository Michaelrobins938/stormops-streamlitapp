"""
StormOps v1 Minimal UI
Three-button interface: Generate Leads, Build Routes, Send SMS
"""

import streamlit as st
import psycopg2
from datetime import datetime
import logging

from proposal_engine import ProposalEngine
from route_optimizer import RouteOptimizer
from crm_integration import MockCRMIntegration
from moe import MarkovOpportunityEngine
from impact_report_generator import ImpactReportGenerator
from sla_monitor import SLAMonitor
from forecast_monitor import ForecastMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(page_title="StormOps v1", layout="wide", initial_sidebar_state="auto")

# Database config
DB_HOST = 'localhost'
DB_NAME = 'stormops'
DB_USER = 'postgres'
DB_PASSWORD = 'password'

# Initialize session state
if 'event_id' not in st.session_state:
    st.session_state.event_id = None
if 'zip_code' not in st.session_state:
    st.session_state.zip_code = '75034'
if 'proposals' not in st.session_state:
    st.session_state.proposals = []

# Header
st.title("🌪️ StormOps v1 – DFW Storm Control Plane")
st.markdown("**Physics-native lead generation and route optimization for hail events**")

# Sidebar
with st.sidebar:
    st.markdown("### Configuration")
    
    # Event selector
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, peak_hail_inches FROM events WHERE status = 'active' ORDER BY event_date DESC LIMIT 10")
        events = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if events:
            event_names = [f"{e[1]} ({e[2]}\" hail)" for e in events]
            selected_idx = st.selectbox("Select Event", range(len(events)), format_func=lambda i: event_names[i])
            st.session_state.event_id = events[selected_idx][0]
        else:
            st.warning("No active events found")
    except Exception as e:
        st.error(f"Database error: {e}")
    
    # ZIP code selector
    st.session_state.zip_code = st.text_input("Target ZIP Code", value=st.session_state.zip_code)
    
    # SII thresholds
    sii_min = st.slider("Min SII Score", 0, 100, 60)
    sii_max = st.slider("Max SII Score", 0, 100, 100)
    
    st.markdown("---")
    st.markdown("### Quick Stats")
    
    if st.session_state.event_id:
        try:
            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
            )
            cursor = conn.cursor()
            
            # Event stats
            cursor.execute("""
                SELECT peak_hail_inches, max_wind_mph, estimated_value_usd
                FROM events WHERE id = %s
            """, (st.session_state.event_id,))
            event = cursor.fetchone()
            
            if event:
                st.metric("Peak Hail", f"{event[0]}\"")
                st.metric("Max Wind", f"{event[1]} mph")
                st.metric("Est. Value", f"${event[2]:,.0f}")
            
            # Parcel stats
            cursor.execute("""
                SELECT COUNT(*) FROM impact_scores is
                JOIN parcels p ON is.parcel_id = p.id
                WHERE is.event_id = %s AND p.zip_code = %s AND is.sii_score >= %s
            """, (st.session_state.event_id, st.session_state.zip_code, sii_min))
            
            parcel_count = cursor.fetchone()[0]
            st.metric("Parcels (SII >= " + str(sii_min) + ")", parcel_count)
            
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Error loading stats: {e}")

# Main content
if not st.session_state.event_id:
    st.warning("Please select an event from the sidebar")
else:
    # Three-column layout for main actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 1️⃣ Generate Leads")
        st.markdown(f"Create leads for {st.session_state.zip_code} with SII ≥ {sii_min}")
        
        if st.button("Generate Leads Now", key="btn_gen_leads"):
            with st.spinner("Generating leads..."):
                try:
                    engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
                    engine.connect()
                    
                    proposal_id = engine.generate_lead_gen_proposal(
                        event_id=st.session_state.event_id,
                        zip_code=st.session_state.zip_code,
                        sii_min=sii_min,
                        sii_max=sii_max,
                    )
                    
                    if proposal_id:
                        st.success(f"✅ Lead gen proposal created: {proposal_id}")
                        st.session_state.proposals.append(proposal_id)
                    else:
                        st.error("Failed to create proposal")
                    
                    engine.close()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col2:
        st.markdown("### 2️⃣ Build Routes")
        st.markdown(f"Optimize 4 canvassing routes for {st.session_state.zip_code}")
        
        if st.button("Build Routes Now", key="btn_build_routes"):
            with st.spinner("Building routes..."):
                try:
                    optimizer = RouteOptimizer(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
                    optimizer.connect()
                    
                    route_ids = optimizer.build_routes(
                        event_id=st.session_state.event_id,
                        zip_code=st.session_state.zip_code,
                        sii_min=sii_min,
                        num_canvassers=4,
                    )
                    
                    if route_ids:
                        st.success(f"✅ Built {len(route_ids)} routes")
                        for rid in route_ids:
                            st.caption(f"Route: {rid}")
                    else:
                        st.error("Failed to build routes")
                    
                    optimizer.close()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col3:
        st.markdown("### 3️⃣ Send SMS")
        st.markdown(f"Trigger SMS campaign to past customers in {st.session_state.zip_code}")
        
        if st.button("Send SMS Campaign", key="btn_send_sms"):
            with st.spinner("Sending SMS..."):
                try:
                    engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
                    engine.connect()
                    
                    proposal_id = engine.generate_sms_campaign_proposal(
                        event_id=st.session_state.event_id,
                        zip_code=st.session_state.zip_code,
                        segment='past_customers',
                    )
                    
                    if proposal_id:
                        st.success(f"✅ SMS campaign proposal created: {proposal_id}")
                        st.session_state.proposals.append(proposal_id)
                    else:
                        st.error("Failed to create SMS proposal")
                    
                    engine.close()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # Tabs for different views
    tab_proposals, tab_intelligence, tab_quality, tab_forecast = st.tabs(
        ["📋 Proposals", "🧠 Operational Intelligence", "📊 Quality Monitor", "🌤️ Forecast"]
    )
    
    # Proposals tab
    with tab_proposals:
        st.markdown("### Proposal Queue")
        
        try:
            engine = ProposalEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
            engine.connect()
            
            proposals = engine.list_proposals(st.session_state.event_id, status='pending')
            
            if proposals:
                for prop in proposals:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{prop['type'].upper()}**")
                    
                    with col2:
                        st.write(f"ZIP: {prop['target_zip']}")
                    
                    with col3:
                        st.write(f"Est. Value: ${prop['expected_value']:,.0f}")
                    
                    with col4:
                        if st.button("Approve", key=f"approve_{prop['id']}"):
                            engine.approve_proposal(prop['id'])
                            st.rerun()
            else:
                st.info("No pending proposals")
            
            engine.close()
        except Exception as e:
            st.error(f"Error loading proposals: {e}")
    
    # Operational Intelligence tab
    with tab_intelligence:
        st.markdown("### Markov Opportunity Engine (MOE)")
        
        try:
            moe = MarkovOpportunityEngine(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
            moe.connect()
            
            # Get operational score
            op_score = moe.get_operational_score(st.session_state.event_id)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Operational Score", f"{op_score:.0f}/100")
            with col2:
                st.metric("Phase", "Impact" if op_score > 50 else "Risk" if op_score > 20 else "Baseline")
            with col3:
                st.metric("Surge Multiplier", "1.5x" if op_score > 60 else "1.2x" if op_score > 40 else "1.0x")
            
            st.markdown("---")
            st.markdown("### Impact Reports")
            
            # Generate impact reports
            if st.button("Generate Impact Reports (SII >= 75)"):
                with st.spinner("Generating reports..."):
                    gen = ImpactReportGenerator(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
                    gen.connect()
                    count = gen.generate_batch_reports(st.session_state.event_id, sii_min=75)
                    st.success(f"Generated {count} impact reports")
                    gen.close()
            
            moe.close()
        except Exception as e:
            st.error(f"Error: {e}")
    
    # Quality Monitor tab
    with tab_quality:
        st.markdown("### SLA & Quality Metrics")
        
        try:
            monitor = SLAMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
            monitor.connect()
            
            # Dashboard metrics
            metrics = monitor.get_dashboard_metrics(st.session_state.event_id)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Leads", metrics.get('total_leads', 0))
            with col2:
                st.metric("Contacted", f"{metrics.get('contacted_leads', 0)} ({metrics.get('contact_rate', 0)}%)")
            with col3:
                st.metric("Inspected", metrics.get('inspected_leads', 0))
            with col4:
                st.metric("Closed", f"{metrics.get('closed_leads', 0)} ({metrics.get('close_rate', 0)}%)")
            
            st.markdown("---")
            st.metric("Total Claim Value", f"${metrics.get('total_claim_value', 0):,.0f}")
            
            st.markdown("---")
            st.markdown("### SLA Breaches")
            
            breaches = monitor.check_sla_breaches(st.session_state.event_id)
            if breaches:
                st.warning(f"⚠️ {len(breaches)} SLA breaches detected")
                for breach in breaches[:5]:
                    st.caption(f"{breach['address']}: {breach['minutes_elapsed']} min (SLA: {breach['sla_threshold']} min)")
            else:
                st.success("✅ No SLA breaches")
            
            st.markdown("---")
            st.markdown("### Claim Acceptance Impact")
            
            acceptance = monitor.get_claim_acceptance_rate(st.session_state.event_id)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("With Reports", f"{acceptance.get('acceptance_rate_with_reports', 0)}%")
            with col2:
                st.metric("Without Reports", f"{acceptance.get('acceptance_rate_without_reports', 0)}%")
            with col3:
                st.metric("Lift", f"+{acceptance.get('lift_from_reports', 0)}%")
            
            monitor.close()
        except Exception as e:
            st.error(f"Error: {e}")
    
    # Forecast tab
    with tab_forecast:
        st.markdown("### 7-Day Forecast Monitoring")
        
        try:
            fm = ForecastMonitor(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)
            
            # Mock 7-day forecast
            forecast_data = [
                {'day': 1, 'severe_probability': 0.02, 'hail_probability': 0.01, 'max_wind_mph': 15},
                {'day': 2, 'severe_probability': 0.05, 'hail_probability': 0.03, 'max_wind_mph': 20},
                {'day': 3, 'severe_probability': 0.25, 'hail_probability': 0.30, 'max_wind_mph': 55},
                {'day': 4, 'severe_probability': 0.10, 'hail_probability': 0.08, 'max_wind_mph': 25},
                {'day': 5, 'severe_probability': 0.02, 'hail_probability': 0.01, 'max_wind_mph': 15},
                {'day': 6, 'severe_probability': 0.01, 'hail_probability': 0.00, 'max_wind_mph': 10},
                {'day': 7, 'severe_probability': 0.03, 'hail_probability': 0.02, 'max_wind_mph': 12},
            ]
            
            # Get summary
            summary = fm.get_7day_forecast_summary(forecast_data)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Days with Severe", summary['days_with_severe'])
            with col2:
                st.metric("Days with Hail", summary['days_with_hail'])
            with col3:
                st.metric("Peak Wind", f"{summary['peak_wind_mph']} mph")
            
            st.markdown("---")
            st.markdown("### Forecast Alerts")
            
            all_alerts = []
            for day_forecast in forecast_data:
                alerts = fm.check_forecast_alerts(st.session_state.event_id, day_forecast)
                all_alerts.extend(alerts)
            
            if all_alerts:
                st.warning(f"⚠️ {len(all_alerts)} forecast alerts")
                for alert in all_alerts:
                    st.caption(f"**{alert['type'].upper()}**: {alert['message']}")
            else:
                st.success("✅ No forecast alerts")
            
            st.markdown("---")
            st.markdown(f"**Operational Window**: {summary['operational_window']}")
        
        except Exception as e:
            st.error(f"Error: {e}")
