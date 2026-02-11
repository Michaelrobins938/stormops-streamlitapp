import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Storm Lead Finder", layout="wide")

BASE = "/home/forsythe/earth2-forecast-wsl/hotspot_tool"

# Load data
df = pd.read_csv(f"{BASE}/outputs/dfw_hotspots_areas.csv")
df["zip"] = df["ZCTA5CE10"].astype(str)
df["job_score"] = df["storm_score_max"] * 100

with open(f"{BASE}/data/dfw_zips.geojson") as f:
    gj = json.load(f)

# Title
st.title("🗺️ Storm Lead Finder")
st.caption("Live storm map - tap points to see ZIP details")

# Compute centroids
centroids = []
for feat in gj["features"]:
    props = feat.get("properties", {})
    zcta = props.get("ZCTA5CE10")
    if zcta:
        geom = feat.get("geometry", {})
        if geom.get("type") == "Polygon":
            coords = geom.get("coordinates", [[]])[0]
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

if centroids:
    cent_df = pd.DataFrame(centroids)
    plot_df = cent_df.merge(df, on="zip", how="inner")

    if len(plot_df) > 0:
        # Summary
        st.markdown(
            f"**{len(plot_df)} ZIPs** | **Top: {plot_df.loc[plot_df['job_score'].idxmax(), 'zip']}** ({plot_df['job_score'].max():.1f})"
        )

        # Map
        fig = px.scatter_mapbox(
            plot_df,
            lat="lat",
            lon="lon",
            color="job_score",
            size="storm_score_max",
            color_continuous_scale="YlOrRd",
            zoom=7,
            mapbox_style="open-street-map",
            hover_name="zip",
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=600)
        st.plotly_chart(fig, use_container_width=True)

        # Top ZIPs
        st.markdown("### Top ZIPs by Score")
        for _, row in (
            plot_df.sort_values("job_score", ascending=False).head(10).iterrows()
        ):
            st.write(f"**{row['zip']}** - Score: {row['job_score']:.1f}")
    else:
        st.warning("No matching data")
else:
    st.warning("Could not compute centroids")

st.success("Map loaded!")
