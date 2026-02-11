import json
import os
from datetime import datetime

import geopandas as gpd
import numpy as np
import xarray as xr
from shapely.geometry import Point

# -------- CONFIG --------
# FCN forecast Zarr from your existing pipeline
ZARR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "outputs", "fcn_forecast.zarr"
)

# Time window (lead_time indices) for scoring; adjust if needed
TIME_SLICE = slice(0, 20)  # first 20 lead steps (~5 days)

# DFW bounding box (rough)
LAT_MIN, LAT_MAX = 32.0, 34.0
LON_MIN, LON_MAX = -99.0, -95.0

# Thresholds (tune over time)
FREEZE_MIN_K = 271.15  # -2 °C
FREEZE_MAX_K = 275.15  # +2 °C
WIND_HIGH = 25.0  # m/s ~ 56 mph
WIND_MED = 15.0  # m/s ~ 34 mph

# Polygon file (put your real DFW ZIP/tract shapes here)
BASE_DIR = os.path.dirname(__file__)
POLYGON_FILE = os.path.join(BASE_DIR, "data", "dfw_zips.geojson")

OUTPUT_GRID_CSV = os.path.join(BASE_DIR, "outputs", "dfw_hotspots_grid.csv")
OUTPUT_AREAS_CSV = os.path.join(BASE_DIR, "outputs", "dfw_hotspots_areas.csv")
# ------------------------


def load_forecast():
    if not os.path.exists(ZARR_PATH):
        raise FileNotFoundError(
            f"Could not find Zarr forecast at {ZARR_PATH}. "
            "Run your FCN forecast pipeline first so fcn_forecast.zarr exists."
        )

    ds = xr.open_zarr(ZARR_PATH, consolidated=False)

    # Normalize lon to -180..180
    if ds.lon.max() > 180:
        ds = ds.assign_coords(lon=((ds.lon + 180) % 360) - 180)

    # Subset DFW region and time
    ds_dfw = ds.sel(lat=slice(LAT_MAX, LAT_MIN), lon=slice(LON_MIN, LON_MAX)).isel(
        lead_time=TIME_SLICE
    )

    return ds_dfw


def compute_storm_score(ds):
    """
    Compute a simple 'storm damage' score per (time, lat, lon) cell
    combining wind and freezing-precip proxy.
    Returns both aggregated scores and time-series for temporal analysis.
    """
    u = ds["u10m"]
    v = ds["v10m"]
    wind = np.sqrt(u**2 + v**2)

    t2m = ds["t2m"]
    tcwv = ds["tcwv"]  # column water vapour

    freeze_mask = (t2m >= FREEZE_MIN_K) & (t2m <= FREEZE_MAX_K)
    freeze_intensity = tcwv.where(freeze_mask, 0.0)

    wind_score = xr.zeros_like(wind)
    wind_score = wind_score.where(wind < WIND_MED, 1.0)
    wind_score = wind_score.where(wind < WIND_HIGH, 2.0)

    # Avoid divide-by-zero if freeze_intensity is zero everywhere
    max_freeze = (
        float(freeze_intensity.max().values)
        if float(freeze_intensity.max().values) > 0
        else 1.0
    )
    freeze_norm = freeze_intensity / max_freeze

    combined = 0.5 * wind_score + 0.5 * freeze_norm

    # Aggregate over time and lead_time to a single score per (lat, lon)
    storm_score = combined.mean(dim=["time", "lead_time"])
    max_wind = wind.max(dim=["time", "lead_time"])
    total_freeze_precip = freeze_intensity.sum(dim=["time", "lead_time"])

    # Keep time-series for temporal analysis (average across init times, keep lead_time)
    combined_time = combined.mean(dim="time")  # shape: (lead_time, lat, lon)
    wind_time = wind.mean(dim="time")  # shape: (lead_time, lat, lon)

    return storm_score, max_wind, total_freeze_precip, combined_time, wind_time


