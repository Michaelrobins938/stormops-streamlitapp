"""
Timeline Tab - "When it hit / When to start" vertical story view
Implements PRD design for mobile-first storm response workflow.
"""

import streamlit as st


def render_timeline_tab(merged, df, job_focus, meta):
    """Render the Timeline tab with storm story and action recommendations."""
    
    st.markdown("---")
    st.subheader("⏱️ Storm Timeline")
    st.caption("When it hit • When you can start • What to do next")
    
    # Get timing data
    peak_hour = merged["peak_hour_utc"].mean() if "peak_hour_utc" in merged.columns else 0
    hours_high_risk = merged["hours_high_risk_mean"].mean() if "hours_high_risk_mean" in merged.columns else 0
    max_hours = merged["hours_high_risk_max"].max() if "hours_high_risk_max" in merged.columns else 0
    
    # Card 1: When it hit
    st.markdown("### 📍 When It Hit")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e2130 0%, #0e1117 100%); 
                    border: 1px solid #ff7a00; border-radius: 12px; padding: 20px; 
                    margin: 8px 0; text-align: center;">
            <div style="font-size: 0.9rem; color: #888;">Peak Impact</div>
            <div style="font-size: 2.5rem; font-weight: bold; color: #ff7a00;">
                Hour {peak_hour:.0f}
            </div>
            <div style="font-size: 0.8rem; color: #888;">from forecast start</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e2130 0%, #0e1117 100%); 
                    border: 1px solid #ff7a00; border-radius: 12px; padding: 20px; 
                    margin: 8px 0; text-align: center;">
            <div style="font-size: 0.9rem; color: #888;">Elevated Conditions</div>
            <div style="font-size: 2.5rem; font-weight: bold; color: #ff4444;">
                {max_hours:.0f}h
            </div>
            <div style="font-size: 0.8rem; color: #888;">total at high risk</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Card 2: When you can start (job-specific)
    st.markdown("### 🚧 When You Can Start")
    
    # Job-specific timing recommendations
    job_timing = {
        "Tear-off / Demo": {
            "emoji": "🏗️",
            "wait_after_peak": 48,
            "description": "Wait 48h after peak",
            "earliest_start": f"Hour {peak_hour + 48:.0f}",
            "reasoning": "Requires calm conditions (wind <15 m/s, minimal precip)"
        },
        "Membrane Install": {
            "emoji": "🛡️",
            "wait_after_peak": 24,
            "description": "Wait 24h after peak",
            "earliest_start": f"Hour {peak_hour + 24:.0f}",
            "reasoning": "Tolerates wind up to 20 m/s, avoid rain"
        },
        "Inspection / Canvassing": {
            "emoji": "🔍",
            "wait_after_peak": 6,
            "description": "Can start 6h after peak",
            "earliest_start": f"Hour {peak_hour + 6:.0f}",
            "reasoning": "Can work in most conditions (wind <25 m/s)"
        }
    }
    
    timing = job_timing.get(job_focus, job_timing["Inspection / Canvassing"])
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e2130 0%, #0e1117 100%); 
                border: 2px solid #ff7a00; border-radius: 16px; padding: 24px; 
                margin: 16px 0;">
        <div style="font-size: 1.2rem; margin-bottom: 12px;">
            {timing["emoji"]} <strong>{job_focus}</strong>
        </div>
        <div style="font-size: 2rem; font-weight: bold; color: #44ff44; margin-bottom: 8px;">
            {timing["description"]}
        </div>
        <div style="font-size: 1.5rem; color: #ff7a00; margin-bottom: 12px;">
            Earliest safe start: {timing["earliest_start"]}
        </div>
        <div style="font-size: 0.9rem; color: #888;">
            💡 {timing["reasoning"]}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Card 3: Do this next
    st.markdown("### 🎯 Do This Next")
    
    # Generate action items based on job type and timing
    actions = []
    
    if job_focus == "Tear-off / Demo":
        actions = [
            ("📋", "Generate tear-off crew assignments for ZIPs scoring 73+"),
            ("📍", "Pre-stage materials in high-impact areas"),
            ("⏰", "Schedule crews no earlier than Hour 60"),
            ("🌤️", "Monitor weather - no follow-on storms expected"),
        ]
    elif job_focus == "Membrane Install":
        actions = [
            ("📋", "Create install schedule for ZIPs scoring 55+"),
            ("📍", "Position crews near high-impact zones"),
            ("⏰", "Ready crews for Hour 36+"),
            ("💧", "Check precip forecast - avoid rainy windows"),
        ]
    else:  # Inspection
        actions = [
            ("📋", "Download today's inspection route"),
            ("🚗", "Head to highest-damage ZIPs first"),
            ("⏰", "Start immediately - fresh leads convert best"),
            ("📸", "Document damage for insurance claims"),
        ]
    
    for emoji, action in actions:
        st.markdown(f"{emoji} {action}")
    
    # Timeline visualization
    st.markdown("### 📊 Timeline View")
    
    # Create a simple timeline
    timeline_events = [
        ("Hour 0", "Storm begins", "#888"),
        (f"Hour {peak_hour:.0f}", "Peak impact", "#ff4444"),
        (f"Hour {peak_hour + 6:.0f}", "Inspection window opens", "#44ff44"),
        (f"Hour {peak_hour + 24:.0f}", "Membrane install window", "#ffaa00"),
        (f"Hour {peak_hour + 48:.0f}", "Tear-off window", "#ff7a00"),
    ]
    
    timeline_html = """
    <div style="position: relative; padding: 20px 0;">
        <div style="position: absolute; top: 0; bottom: 0; left: 20px; width: 4px; 
                    background: #333; border-radius: 2px;"></div>
    """
    
    for hour, label, color in timeline_events:
        timeline_html += f"""
        <div style="position: relative; padding-left: 40px; margin-bottom: 16px;">
            <div style="position: absolute; left: 12px; width: 20px; height: 20px; 
                        background: {color}; border-radius: 50%; border: 3px solid #0e1117;"></div>
            <div style="font-size: 1.1rem; font-weight: bold;">{hour}</div>
            <div style="font-size: 0.9rem; color: #888;">{label}</div>
        </div>
        """
    
    timeline_html += "</div>"
    st.markdown(timeline_html, unsafe_allow_html=True)
    
    # Quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    action_cols = st.columns(4)
    
    with action_cols[0]:
        if st.button("📋 Export Route", use_container_width=True):
            st.success("Route exported! Check Downloads.")
    
    with action_cols[1]:
        if st.button("📤 Share Timeline", use_container_width=True):
            timeline_text = f"""Storm Timeline - {job_focus}
- Peak Impact: Hour {peak_hour:.0f}
- Elevated Conditions: {max_hours:.0f}h
- {job_focus} Start: {timing["earliest_start"]}

Generated by Earth-2 StormOps"""
            st.code(timeline_text, language="text")
            st.success("Timeline copied!")
    
    with action_cols[2]:
        if st.button("🗺️ Open Map", use_container_width=True):
            st.session_state.active_tab = "map"
    
    with action_cols[3]:
        if st.button("📋 View Leads", use_container_width=True):
            st.session_state.active_tab = "leads"


