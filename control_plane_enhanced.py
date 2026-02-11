"""
StormOps Control Plane UI - Enhanced with ML + GA4 Integration
Add this to your existing Streamlit app to wire the "Generate Leads" button
"""

import streamlit as st
from stormops_ui_integration import (
    generate_leads_physics_driven,
    execute_playbook,
    get_ui_dashboard_data,
    update_storm_play_score
)

# Add to your existing control_plane.py

def render_lead_generation_panel(event_id: str, current_zip: str):
    """Enhanced lead generation panel with SII + GA4 integration."""
    
    st.subheader("🎯 Lead Generation (Physics-Driven)")
    
    # Show current context
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current ZIP", current_zip)
    with col2:
        st.metric("Event", event_id)
    with col3:
        playbook = st.selectbox("Playbook", ["frisco-alpha", "loyalty-dfw-highses", "expansion-lookalike"])
    
    # SII threshold slider
    min_sii = st.slider(
        "Minimum SII Score (ML-powered)",
        min_value=0,
        max_value=100,
        value=70,
        help="Properties below this Storm Impact Index score will be filtered out. Powered by XGBoost model."
    )
    
    # Show what this threshold means
    st.caption(f"✓ SII ≥ {min_sii}: Physics predicts significant damage likelihood")
    
    # Advanced filters (collapsible)
    with st.expander("Advanced Filters"):
        require_ga4_intent = st.checkbox(
            "Require GA4 high-intent signals",
            value=False,
            help="Only include properties with recent estimate tool usage, quote starts, or call clicks"
        )
        
        min_income = st.number_input("Min Median Income", value=0, step=10000)
        
        personas = st.multiselect(
            "Target Personas",
            ["Proof_Seeker", "Family_Protector", "Deal_Hunter", "Status_Conscious", "Procrastinator"],
            default=[]
        )
    
    # Generate leads button
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Generate Leads Now", type="primary", use_container_width=True):
            with st.spinner("Running SII model + GA4 intent analysis..."):
                result = generate_leads_physics_driven(
                    zip_code=current_zip,
                    min_sii_score=min_sii,
                    event_id=event_id,
                    playbook_id=playbook
                )
                
                st.success(f"✅ Generated {result['total_leads']} leads!")
                
                # Show tiered breakdown
                st.markdown("### Lead Tiers")
                tier_col1, tier_col2, tier_col3 = st.columns(3)
                
                with tier_col1:
                    st.metric(
                        "🥇 Tier A",
                        result['tier_a'],
                        help="SII ≥ 80 + GA4 high-intent"
                    )
                
                with tier_col2:
                    st.metric(
                        "🥈 Tier B",
                        result['tier_b'],
                        help="SII 70-79"
                    )
                
                with tier_col3:
                    st.metric(
                        "🥉 Tier C",
                        result['tier_c'],
                        help="SII 60-69"
                    )
                
                # Show key metrics
                st.markdown("### Metrics")
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                
                with metric_col1:
                    st.metric("Avg SII Score", f"{result['avg_sii_score']:.1f}")
                
                with metric_col2:
                    st.metric("Total MOE", f"${result['total_moe']:,.0f}")
                
                with metric_col3:
                    st.metric("High-Intent Web", result['high_intent_count'])
                
                # Show proposals created
                st.info(f"📋 Created {result['proposals_created']} proposals tagged with playbook '{playbook}'")
                
                # Attribution note
                st.caption("✓ All leads tagged for GA4 offline conversion tracking")
    
    with col2:
        if st.button("🎮 Execute Full Playbook", use_container_width=True):
            with st.spinner(f"Executing {playbook} across multiple ZIPs..."):
                # Get ZIPs from playbook config
                zip_codes = ["75034", "75035"]  # From playbook targeting rules
                
                execution = execute_playbook(
                    playbook_id=playbook,
                    event_id=event_id,
                    zip_codes=zip_codes
                )
                
                st.success(f"✅ Playbook execution started!")
                
                st.markdown(f"**Execution ID:** `{execution['execution_id']}`")
                st.markdown(f"**Total Leads:** {execution['total_leads']}")
                st.markdown(f"**Tier A Leads:** {execution['tier_a_leads']}")
                st.markdown(f"**High-Intent:** {execution['high_intent_leads']}")
                st.markdown(f"**ZIPs:** {', '.join(execution['zip_codes'])}")
                
                st.info("🔄 Attribution tracking active. Conversions will sync to Google Ads nightly.")