def compute_temporal_metrics(combined_time, wind_time, risk_threshold=0.6):
    """
    Compute time-based metrics per (lat, lon) cell.
    Tracks when risk turns on/off and peak timing.

    Returns:
        hours_high_risk: Total hours above threshold per cell
        risk_start_idx: First lead_time index where risk is high
        risk_end_idx: Last lead_time index where risk is high
        peak_hour_idx: Index of maximum damage score
        wind_at_peak: Wind speed at time of peak damage
    """
    # Convert lead_time to hours (assuming each step is 6 hours based on TIME_SLICE)
    lead_time_hours = combined_time.lead_time.values * 6

    # Create risk flag (True where score >= threshold)
    risk_flag = combined_time >= risk_threshold

    # Count total hours at high risk
    hours_high_risk = risk_flag.sum(dim="lead_time") * 6  # Convert steps to hours

    # Find peak hour (lead_time index with max combined score)
    peak_hour_idx = combined_time.argmax(dim="lead_time")

    # Get wind at peak hour using the index
    # Use numpy indexing to avoid xarray chunked array issues
    wind_at_peak = xr.DataArray(
        np.array(
            [
                wind_time.isel(lead_time=int(i), lat=lat_idx, lon=lon_idx).values
                for lat_idx in range(len(wind_time.lat))
                for lon_idx in range(len(wind_time.lon))
                for i in [peak_hour_idx.isel(lat=lat_idx, lon=lon_idx).values]
            ]
        ).reshape(len(wind_time.lat), len(wind_time.lon)),
        dims=["lat", "lon"],
        coords={"lat": wind_time.lat, "lon": wind_time.lon},
    )

    # Find risk start/end - first and last True in risk_flag
    # Convert to numpy for easier manipulation
    risk_start_idx = xr.DataArray(
        np.zeros((len(combined_time.lat), len(combined_time.lon)), dtype=int),
        dims=["lat", "lon"],
        coords={"lat": combined_time.lat, "lon": combined_time.lon},
    )
    risk_end_idx = xr.DataArray(
        np.zeros((len(combined_time.lat), len(combined_time.lon)), dtype=int),
        dims=["lat", "lon"],
        coords={"lat": combined_time.lat, "lon": combined_time.lon},
    )

    # Fill with -1 to indicate no risk period
    risk_start_idx.values[:] = -1
    risk_end_idx.values[:] = -1

    for i in range(len(combined_time.lead_time)):
        current_flag = risk_flag.isel(lead_time=i)
        # Update start where not yet set and flag is True
        mask = (risk_start_idx == -1) & current_flag
        risk_start_idx = xr.where(mask, i, risk_start_idx)
        # Update end where flag is True (will keep last True)
        risk_end_idx = xr.where(current_flag, i, risk_end_idx)

    return hours_high_risk, risk_start_idx, risk_end_idx, peak_hour_idx, wind_at_peak


def grid_to_geodataframe(
    storm_score,
    max_wind,
    total_freeze_precip,
    hours_high_risk=None,
    peak_hour_idx=None,
    wind_at_peak=None,
    risk_start_idx=None,
    risk_end_idx=None,
):
    lats = storm_score["lat"].values
    lons = storm_score["lon"].values

    records = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            score = float(storm_score.isel(lat=i, lon=j).values)
            wmax = float(max_wind.isel(lat=i, lon=j).values)
            fprecip = float(total_freeze_precip.isel(lat=i, lon=j).values)

            if np.isnan(score):
                continue

            record = {
                "lat": lat,
                "lon": lon,
                "storm_score": score,
                "max_wind": wmax,
                "freeze_precip": fprecip,
                "geometry": Point(lon, lat),
            }

            # Add temporal metrics if available
            if hours_high_risk is not None:
                record["hours_high_risk"] = int(
                    hours_high_risk.isel(lat=i, lon=j).values
                )
            if peak_hour_idx is not None:
                record["peak_hour_idx"] = int(peak_hour_idx.isel(lat=i, lon=j).values)
                # Convert to actual hours (lead_time * 6)
                record["peak_hour_utc"] = (
                    int(peak_hour_idx.isel(lat=i, lon=j).values) * 6
                )
            if wind_at_peak is not None:
                record["wind_at_peak"] = float(wind_at_peak.isel(lat=i, lon=j).values)
            if risk_start_idx is not None:
                start_idx = int(risk_start_idx.isel(lat=i, lon=j).values)
                if start_idx >= 0:
                    record["risk_start_hour_utc"] = start_idx * 6
                else:
                    record["risk_start_hour_utc"] = None
            if risk_end_idx is not None:
                end_idx = int(risk_end_idx.isel(lat=i, lon=j).values)
                if end_idx >= 0:
                    record["risk_end_hour_utc"] = end_idx * 6
                else:
                    record["risk_end_hour_utc"] = None

            records.append(record)

    gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
    return gdf


