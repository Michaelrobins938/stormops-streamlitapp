#!/usr/bin/env python3
"""Minimal test to verify map renders."""

import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Test Map", layout="wide")

BASE_DIR = "/home/forsythe/earth2-forecast-wsl/hotspot_tool"

AREAS_CSV = os.path.join(BASE_DIR, "outputs", "dfw_hotspots_areas.csv")
ZIPS_GEOJSON = os.path.join(BASE_DIR, "data", "dfw_zips.geojson")

st.title("🗺️ Storm Lead Finder - TEST")

df = pd.read_csv(AREAS_CSV)
st.write(f"CSV: {len(df)} rows, columns: {list(df.columns[:5])}")

with open(ZIPS_GEOJSON) as f:
    geojson_data = json.load(f)
st.write(f"GeoJSON: {len(geojson_data.get('features', []))} features")

zip_col = None
for c in ["ZCTA5CE10", "ZIP", "zip", "GEOID"]:
    if c in df.columns:
        zip_col = c
        break

st.write(f"Using ZIP column: {zip_col}")

df["job_score"] = df["storm_score_max"] * 1.1

h = len(df[df["damage_risk"] == "High"])
m = len(df[df["damage_risk"] == "Medium"])
st.markdown(f"**High: {h}** | **Medium: {m}**")

filtered = df[df["damage_risk"].isin(["High", "Medium"])]
st.write(f"Filtered: {len(filtered)} rows")

if filtered.empty:
    st.warning("No data!")
    st.stop()

import plotly.express as px

centroids = []
for feature in geojson_data.get("features", []):
    props = feature.get("properties", {})
    zcta = props.get("ZCTA5CE10") or props.get("ZIP") or props.get("GEOID")
    if zcta:
        geom = feature.get("geometry", {})
        if geom.get("type") == "Polygon":
            coords = coords[0] if (coords := geom.get("coordinates")) else []
            if coords:
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                centroids.append(
                    {
                        "zip": str(zcta),
                        "lat": sum(lats) / len(lats),
                        "lon": sum(lons) / len(lons),
                    }
                )

st.write(f"Centroids: {len(centroids)}")

if centroids:
    cent_df = pd.DataFrame(centroids)
    plot_df = cent_df.merge(filtered, left_on="zip", right_on=zip_col, how="inner")
    st.write(f"Plot data: {len(plot_df)} rows")

    if len(plot_df) > 0:
        fig = px.scatter_mapbox(
            plot_df,
            lat="lat",
            lon="lon",
            color="job_score",
            size="storm_score_max",
            color_continuous_scale="YlOrRd",
            zoom=8,
            mapbox_style="open-street-map",
            hover_name="zip",
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Top ZIPs")
        top = plot_df.sort_values("job_score", ascending=False).head(5)
        for _, row in top.iterrows():
            st.write(f"**{row['zip']}** - {row['job_score']:.2f}")
    else:
        st.warning("No matching data to plot")
else:
    st.warning("No centroids")

st.success("Done")
