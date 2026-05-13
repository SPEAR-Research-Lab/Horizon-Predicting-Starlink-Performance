"""
Run the full Horizon prediction pipeline.

Generates adaptive hex centers, enriches with real weather data (Open-Meteo)
and real satellite density (SGP4 orbital propagation), runs ML predictions,
and exports JSON files for the frontend.

Usage:
    python -m src.run_pipeline          (from leo-viewer/backend/)
    python leo-viewer/backend/src/run_pipeline.py  (from repo root)
"""

import datetime
import math
from pathlib import Path

import numpy as np
import pandas as pd

import sys

if "leo-viewer/backend" not in str(Path.cwd()):
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.__init__ import data_dir, logger
from src.generate_adaptive_hex_centers import generate_adaptive_hex_centers
from src.predict import predict_file
from src.predicts_json import export_hex_json, export_dot_json

FRONTEND_PUBLIC = Path(__file__).parent.parent.parent / "frontend" / "public"

PREDICTION_DATES = [datetime.date(2025, 11, d) for d in range(24, 31)]
HOURS = list(range(24))

SAT_DATA_DIR = Path(__file__).parent.parent.parent.parent / "satellite-data" / "data"
RADIUS_KM = 580


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def tle_path_for_date(date: datetime.date) -> Path:
    """Get TLE file path for a date using DD-MM-YYYY.tle naming convention."""
    return SAT_DATA_DIR / f"{date.strftime('%d-%m-%Y')}.tle"


def load_tle_satellites(tle_path: Path):
    from sgp4.api import Satrec
    lines = [l.strip() for l in tle_path.read_text().splitlines() if l.strip()]
    sats = []
    for i in range(0, len(lines) - 2, 3):
        try:
            sats.append(Satrec.twoline2rv(lines[i + 1], lines[i + 2]))
        except Exception:
            continue
    return sats


def compute_sat_density(lat, lon, dt, sats):
    from sgp4.api import jday
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, 0, 0)
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
        dist = haversine(lat, lon, sat_lat, sat_lon)
        if dist <= RADIUS_KM:
            count += 1
    return count


def compute_sat_density_for_locations(unique_locs: pd.DataFrame, date: datetime.date, hour: int) -> dict:
    """Compute satellite density for unique locations at a specific time."""
    tle_path = tle_path_for_date(date)
    if not tle_path.exists():
        available = sorted(SAT_DATA_DIR.glob("*.tle"))
        if available:
            tle_path = available[-1]
        else:
            return {}

    sats = load_tle_satellites(tle_path)
    dt = datetime.datetime(date.year, date.month, date.day, hour)

    densities = {}
    for _, row in unique_locs.iterrows():
        key = (round(row["lat"], 4), round(row["lon"], 4))
        if key not in densities:
            densities[key] = compute_sat_density(row["lat"], row["lon"], dt, sats)
    return densities


def fetch_weather_for_locations(unique_locs: pd.DataFrame) -> dict:
    """Fetch real weather from Open-Meteo for unique locations."""
    import time
    import requests

    weather_cache = {}
    for _, row in unique_locs.iterrows():
        lat, lon = round(row["lat"], 2), round(row["lon"], 2)
        key = (lat, lon)
        if key in weather_cache:
            continue
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "hourly": "temperature_2m,precipitation,cloud_cover,wind_speed_10m",
                    "start_date": "2025-11-24", "end_date": "2025-11-30",
                    "timezone": "UTC",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()["hourly"]
                weather_cache[key] = {
                    "temperature_2m": data["temperature_2m"],
                    "precipitation": data["precipitation"],
                    "cloud_cover": data["cloud_cover"],
                    "wind_speed_10m": data["wind_speed_10m"],
                    "time": data["time"],
                }
            time.sleep(0.2)
        except Exception as e:
            logger.warning(f"Weather fetch failed for ({lat},{lon}): {e}")
    return weather_cache


