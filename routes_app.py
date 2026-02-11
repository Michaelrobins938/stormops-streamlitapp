"""
StormOps Control Plane - Routes & Jobs
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import uuid
from route_builder import RouteBuilder, JobTracker
from copilot import render_copilot
from theme import get_theme_css

st.set_page_config(page_title="StormOps - Routes & Jobs", layout="wide", page_icon="")

engine = create_engine("sqlite:///stormops_cache.db")

st.markdown(get_theme_css(), unsafe_allow_html=True)

# Hardcoded for demo
tenant_id = "00000000-0000-0000-0000-000000000000"
storm_id = "bd502bf4-5401-4cc6-83ba-be85395e9cc7"

st.markdown("## StormOps: Routes & Jobs")

tab1, tab2 = st.tabs(["Build Routes", "Job Intelligence"])

# ============================================================================
# PHASE 3: BUILD ROUTES
# ============================================================================
with tab1:
    st.header("Phase 3: Build Routes")

    builder = RouteBuilder(tenant_id, storm_id)
    existing_routes = builder.get_routes()

    if existing_routes:
        st.metric("Total Routes", len(existing_routes))

        routes_df = pd.DataFrame(existing_routes)
        st.dataframe(routes_df, use_container_width=True)

        st.subheader("Assign Crews")
        for route in existing_routes:
            if route["status"] == "pending":
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.text(
                        f"{route['route_name']} ({route['property_count']} properties)"
                    )
                with col2:
                    crew = st.text_input(
                        "Crew",
                        key=f"crew_{route['route_id']}",
                        label_visibility="collapsed",
                    )
                with col3:
                    if st.button("Assign", key=f"assign_{route['route_id']}"):
                        builder.assign_crew(route["route_id"], crew)
                        st.success(f"Assigned to {crew}")
                        st.rerun()

        st.subheader("Export Route")
        selected_route = st.selectbox(
            "Select route",
            [r["route_id"] for r in existing_routes],
            format_func=lambda x: next(
                r["route_name"] for r in existing_routes if r["route_id"] == x
            ),
        )
        if st.button("Generate CSV"):
            csv = builder.export_route_csv(selected_route)
            st.download_button(
                "Download CSV", csv, f"route_{selected_route}.csv", "text/csv"
            )

    else:
        st.info("No routes generated yet")

        col1, col2 = st.columns(2)
        with col1:
            max_per_route = st.number_input("Max properties per route", 20, 100, 50)

        if st.button("Generate Routes", type="primary"):
            with st.spinner("Generating routes..."):
                routes = builder.generate_routes(max_per_route)
                st.success(f" Generated {len(routes)} routes")
                st.rerun()

# ============================================================================
# PHASE 4: JOB INTELLIGENCE
# ============================================================================
with tab2:
    st.header("Phase 4: Job Intelligence")

    tracker = JobTracker(tenant_id, storm_id)

    # Show all jobs
    with engine.connect() as conn:
        jobs = pd.read_sql(
            f"""
            SELECT 
                j.job_id,
                p.external_id as property,
                p.address,
                r.route_name,
                j.status,
                j.completed_at
            FROM jobs j
            JOIN properties p ON j.property_id = p.property_id
            LEFT JOIN routes r ON j.route_id = r.route_id
            WHERE j.storm_id = '{storm_id}'
            ORDER BY j.created_at
        """,
            conn,
        )

    if len(jobs) > 0:
        st.metric("Total Jobs", len(jobs))

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pending", len(jobs[jobs["status"] == "pending"]))
        with col2:
            st.metric("In Progress", len(jobs[jobs["status"] == "in_progress"]))
        with col3:
            st.metric("Completed", len(jobs[jobs["status"] == "completed"]))

        st.dataframe(jobs, use_container_width=True)

        st.subheader("Update Job")

        job_id_input = st.text_input("Job ID (UUID)")

        if job_id_input:
            try:
                job_id = uuid.UUID(job_id_input)

                col1, col2 = st.columns(2)
                with col1:
                    new_status = st.selectbox(
                        "Status", ["pending", "in_progress", "completed"]
                    )
                    notes = st.text_area("Notes")

                with col2:
                    converted = st.checkbox("Converted to claim")
                    if converted:
                        claim_amount = st.number_input(
                            "Claim Amount ($)", 0, 100000, 10000
                        )
                        damage_type = st.selectbox(
                            "Damage Type", ["hail", "wind", "water", "other"]
                        )

                if st.button("Update Job", type="primary"):
                    claim_intel = (
                        {"claim_amount": claim_amount, "damage_type": damage_type}
                        if converted
                        else None
                    )
                    tracker.update_job(
                        job_id,
                        status=new_status,
                        notes=notes,
                        claim_intel=claim_intel,
                        converted=converted if new_status == "completed" else None,
                    )
                    st.success(" Job updated")
                    st.rerun()

            except ValueError:
                st.error("Invalid Job ID")

    else:
        st.info("No jobs yet. Generate routes first.")
