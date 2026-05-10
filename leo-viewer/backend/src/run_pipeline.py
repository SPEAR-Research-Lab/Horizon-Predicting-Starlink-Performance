"""
Run the full Horizon prediction pipeline.

Generates adaptive hex centers, enriches with weather and satellite data,
runs ML predictions, and exports JSON files for the frontend.

Usage:
    python -m src.run_pipeline          (from leo-viewer/backend/)
    python leo-viewer/backend/src/run_pipeline.py  (from repo root)
"""

import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import sys

# Allow running from repo root or from backend/
if "leo-viewer/backend" not in str(Path.cwd()):
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.__init__ import data_dir, logger
from src.generate_adaptive_hex_centers import generate_adaptive_hex_centers
from src.predict import predict_file
from src.predicts_json import export_hex_json, export_dot_json

FRONTEND_PUBLIC = Path(__file__).parent.parent.parent / "frontend" / "public"

# Model training window — predictions use this date range
PREDICTION_DATES = [datetime.date(2025, 11, d) for d in range(24, 31)]
HOURS = list(range(24))


def generate_weather_and_satellites(hex_csv: Path, output_csv: Path) -> None:
    """Generate time-series data with estimated weather and satellite density."""
    hexes = pd.read_csv(hex_csv)
    lat_col = "lat" if "lat" in hexes.columns else "Latitude"
    lon_col = "lon" if "lon" in hexes.columns else "Longitude"

    rows = []
    for _, h in hexes.iterrows():
        for date in PREDICTION_DATES:
            for hour in HOURS:
                row = {
                    "lat": h[lat_col],
                    "lon": h[lon_col],
                    "Date": date.strftime("%Y-%m-%d"),
                    "Hour": hour,
                }
                if "h3Index" in hexes.columns:
                    row["h3Index"] = h["h3Index"]
                rows.append(row)

    df = pd.DataFrame(rows)
    abs_lat = df["lat"].abs()

    # November weather estimates by latitude band
    n = len(df)
    df["temperature_2m"] = np.where(
        abs_lat > 50, -5 + np.random.normal(0, 3, n),
        np.where(abs_lat > 30, 10 + np.random.normal(0, 4, n),
                 25 + np.random.normal(0, 3, n))
    )
    df["precipitation"] = np.random.exponential(0.5, n)
    df["cloud_cover"] = np.clip(np.random.normal(50, 25, n), 0, 100)
    df["wind_speed_10m"] = np.clip(np.random.exponential(8, n), 0, 40)

    # Satellite density estimate by latitude (Starlink coverage pattern)
    df["sat_density"] = np.where(
        abs_lat < 20, 12,
        np.where(abs_lat < 40, 18,
                 np.where(abs_lat < 60, 22,
                          np.where(abs_lat < 70, 16, 8)))
    )

    df.to_csv(output_csv, index=False)
    logger.info(f"Generated {len(df)} rows -> {output_csv}")


def run_pipeline() -> None:
    """Execute the full prediction pipeline."""
    logger.info("=" * 60)
    logger.info("HORIZON PREDICTION PIPELINE")
    logger.info("=" * 60)

    # Step 1: Generate adaptive hex centers
    logger.info("\n[1/5] Generating adaptive hex centers...")
    generate_adaptive_hex_centers()

    # Step 2: Generate weather + satellite data for each resolution
    logger.info("\n[2/5] Generating weather and satellite features...")
    input_files = {
        "hex_centers_res2.csv": "hex_centers_res2_weather_satellites.csv",
        "hex_centers_res3.csv": "hex_centers_res3_weather_satellites.csv",
        "hex_centers_res4.csv": "hex_centers_res4_weather_satellites.csv",
        "unique_lat_long_points.csv": "unique_lat_long_points_weather_satellites.csv",
    }
    for in_name, out_name in input_files.items():
        in_path = data_dir / in_name
        if in_path.exists():
            generate_weather_and_satellites(in_path, data_dir / out_name)

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