def render_leads_tab(merged, df, job_focus, customer_impact):
    """Render the Leads tab with field-friendly list."""
    
    st.markdown("---")
    st.subheader("📋 Today's Priority Leads")
    st.caption(f"Optimized for {job_focus} work")
    
    # Search and filters
    search_cols = st.columns([2, 1])
    
    with search_cols[0]:
        search = st.text_input("🔍 Search ZIP or address", placeholder="75040, Oak Street...")
    
    with search_cols[1]:
        sort_by = st.selectbox("Sort by", ["Risk Score", "Distance", "Job Fit"])
    
    # Quick filters
    filter_cols = st.columns(4)
    
    with filter_cols[0]:
        show_high = st.checkbox("High Risk", value=True)
    with filter_cols[1]:
        show_medium = st.checkbox("Medium Risk", value=True)
    with filter_cols[2]:
        show_low = st.checkbox("Low Risk", value=False)
    with filter_cols[3]:
        show_my_customers = st.checkbox("My Customers Only")
    
    # Filter data
    risk_filter = []
    if show_high:
        risk_filter.append("High")
    if show_medium:
        risk_filter.append("Medium")
    if show_low:
        risk_filter.append("Low")
    
    filtered_leads = merged[merged["damage_risk"].isin(risk_filter)]
    
    if search:
        filtered_leads = filtered_leads[
            filtered_leads.apply(lambda row: search.lower() in str(row.get('ZCTA5CE10', '')).lower(), axis=1)
        ]
    
    # Sort by selected criteria
    if sort_by == "Risk Score":
        filtered_leads = filtered_leads.sort_values("storm_score_max", ascending=False)
    elif sort_by == "Distance":
        # Placeholder - would need user location
        filtered_leads = filtered_leads.sort_values("storm_score_max", ascending=False)
    
    # Lead list
    st.markdown("### 🎯 Priority List")
    
    if filtered_leads.empty:
        st.info("No leads match your filters. Try adjusting criteria.")
    else:
        # Show count
        st.caption(f"Showing {len(filtered_leads)} of {len(merged)} ZIPs")
        
        # Render lead cards
        for i, (_, row) in enumerate(filtered_leads.head(20).iterrows()):
            zip_code = row.get('ZCTA5CE10', 'N/A')
            risk = row.get('damage_risk', 'Unknown')
            score = row.get('storm_score_max', 0)
            wind = row.get('max_wind_max', 0)
            
            # Risk color
            risk_color = "#ff4444" if risk == "High" else "#ffaa00" if risk == "Medium" else "#44ff44"
            
            # Job fit badge
            if job_focus == "Tear-off / Demo":
                job_fit = "⭐ Best" if score > 1.0 else ("Good" if score > 0.5 else "Fair")
            elif job_focus == "Membrane Install":
                job_fit = "⭐ Best" if (score > 0.8 and wind < 15) else ("Good" if score > 0.5 else "Fair")
            else:
                job_fit = "⭐ Best" if score > 0.5 else "Good"
            
            st.markdown(f"""
            <div class="lead-row" style="background: #1e2130; border: 1px solid #333; 
                                         border-radius: 8px; padding: 16px; margin: 8px 0;
                                         display: flex; align-items: center; justify-content: space-between;">
                <div class="lead-info">
                    <div style="font-size: 1.3rem; font-weight: bold; color: #ff7a00;">
                        📍 ZIP {zip_code}
                    </div>
                    <div style="display: flex; gap: 12px; margin-top: 8px;">
                        <span style="background: {risk_color}; padding: 4px 12px; 
                                    border-radius: 20px; font-size: 0.8rem;">
                            {risk}
                        </span>
                        <span style="background: #333; padding: 4px 12px; 
                                    border-radius: 20px; font-size: 0.8rem;">
                            {job_fit} for {job_focus.split('/')[0]}
                        </span>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.5rem; font-weight: bold;">{score:.2f}</div>
                    <div style="font-size: 0.8rem; color: #888;">risk score</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons for this lead
            action_btns = st.columns(4)
            with action_btns[0]:
                if st.button("🗺️ Navigate", key=f"nav_{i}", use_container_width=True):
                    st.toast(f"Opening navigation to ZIP {zip_code}")
            with action_btns[1]:
                if st.button("📞 Call", key=f"call_{i}", use_container_width=True):
                    st.toast(f"Lead phone placeholder for {zip_code}")
            with action_btns[2]:
                if st.button("✓ Done", key=f"done_{i}", use_container_width=True):
                    st.toast(f"Marked ZIP {zip_code} as complete")
            with action_btns[3]:
                if st.button("📤 Share", key=f"share_{i}", use_container_width=True):
                    share_text = f"Storm Lead: ZIP {zip_code}\nRisk: {risk}\nScore: {score:.2f}"
                    st.code(share_text, language="text")
            
            st.markdown("---")
        
        # Export all leads
        if len(filtered_leads) > 20:
            st.markdown(f"*Showing top 20 of {len(filtered_leads)} leads. Export for complete list.*")
        
        # Export button
        export_cols = st.columns(2)
        
        with export_cols[0]:
            csv = filtered_leads.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Lead List (CSV)",
                data=csv,
                file_name=f"storm_leads_{job_focus.split()[0]}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with export_cols[1]:
            if st.button("📱 Send to Phone", use_container_width=True):
                st.info("SMS integration coming soon!")
