"""
StormOps - Main App Entry Point
Clean wizard-style navigation
"""

import streamlit as st

def main():
    st.set_page_config(
        page_title="StormOps",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Header bar
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown("### ⚡ StormOps")
    with col2:
        st.metric("Storm Score", "40/100", delta="+5")
    with col3:
        st.markdown("**Storm:** Sample")
    with col4:
        st.markdown("**ENV:** PROD")

    st.divider()

    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🎯 Storm Workflow")
        
        page = st.radio(
            "Navigate",
            [
                "📊 Overview",
                "🎯 Phase 1: Target",
                "📈 Phase 2: Attribution", 
                "🗺️ Phase 3: Routes",
                "🔧 Phase 4: Jobs",
                "🔄 Phase 5: Nurture"
            ],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Progress indicators
        st.markdown("**Progress**")
        st.progress(0.4, text="Targets: 100%")
        st.progress(0.0, text="Routes: 0%")
        st.progress(0.0, text="Jobs: 0%")

    # Route to pages
    if "Overview" in page:
        st.markdown("## Storm Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Properties", "1,247")
        col2.metric("High Uplift", "342")
        col3.metric("Routes Ready", "0")
        col4.metric("Est. Value", "$8.4M")
        
        st.divider()
        
        st.markdown("### Next Steps")
        st.info("✅ Targets identified. Click **Phase 3: Routes** to generate field routes.")
        
        if st.button("🗺️ Generate Routes", type="primary", use_container_width=True):
            st.success("Click Phase 3 in sidebar to generate routes")

    elif "Phase 1" in page:
        st.markdown("## Phase 1: Target Properties")
        st.info("**What to do:** Review high-uplift properties and apply treatment policy.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Treatment Policy")
            policy = st.selectbox("Policy Mode", ["Moderate", "Aggressive", "Conservative"])
            if st.button("Apply Policy", type="primary"):
                st.success("✅ Policy applied to 342 properties")
        
        with col2:
            st.markdown("### Metrics")
            st.metric("Treat", "342")
            st.metric("Hold", "905")
            st.metric("Avg Uplift", "18.5%")

    elif "Phase 2" in page:
        st.markdown("## Phase 2: Attribution")
        st.info("**What to do:** Review channel performance and attribution.")
        
        st.markdown("### Channel Performance")
        st.bar_chart({"Direct": 45, "Email": 30, "Social": 15, "Referral": 10})

    elif "Phase 3" in page:
        st.markdown("## Phase 3: Build Routes")
        st.info("**What to do:** Generate optimized routes and assign to crews.")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            max_per_route = st.number_input("Properties per route", 20, 100, 50)
            if st.button("Generate Routes", type="primary"):
                st.success("✅ Generated 7 routes")
                st.rerun()
        
        with col2:
            st.metric("Routes", "0")
            st.metric("Properties", "0")

    elif "Phase 4" in page:
        st.markdown("## Phase 4: Job Intelligence")
        st.info("**What to do:** Track field work and capture outcomes.")
        
        # Job board
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**Unassigned**")
            st.markdown("0 jobs")
        
        with col2:
            st.markdown("**Assigned**")
            st.markdown("0 jobs")
        
        with col3:
            st.markdown("**In Progress**")
            st.markdown("0 jobs")
        
        with col4:
            st.markdown("**Completed**")
            st.markdown("0 jobs")

    elif "Phase 5" in page:
        st.markdown("## Phase 5: Nurture Loop")
        st.info("**What to do:** Follow up with unconverted properties.")
        
        st.metric("Unconverted", "0")
        st.metric("Follow-ups Sent", "0")

if __name__ == "__main__":
    main()