def aggregate_to_areas(grid_gdf, polygon_file):
    if not os.path.exists(polygon_file):
        raise FileNotFoundError(
            f"Polygon file {polygon_file} not found.\n"
            "Place a GeoJSON (e.g., DFW ZIP code polygons) there and rerun."
        )

    areas = gpd.read_file(polygon_file).to_crs("EPSG:4326")

    joined = gpd.sjoin(grid_gdf, areas, how="inner", predicate="intersects")

    # Try to guess an ID column
    area_id_col = None
    for col in ["ZIP", "zip", "ZCTA5CE10", "id", "name", "GEOID"]:
        if col in areas.columns:
            area_id_col = col
            break
    if area_id_col is None:
        raise ValueError(
            "Could not find a suitable ID column in polygons "
            "(looked for ZIP, ZCTA5CE10, id, name, GEOID)."
        )

    group = joined.groupby(area_id_col)

    # Build aggregation dictionary
    agg_dict = {
        "storm_score_mean": ("storm_score", "mean"),
        "storm_score_max": ("storm_score", "max"),
        "max_wind_max": ("max_wind", "max"),
        "freeze_precip_sum": ("freeze_precip", "sum"),
        "n_cells": ("storm_score", "count"),
    }

    # Add temporal aggregations if columns exist
    if "hours_high_risk" in joined.columns:
        agg_dict["hours_high_risk_max"] = ("hours_high_risk", "max")
        agg_dict["hours_high_risk_mean"] = ("hours_high_risk", "mean")

    if "wind_at_peak" in joined.columns:
        agg_dict["wind_at_peak_max"] = ("wind_at_peak", "max")
        agg_dict["wind_at_peak_mean"] = ("wind_at_peak", "mean")

    if "risk_start_hour_utc" in joined.columns:
        agg_dict["risk_start_hour_utc_min"] = ("risk_start_hour_utc", "min")

    if "risk_end_hour_utc" in joined.columns:
        agg_dict["risk_end_hour_utc_max"] = ("risk_end_hour_utc", "max")

    agg = group.agg(**agg_dict).reset_index()

    # Handle peak hour mode separately if column exists
    if "peak_hour_idx" in joined.columns:

        def get_mode(x):
            if len(x) == 0:
                return 0
            mode_vals = x.mode()
            return mode_vals.iloc[0] if len(mode_vals) > 0 else x.iloc[0]

        peak_hour_mode = group["peak_hour_idx"].agg(get_mode).reset_index()
        peak_hour_mode.columns = [area_id_col, "peak_hour_idx_mode"]
        agg = agg.merge(peak_hour_mode, on=area_id_col)

    # Convert peak_hour_idx to actual UTC hours
    if "peak_hour_idx_mode" in agg.columns:
        agg["peak_hour_utc"] = agg["peak_hour_idx_mode"] * 6

    def label(row):
        if row["storm_score_max"] > 1.5:
            return "High"
        if row["storm_score_max"] > 0.8:
            return "Medium"
        return "Low"

    agg["damage_risk"] = agg.apply(label, axis=1)

    return agg, area_id_col


