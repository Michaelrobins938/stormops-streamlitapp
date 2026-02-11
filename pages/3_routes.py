"""
Phase 3: Routes & Jobs - Kanban Board View
Foreman sees today's routes, assignments, and map
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import uuid
from theme import get_theme_css

st.set_page_config(page_title="Routes & Jobs", layout="wide", page_icon="")

st.markdown(get_theme_css(), unsafe_allow_html=True)

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown("## Routes & Jobs")
with col2:
    st.metric("Active Routes", "7")
with col3:
    st.metric("Completion", "45%")

st.divider()

# Connect to DB
engine = create_engine("sqlite:///stormops_cache.db")

# Hardcoded for demo
tenant_id = "demo-tenant"
storm_id = "demo-storm"

# Get routes and jobs
with engine.connect() as conn:
    routes = pd.read_sql(
        f"""
        SELECT
            r.route_id,
            r.name AS route_name,
            r.zip_code,
            r.property_count,
            r.status,
            COALESCE(r.assigned_crew, 'Unassigned') AS assigned_crew,
            COUNT(j.job_id) as total_jobs,
            SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END) as completed_jobs
        FROM routes r
        LEFT JOIN jobs j ON r.route_id = j.route_id
        WHERE r.tenant_id = '{tenant_id}' AND r.storm_id = '{storm_id}'
        GROUP BY r.route_id, r.name, r.zip_code, r.property_count, r.status, r.assigned_crew
        ORDER BY r.created_at
    """,
        conn,
    )

# Job board
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("####  Unassigned")
    unassigned = routes[routes["status"] == "pending"]
    st.metric("Routes", len(unassigned))

    for _, route in unassigned.iterrows():
        with st.container():
            st.markdown(f"**{route['route_name']}**")
            st.caption(f"ZIP {route['zip_code']}  {route['property_count']} properties")
            crew = st.text_input(
                "Assign crew",
                key=f"crew_{route['route_id']}",
                label_visibility="collapsed",
                placeholder="Crew name",
            )
            if st.button(
                "Assign", key=f"assign_{route['route_id']}", use_container_width=True
            ):
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                        UPDATE routes SET assigned_crew = :crew, status = 'assigned'
                        WHERE route_id = :rid
                    """),
                        {"crew": crew, "rid": route["route_id"]},
                    )
                st.success(f"Assigned to {crew}")
                st.rerun()
            st.divider()

with col2:
    st.markdown("####  Assigned")
    assigned = routes[routes["status"] == "assigned"]
    st.metric("Routes", len(assigned))

    for _, route in assigned.iterrows():
        with st.container():
            st.markdown(f"**{route['route_name']}**")
            st.caption(f"Crew: {route['assigned_crew']}")
            st.caption(f"{route['property_count']} properties")
            if st.button(
                "Start", key=f"start_{route['route_id']}", use_container_width=True
            ):
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                        UPDATE routes SET status = 'in_progress' WHERE route_id = :rid
                    """),
                        {"rid": route["route_id"]},
                    )
                    conn.execute(
                        text("""
                        UPDATE jobs SET status = 'in_progress' WHERE route_id = :rid
                    """),
                        {"rid": route["route_id"]},
                    )
                st.rerun()
            st.divider()

with col3:
    st.markdown("####  In Progress")
    in_progress = routes[routes["status"] == "in_progress"]
    st.metric("Routes", len(in_progress))

    for _, route in in_progress.iterrows():
        with st.container():
            st.markdown(f"**{route['route_name']}**")
            st.caption(f"Crew: {route['assigned_crew']}")
            completion = (
                (route["completed_jobs"] / route["total_jobs"] * 100)
                if route["total_jobs"] > 0
                else 0
            )
            st.progress(
                completion / 100,
                text=f"{route['completed_jobs']}/{route['total_jobs']} done",
            )
            if st.button(
                "View Jobs", key=f"view_{route['route_id']}", use_container_width=True
            ):
                st.session_state["selected_route"] = route["route_id"]
            st.divider()

with col4:
    st.markdown("####  Completed")
    completed = routes[routes["status"] == "completed"]
    st.metric("Routes", len(completed))

    for _, route in completed.iterrows():
        with st.container():
            st.markdown(f"**{route['route_name']}**")
            st.caption(f"Crew: {route['assigned_crew']}")
            st.caption(f" {route['completed_jobs']} jobs")
            st.divider()

# Job details drawer
if "selected_route" in st.session_state:
    st.divider()
    st.markdown("###  Job Details")

    route_id = st.session_state["selected_route"]

    with engine.connect() as conn:
        jobs = pd.read_sql(
            f"""
            SELECT 
                j.job_id,
                j.address,
                j.status,
                j.notes,
                j.completed_at
            FROM jobs j
            WHERE j.route_id = '{route_id}'
            ORDER BY j.created_at
        """,
            conn,
        )

    for _, job in jobs.iterrows():
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown(f"**{job['job_id']}** - {job['address']}")

        with col2:
            status_emoji = {"pending": "", "in_progress": "", "completed": ""}
            st.markdown(f"{status_emoji.get(job['status'], '')} {job['status']}")

        with col3:
            if job["status"] != "completed":
                if st.button("Complete", key=f"complete_{job['job_id']}"):
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                            UPDATE jobs SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                            WHERE job_id = :jid
                        """),
                            {"jid": job["job_id"]},
                        )
                    st.rerun()

        st.divider()

# Quick actions
st.divider()
col1, col2 = st.columns(2)

with col1:
    if st.button(" Generate New Routes", type="primary", use_container_width=True):
        from route_builder import RouteBuilder

        builder = RouteBuilder(tenant_id, storm_id)
        routes = builder.generate_routes(max_per_route=50)
        st.success(f" Generated {len(routes)} routes")
        st.rerun()

with col2:
    if st.button(" View Pilot Dashboard", use_container_width=True):
        st.info("Run: streamlit run pilot_dashboard.py")