def generate_enriched_data(hex_csv: Path, output_csv: Path, use_real_weather: bool = True, use_real_sats: bool = True) -> None:
    """Generate time-series data with real or estimated weather and satellite density."""
    hexes = pd.read_csv(hex_csv)
    lat_col = "lat" if "lat" in hexes.columns else "Latitude"
    lon_col = "lon" if "lon" in hexes.columns else "Longitude"

    unique_locs = hexes[[lat_col, lon_col]].drop_duplicates().rename(columns={lat_col: "lat", lon_col: "lon"})

    weather_cache = {}
    if use_real_weather:
        logger.info(f"  Fetching weather for {len(unique_locs)} locations...")
        weather_cache = fetch_weather_for_locations(unique_locs)
        logger.info(f"  Got weather for {len(weather_cache)} locations")

    sat_cache = {}
    if use_real_sats and SAT_DATA_DIR.exists():
        logger.info(f"  Computing satellite density for {len(unique_locs)} locations...")
        for date in PREDICTION_DATES:
            densities = compute_sat_density_for_locations(unique_locs, date, 12)
            for key, val in densities.items():
                sat_cache[(key, date.strftime("%Y-%m-%d"))] = val
        logger.info(f"  Computed {len(sat_cache)} sat density values")

    rows = []
    for _, h in hexes.iterrows():
        lat, lon = h[lat_col], h[lon_col]
        weather_key = (round(lat, 2), round(lon, 2))
        weather = weather_cache.get(weather_key)

        for di, date in enumerate(PREDICTION_DATES):
            date_str = date.strftime("%Y-%m-%d")
            sat_key = ((round(lat, 4), round(lon, 4)), date_str)
            sat_density = sat_cache.get(sat_key, 18)  # fallback

            for hour in HOURS:
                row = {"lat": lat, "lon": lon, "Date": date_str, "Hour": hour}
                if "h3Index" in hexes.columns:
                    row["h3Index"] = h["h3Index"]

                hour_idx = di * 24 + hour
                if weather and hour_idx < len(weather["temperature_2m"]):
                    row["temperature_2m"] = weather["temperature_2m"][hour_idx]
                    row["precipitation"] = weather["precipitation"][hour_idx]
                    row["cloud_cover"] = weather["cloud_cover"][hour_idx]
                    row["wind_speed_10m"] = weather["wind_speed_10m"][hour_idx]
                else:
                    abs_lat = abs(lat)
                    row["temperature_2m"] = -2 if abs_lat > 50 else (12 if abs_lat > 30 else 26)
                    row["precipitation"] = 0.3
                    row["cloud_cover"] = 45
                    row["wind_speed_10m"] = 10

                row["sat_density"] = sat_density
                rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    logger.info(f"  -> {output_csv} ({len(df)} rows)")


def run_pipeline() -> None:
    """Execute the full prediction pipeline."""
    logger.info("=" * 60)
    logger.info("HORIZON PREDICTION PIPELINE")
    logger.info("=" * 60)

    # Step 1: Generate adaptive hex centers
    logger.info("\n[1/5] Generating adaptive hex centers...")
    generate_adaptive_hex_centers()

    # Step 2: Enrich with real weather + satellite data
    logger.info("\n[2/5] Enriching with weather and satellite data...")
    input_files = {
        "hex_centers_res2.csv": "hex_centers_res2_weather_satellites.csv",
        "hex_centers_res3.csv": "hex_centers_res3_weather_satellites.csv",
        "hex_centers_res4.csv": "hex_centers_res4_weather_satellites.csv",
        "unique_lat_long_points.csv": "unique_lat_long_points_weather_satellites.csv",
    }
    for in_name, out_name in input_files.items():
        in_path = data_dir / in_name
        if in_path.exists():
            logger.info(f"  Processing {in_name}...")
            generate_enriched_data(in_path, data_dir / out_name)

    # Step 3: Run ML predictions
    logger.info("\n[3/5] Running ML predictions...")
    prediction_files = {
        "hex_centers_res2_weather_satellites.csv": "hex_centers_res2_weather_satellites_predictions.csv",
        "hex_centers_res3_weather_satellites.csv": "hex_centers_res3_weather_satellites_predictions.csv",
        "hex_centers_res4_weather_satellites.csv": "hex_centers_res4_weather_satellites_predictions.csv",
        "unique_lat_long_points_weather_satellites.csv": "unique_lat_long_points_weather_satellites_predictions.csv",
    }
    for in_name, out_name in prediction_files.items():
        in_path = data_dir / in_name
        if in_path.exists():
            predict_file(in_path, data_dir / out_name)

    # Step 4: Export frontend JSONs
    logger.info("\n[4/5] Exporting frontend JSON files...")
    FRONTEND_PUBLIC.mkdir(parents=True, exist_ok=True)
    for res in [2, 3, 4]:
        csv_path = data_dir / f"hex_centers_res{res}_weather_satellites_predictions.csv"
        if csv_path.exists():
            export_hex_json(csv_path, FRONTEND_PUBLIC / f"predicted_hex_res{res}.json")

    dot_csv = data_dir / "unique_lat_long_points_weather_satellites_predictions.csv"
    if dot_csv.exists():
        export_dot_json(dot_csv, FRONTEND_PUBLIC / "dot_predictions.json")

    # Step 5: Create combined hexagon_centers.csv
    logger.info("\n[5/5] Creating combined hexagon_centers.csv...")
    dfs = []
    for res in [2, 3, 4]:
        f = data_dir / f"hex_centers_res{res}.csv"
        if f.exists():
            df = pd.read_csv(f)
            df["resolution"] = res
            dfs.append(df)
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        combined[["h3Index", "lat", "lon", "resolution"]].to_csv(
            data_dir / "hexagon_centers.csv", index=False
        )
        logger.info(f"hexagon_centers.csv: {len(combined)} total hexes")

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
