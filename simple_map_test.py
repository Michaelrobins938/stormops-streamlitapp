import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="MAP TEST", layout="wide")

BASE = "/home/forsythe/earth2-forecast-wsl/hotspot_tool"

df = pd.read_csv(f"{BASE}/outputs/dfw_hotspots_areas.csv")
df["zip"] = df["ZCTA5CE10"].astype(str)
df["job_score"] = df["storm_score_max"] * 100

with open(f"{BASE}/data/dfw_zips.geojson") as f:
    gj = json.load(f)

st.title("MAP TEST - DATA LOADED")
st.write(f"CSV rows: {len(df)}")
st.write(f"GeoJSON features: {len(gj['features'])}")

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

st.write(f"Centroids: {len(centroids)}")

if centroids:
    cd = pd.DataFrame(centroids)
    plot = cd.merge(df, on="zip", how="inner")
    st.write(f"Plot data: {len(plot)} rows")

    if len(plot) > 0:
        fig = px.scatter_mapbox(
            plot,
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

        st.success("MAP SHOULD BE ABOVE")

        st.write("Top 5 ZIPs:")
        for _, row in plot.sort_values("job_score", ascending=False).head(5).iterrows():
            st.write(f"{row['zip']}: {row['job_score']:.2f}")
    else:
        st.error("No matching data after merge!")
else:
    st.error("No centroids computed!")

st.write("TEST COMPLETE")
