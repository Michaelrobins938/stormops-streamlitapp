import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="StormOps Test", page_icon="⛈️")

# Test 1: Can we load data?
AREAS_CSV = "outputs/dfw_hotspots_areas.csv"

try:
    df = pd.read_csv(AREAS_CSV)
    st.success(f"Loaded {len(df)} rows")
    st.write("Columns:", list(df.columns[:5]))
except Exception as e:
    st.error(f"Error loading data: {e}")

# Test 2: Simple content
st.markdown("# Test Header")
st.markdown("If you see this, Streamlit is working")

# Test 3: Data preview
if "df" in locals():
    st.dataframe(df.head(3))
