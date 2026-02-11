import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.title("Test App")

engine = create_engine('postgresql://stormops:password@localhost:5432/stormops')

with engine.connect() as conn:
    tenants = pd.read_sql("SELECT tenant_id, org_name FROM tenants WHERE status = 'active'", conn)
    st.write(f"Found {len(tenants)} tenants")
    st.dataframe(tenants)

st.success("App loaded successfully!")
