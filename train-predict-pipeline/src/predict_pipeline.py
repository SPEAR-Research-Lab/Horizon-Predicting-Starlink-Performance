"""
Horizon Prediction Pipeline

One script to run on AWS weekly. Takes the fixed hex grid centers,
enriches them with current weather + satellite density, runs ML predictions,
and exports JSONs for the frontend.

Usage:
    python -m src.predict_pipeline
    python -m src.predict_pipeline --output ../leo-viewer/frontend/public
"""

import argparse
import datetime
import math
import time
from pathlib import Path

import pandas as pd
import numpy as np
import requests
from sgp4.api import Satrec, jday

from . import data_dir, output_dir, satellite_data_dir, root_dir, logger
from .predict import predict_file
from .predicts_json import export_hex_json, export_dot_json


RADIUS_KM = 580

HEX_FILES = [
    "hex_centers_res2.csv",
    "hex_centers_res3.csv",
    "hex_centers_res4.csv",
]


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def enrich_weather(input_csv: Path, output_csv: Path, forecast_days: int = 14) -> None:
    """Fetch Open-Meteo weather for each unique location and expand into time series."""
    df = pd.read_csv(input_csv)
    lat_col = "lat" if "lat" in df.columns else "Latitude"
    lon_col = "lon" if "lon" in df.columns else "Longitude"

    unique_locs = df[[lat_col, lon_col]].drop_duplicates()
    extra_cols = [c for c in df.columns if c not in (lat_col, lon_col)]

    results = []
    for _, loc in unique_locs.iterrows():
        lat, lon = loc[lat_col], loc[lon_col]
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "hourly": "temperature_2m,precipitation,cloud_cover,wind_speed_10m",
                    "forecast_days": forecast_days, "timezone": "UTC",
                },
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            hourly = resp.json()["hourly"]
            weather_df = pd.DataFrame({
                "datetime": pd.to_datetime(hourly["time"]),
                "temperature_2m": hourly["temperature_2m"],
                "precipitation": hourly["precipitation"],
                "cloud_cover": hourly["cloud_cover"],
                "wind_speed_10m": hourly["wind_speed_10m"],
            })
            weather_df["Date"] = weather_df["datetime"].dt.strftime("%Y-%m-%d")
            weather_df["Hour"] = weather_df["datetime"].dt.hour
            weather_df = weather_df.drop(columns=["datetime"])

            extras = df[(df[lat_col] == lat) & (df[lon_col] == lon)][extra_cols].iloc[0].to_dict() if extra_cols else {}
            for _, w in weather_df.iterrows():
                results.append({lat_col: lat, lon_col: lon, **extras, **w.to_dict()})
            time.sleep(0.25)
        except Exception as e:
            logger.warning(f"Weather fetch failed for ({lat},{lon}): {e}")

    pd.DataFrame(results).to_csv(output_csv, index=False)
    logger.info(f"  -> {output_csv} ({len(results)} rows)")


def enrich_satellites(input_csv: Path, output_csv: Path) -> None:
    """Compute satellite density from TLE data for each row."""
    df = pd.read_csv(input_csv)
    lat_col = "lat" if "lat" in df.columns else "Latitude"
    lon_col = "lon" if "lon" in df.columns else "Longitude"

    tle_files = sorted(satellite_data_dir.glob("*.tle")) if satellite_data_dir.exists() else []
    if not tle_files:
        df["sat_density"] = 18
        df.to_csv(output_csv, index=False)
        logger.warning("No TLE files found, using fallback sat_density=18")
        return

    tle_path = tle_files[-1]
    lines = [l.strip() for l in tle_path.read_text().splitlines() if l.strip()]
    sats = []
    for i in range(0, len(lines) - 2, 3):
        try:
            sats.append(Satrec.twoline2rv(lines[i + 1], lines[i + 2]))
        except Exception:
            continue
    logger.info(f"  Loaded {len(sats)} satellites from {tle_path.name}")

    unique_locs = df[[lat_col, lon_col]].drop_duplicates()
    now = datetime.datetime.utcnow()
    jd, fr = jday(now.year, now.month, now.day, now.hour, 0, 0)

    density_cache = {}
    for _, row in unique_locs.iterrows():
        lat, lon = row[lat_col], row[lon_col]
        key = (round(lat, 2), round(lon, 2))
        if key in density_cache:
            continue
        count = 0
        for sat in sats:
            e, r, _ = sat.sgp4(jd, fr)
            if e != 0:
                continue
            x, y, z = r
            r_mag = math.sqrt(x**2 + y**2 + z**2)
            sat_lat = math.degrees(math.asin(z / r_mag))
            sat_lon = math.degrees(math.atan2(y, x))
            gmst = 280.46061837 + 360.98564736629 * (jd + fr - 2451545.0)
            sat_lon = (sat_lon - gmst) % 360
            if sat_lon > 180:
                sat_lon -= 360
            if _haversine(lat, lon, sat_lat, sat_lon) <= RADIUS_KM:
                count += 1
        density_cache[key] = count

    df["sat_density"] = df.apply(
        lambda row: density_cache.get((round(row[lat_col], 2), round(row[lon_col], 2)), 18), axis=1
    )
    df.to_csv(output_csv, index=False)
    logger.info(f"  -> {output_csv}")


def run(output_path=None) -> None:
    target = output_path or output_dir
    target.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("HORIZON PREDICTION PIPELINE")
    logger.info("=" * 60)

    logger.info("\n[1/4] Enriching hex centers with weather data...")
    for fname in HEX_FILES:
        inpath = data_dir / fname
        if inpath.exists():
            outpath = data_dir / fname.replace(".csv", "_weather.csv")
            logger.info(f"  {fname}...")
            enrich_weather(inpath, outpath)

    logger.info("\n[2/4] Enriching with satellite density...")
    for fname in HEX_FILES:
        weather_fname = fname.replace(".csv", "_weather.csv")
        inpath = data_dir / weather_fname
        if inpath.exists():
            outpath = data_dir / weather_fname.replace("_weather.csv", "_weather_satellites.csv")
            logger.info(f"  {weather_fname}...")
            enrich_satellites(inpath, outpath)

    logger.info("\n[3/4] Running ML predictions...")
    for fname in HEX_FILES:
        inpath = data_dir / fname.replace(".csv", "_weather_satellites.csv")
        if inpath.exists():
            outpath = data_dir / fname.replace(".csv", "_weather_satellites_predictions.csv")
            predict_file(inpath, outpath)

    predictions_dir = Path("/tmp/predictions")
    dot_input = predictions_dir / "prediction_points_features.csv"
    dot_predictions_csv = data_dir / "dot_predictions.csv"
    if dot_input.exists():
        logger.info("  Predicting for dot/city points...")
        predict_file(dot_input, dot_predictions_csv)

    logger.info("\n[4/4] Exporting frontend JSONs...")
    for res in [2, 3, 4]:
        csv_path = data_dir / f"hex_centers_res{res}_weather_satellites_predictions.csv"
        if csv_path.exists():
            export_hex_json(csv_path, target / f"predicted_hex_res{res}.json")

    if dot_predictions_csv.exists():
        export_dot_json(dot_predictions_csv, target / "dot_predictions.json")

    logger.info("\n" + "=" * 60)
    logger.info(f"PIPELINE COMPLETE - Output: {target}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Horizon prediction pipeline")
    parser.add_argument("--output", type=Path, help="Output directory for JSON files")
    args = parser.parse_args()
    run(args.output)