def main():
    os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)

    print("Loading forecast...")
    ds = load_forecast()

    print("Computing storm score...")
    storm_score, max_wind, total_freeze_precip, combined_time, wind_time = (
        compute_storm_score(ds)
    )

    print("Computing temporal metrics...")
    # Use adaptive threshold based on data (80th percentile of storm scores)
    # This ensures we capture meaningful risk periods even for mild storms
    sample_scores = storm_score.values.flatten()
    adaptive_threshold = float(np.percentile(sample_scores[sample_scores > 0], 75))
    print(f"Using adaptive risk threshold: {adaptive_threshold:.3f}")
    (hours_high_risk, risk_start_idx, risk_end_idx, peak_hour_idx, wind_at_peak) = (
        compute_temporal_metrics(
            combined_time, wind_time, risk_threshold=adaptive_threshold
        )
    )

    print("Converting grid to GeoDataFrame...")
    grid_gdf = grid_to_geodataframe(
        storm_score,
        max_wind,
        total_freeze_precip,
        hours_high_risk,
        peak_hour_idx,
        wind_at_peak,
        risk_start_idx,
        risk_end_idx,
    )
    grid_gdf.to_csv(OUTPUT_GRID_CSV, index=False)
    print(f"Saved grid hotspot data to {OUTPUT_GRID_CSV}")

    print("Aggregating to areas...")
    area_scores, area_id_col = aggregate_to_areas(grid_gdf, POLYGON_FILE)
    area_scores.to_csv(OUTPUT_AREAS_CSV, index=False)
    print(f"Saved area hotspot scores to {OUTPUT_AREAS_CSV}")

    print("Top hotspots (by storm_score_max):")
    print(area_scores.sort_values("storm_score_max", ascending=False).head(10))

    # Save metadata about this run
    meta = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "description": "FCN-based storm impact score over DFW for last forecast run",
        "time_slice_start": int(TIME_SLICE.start or 0),
        "time_slice_end": int(TIME_SLICE.stop or 0),
        "total_zips_analyzed": len(area_scores),
        "high_risk_count": len(area_scores[area_scores["damage_risk"] == "High"]),
        "max_storm_score": float(area_scores["storm_score_max"].max()),
    }
    meta_path = os.path.join(BASE_DIR, "outputs", "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved metadata to {meta_path}")

    # Update roof risk index database
    print("Updating roof risk index database...")
    try:
        from roof_risk_index import RoofRiskIndex

        risk_index = RoofRiskIndex()
        event_date = datetime.now().strftime("%Y-%m-%d")

        # Add each ZIP's storm data to risk index
        for _, row in area_scores.iterrows():
            zip_code = str(row[area_id_col])
            storm_data = {
                "storm_score_max": row.get("storm_score_max", 0),
                "storm_score_mean": row.get("storm_score_mean", 0),
                "max_wind_max": row.get("max_wind_max", 0),
                "hours_high_risk_max": row.get("hours_high_risk_max", 0),
                "damage_risk": row.get("damage_risk", "Low"),
            }

            event_weight = risk_index.add_storm_event(zip_code, event_date, storm_data)

            # Calculate and store cumulative risk
            cumulative_risk = risk_index.calculate_cumulative_risk(zip_code, event_date)

        # Get portfolio summary
        all_zips = area_scores[area_id_col].astype(str).tolist()
        portfolio_summary = risk_index.get_portfolio_risk_summary(all_zips, event_date)

        print(f"✅ Roof risk index updated:")
        print(f"   - Events recorded: {len(area_scores)}")
        print(
            f"   - High-risk ZIPs in portfolio: {portfolio_summary.get('high_risk_count', 0)}"
        )
        print(
            f"   - Average risk score: {portfolio_summary.get('avg_risk_score', 0):.1f}"
        )
        print(
            f"   - ZIPs needing inspection: {portfolio_summary.get('zips_needing_inspection', 0)}"
        )

    except Exception as e:
        print(f"⚠️  Could not update roof risk index: {str(e)}")
        print("   (This is optional - storm data still saved)")


if __name__ == "__main__":
    main()