def render_enhanced_dashboard(event_id: str):
    """Enhanced dashboard with ML-powered metrics."""
    
    # Update Storm Play Score
    play_score = update_storm_play_score(event_id)
    
    # Get dashboard data
    dashboard = get_ui_dashboard_data(event_id)
    
    # Header metrics
    st.markdown("## 📊 Storm Intelligence Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Storm Play Score",
            f"{play_score:.0f}/100",
            delta=f"+{play_score - 50:.0f}" if play_score > 50 else None,
            help="ML-powered composite score: Physics (50%) + Web Intent (30%) + Coverage (20%)"
        )
    
    with col2:
        st.metric(
            "Impacted Roofs",
            f"{dashboard['impact']['total_properties']:,}",
            help="Properties with SII scores calculated"
        )
    
    with col3:
        st.metric(
            "High SII (80+)",
            f"{dashboard['impact']['high_sii_count']:,}",
            help="Properties with severe damage likelihood"
        )
    
    with col4:
        st.metric(
            "Web Intent Signals",
            f"{dashboard['web_intent']['properties_with_intent']:,}",
            help="Properties with recent high-intent GA4 events"
        )
    
    # Physics metrics
    st.markdown("### ⚡ Physics Layer")
    phys_col1, phys_col2, phys_col3 = st.columns(3)
    
    with phys_col1:
        st.metric("Avg SII Score", f"{dashboard['impact']['avg_sii']:.1f}")
    
    with phys_col2:
        st.metric("Total MOE", f"${dashboard['impact']['total_moe']:,.0f}")
    
    with phys_col3:
        st.metric("Medium SII (60-79)", f"{dashboard['impact']['medium_sii_count']:,}")
    
    # Proposals status
    st.markdown("### 📋 Active Proposals")
    prop_col1, prop_col2, prop_col3, prop_col4 = st.columns(4)
    
    with prop_col1:
        st.metric("Total", dashboard['proposals']['total'])
    
    with prop_col2:
        st.metric("Pending", dashboard['proposals']['pending'])
    
    with prop_col3:
        st.metric("In Progress", dashboard['proposals']['in_progress'])
    
    with prop_col4:
        st.metric("Tier A", dashboard['proposals']['tier_a'])
    
    # Show data freshness
    st.caption("✓ SII scores updated nightly | GA4 data synced every 4 hours")


def render_attribution_panel():
    """Show attribution insights from GA4 + StormOps touches."""
    
    st.markdown("### 🎯 Attribution Insights")
    
    # Query recent conversions with attribution
    query = """
    SELECT 
        cj.customer_id,
        cj.conversion_date,
        cj.job_value_usd,
        cj.touchpoint_sequence,
        cj.top_channel_by_shapley,
        cj.top_channel_shapley_value,
        COUNT(DISTINCT wbe.event_name) as web_touchpoints,
        COUNT(DISTINCT be.channel) as stormops_touchpoints
    FROM customer_journeys cj
    LEFT JOIN web_behavior_events wbe ON cj.customer_id = wbe.customer_id
    LEFT JOIN behavior_events be ON cj.customer_id = be.customer_id
    WHERE cj.conversion_date > NOW() - INTERVAL '30 days'
    GROUP BY cj.customer_id, cj.conversion_date, cj.job_value_usd,
             cj.touchpoint_sequence, cj.top_channel_by_shapley, cj.top_channel_shapley_value
    ORDER BY cj.conversion_date DESC
    LIMIT 10
    """
    
    import pandas as pd
    from sqlalchemy import create_engine
    
    engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')
    df = pd.read_sql(query, engine)
    
    if len(df) > 0:
        st.dataframe(df, use_container_width=True)
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Conversions", len(df))
        
        with col2:
            st.metric("Total Revenue", f"${df['job_value_usd'].sum():,.0f}")
        
        with col3:
            top_channel = df['top_channel_by_shapley'].mode()[0] if len(df) > 0 else "N/A"
            st.metric("Top Channel", top_channel)
    else:
        st.info("No conversions in last 30 days. Attribution data will appear here once jobs are completed.")


# Add to main app
def main():
    st.set_page_config(page_title="StormOps Control Plane", layout="wide")
    
    st.title("⚡ StormOps Control Plane")
    st.caption("Physics → People → Money → Behavior → Causality")
    
    # Current event context
    event_id = "dfw_storm_24"
    current_zip = "75034"
    
    # Render enhanced dashboard
    render_enhanced_dashboard(event_id)
    
    st.markdown("---")
    
    # Lead generation panel
    render_lead_generation_panel(event_id, current_zip)
    
    st.markdown("---")
    
    # Attribution panel
    render_attribution_panel()
    
    # Sidebar: Playbook status
    with st.sidebar:
        st.markdown("### 🎮 Active Playbooks")
        
        playbooks = [
            {"name": "Frisco-Alpha", "status": "Running", "leads": 287, "conversions": 12},
            {"name": "Loyalty-DFW", "status": "Paused", "leads": 156, "conversions": 8},
            {"name": "Expansion-Lookalike", "status": "Draft", "leads": 0, "conversions": 0}
        ]
        
        for pb in playbooks:
            with st.expander(f"{pb['name']} ({pb['status']})"):
                st.metric("Leads", pb['leads'])
                st.metric("Conversions", pb['conversions'])
                if pb['conversions'] > 0:
                    st.metric("Conv Rate", f"{pb['conversions']/pb['leads']*100:.1f}%")


if __name__ == "__main__":
    main()
