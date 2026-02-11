"""
StormOps Wizard - Guided Phase Navigation
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
from theme import get_theme_css

# Initialize
if "current_phase" not in st.session_state:
    st.session_state.current_phase = 0
if "storm_loaded" not in st.session_state:
    st.session_state.storm_loaded = False

engine = create_engine("sqlite:///stormops_cache.db")

st.markdown(get_theme_css(), unsafe_allow_html=True)


# Header
def render_header():
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown("### STORMOPS WIZARD")
    with col2:
        st.metric("Storm Score", "40/100", "")
    with col3:
        st.markdown(f"Phase {st.session_state.current_phase + 1}/5")
    with col4:
        st.markdown("**PROD**")


# Phase stepper
def render_stepper():
    phases = [
        "Storm Overview",
        "Map Targets",
        "Build Routes",
        "Execute Jobs",
        "Nurture & Close",
    ]
    cols = st.columns(5)
    for i, phase in enumerate(phases):
        with cols[i]:
            if i == st.session_state.current_phase:
                st.button(
                    f"**{i + 1}. {phase}**",
                    key=f"phase_{i}",
                    type="primary",
                    disabled=True,
                )
            elif i < st.session_state.current_phase:
                if st.button(f"{i + 1}. {phase}", key=f"phase_{i}"):
                    st.session_state.current_phase = i
                    st.rerun()
            else:
                st.button(f"{i + 1}. {phase}", key=f"phase_{i}", disabled=True)


# Phase 0: Storm Overview
def phase_0():
    st.markdown("##  Storm Overview")
    st.info("**What to do now:** Load a storm event to begin targeting.")

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("load_storm"):
            storm_name = st.text_input("Storm Name", "DFW_STORM_24")
            center_lat = st.number_input("Center Latitude", value=32.8)
            center_lon = st.number_input("Center Longitude", value=-96.8)
            radius = st.slider("Radius (km)", 10, 100, 50)

            if st.form_submit_button(" Load Storm Event", type="primary"):
                st.session_state.storm_loaded = True
                st.success("Storm loaded! Moving to Phase 1...")
                st.session_state.current_phase = 1
                st.rerun()

    with col2:
        st.markdown("### Storm Stats")
        if st.session_state.storm_loaded:
            st.metric("Impact Zones", "127")
            st.metric("Properties", "4,200")
            st.metric("Est. Value", "$2.1M")
        else:
            st.warning("Load storm to see stats")


# Phase 1: Map Targets
def phase_1():
    st.markdown("##  Map Targets")
    st.info("**What to do now:** Use filters to identify high-value properties.")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Target Map")
        df = pd.read_sql_query(
            "SELECT zip, COUNT(*) as count FROM properties GROUP BY zip LIMIT 10",
            engine,
        )
        if not df.empty:
            fig = px.bar(df, x="zip", y="count", title="Properties by ZIP")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Filters")
        min_sii = st.slider("Min SII Score", 0, 100, 20)
        zip_filter = st.multiselect("ZIP Codes", ["75209", "76201"])

        if st.button("🔍 Find Leads", type="primary"):
            st.success("Found 342 qualified leads")
            st.session_state.current_phase = 2
            st.rerun()


# Phase 2: Build Routes
def phase_2():
    st.markdown("##  Build Routes")
    st.info("**What to do now:** Generate optimized routes for field teams.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Route Builder")
        num_crews = st.number_input("Number of Crews", 1, 10, 3)
        max_stops = st.slider("Max Stops per Route", 10, 50, 25)

        if st.button("🚗 Generate Routes", type="primary"):
            st.success("Created 3 routes with 72 total stops")
            st.session_state.current_phase = 3
            st.rerun()

    with col2:
        st.markdown("### Route Stats")
        st.metric("Routes", "3")
        st.metric("Total Stops", "72")
        st.metric("Avg. Drive Time", "2.3 hrs")


# Phase 3: Execute Jobs
def phase_3():
    st.markdown("## 🔨 Execute Jobs")
    st.info("**What to do now:** Assign routes and track job progress.")

    # Job board
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 📋 Unassigned")
        st.markdown("- Route A (24 stops)")
        st.markdown("- Route B (25 stops)")

    with col2:
        st.markdown("### 👷 Assigned")
        st.markdown("- Route C → Crew 1")

    with col3:
        st.markdown("### 🚧 In Progress")
        st.markdown("- Route D (15/23 done)")

    with col4:
        st.markdown("###  Completed")
        st.markdown("- Route E (23/23)")

    if st.button("➡️ Move to Nurture", type="primary"):
        st.session_state.current_phase = 4
        st.rerun()


# Phase 4: Nurture & Close
def phase_4():
    st.markdown("## 📞 Nurture & Close")
    st.info("**What to do now:** Follow up with leads and track conversions.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Lead Pipeline")
        pipeline = pd.DataFrame(
            {
                "Stage": ["New", "Contacted", "Quoted", "Closed"],
                "Count": [120, 45, 18, 7],
            }
        )
        fig = px.funnel(pipeline, x="Count", y="Stage")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Conversion Metrics")
        st.metric("Conversion Rate", "5.8%")
        st.metric("Avg. Deal Size", "$8,200")
        st.metric("Total Revenue", "$57,400")


# Main app
def main():
    render_header()
    st.divider()
    render_stepper()
    st.divider()

    # Route to current phase
    if st.session_state.current_phase == 0:
        phase_0()
    elif st.session_state.current_phase == 1:
        phase_1()
    elif st.session_state.current_phase == 2:
        phase_2()
    elif st.session_state.current_phase == 3:
        phase_3()
    elif st.session_state.current_phase == 4:
        phase_4()


if __name__ == "__main__":
    st.set_page_config(page_title="StormOps Wizard", layout="wide")
    main()
