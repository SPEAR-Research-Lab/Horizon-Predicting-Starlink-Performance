"""
Horizon Prediction Pipeline

Generates predictions for the LEO-Viewer frontend:
1. Generate adaptive H3 hex centers based on training data density
2. Enrich with real-time weather data (Open-Meteo)
3. Enrich with satellite density (SGP4 orbital propagation)
4. Run ML ensemble predictions (latency + throughput)
5. Export colored JSON files for the map frontend

Usage:
    python -m src.predict_pipeline
    python -m src.predict_pipeline --output ../leo-viewer/frontend/public
"""

import argparse
import shutil
from pathlib import Path

from . import data_dir, models_dir, output_dir, logger
from .generate_adaptive_hex_centers import generate_adaptive_hex_centers
from .enrich_with_weather import enrich_weather
from .enrich_with_satellites import enrich_with_sat_density
from .predict import predict_file
from .predicts_json import export_hex_json, export_dot_json


def run(output_path: Path | None = None) -> None:
    target = output_path or output_dir
    target.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("HORIZON PREDICTION PIPELINE")
    logger.info("=" * 60)

    logger.info("\n[1/5] Generating adaptive hex centers...")
    generate_adaptive_hex_centers()

    logger.info("\n[2/5] Enriching with weather data...")
    weather_inputs = [
        "hex_centers_res2.csv",
        "hex_centers_res3.csv",
        "hex_centers_res4.csv",
        "unique_lat_long_points.csv",
    ]
    for fname in weather_inputs:
        inpath = data_dir / fname
        if inpath.exists():
            outpath = data_dir / fname.replace(".csv", "_weather.csv")
            logger.info(f"  {fname}...")
            enrich_weather(inpath, outpath)

    logger.info("\n[3/5] Enriching with satellite density...")
    sat_inputs = [
        "hex_centers_res2_weather.csv",
        "hex_centers_res3_weather.csv",
        "hex_centers_res4_weather.csv",
        "unique_lat_long_points_weather.csv",
    ]
    for fname in sat_inputs:
        inpath = data_dir / fname
        if inpath.exists():
            outpath = data_dir / fname.replace("_weather.csv", "_weather_satellites.csv")
            logger.info(f"  {fname}...")
            enrich_with_sat_density(inpath, outpath)

    logger.info("\n[4/5] Running ML predictions...")
    predict_inputs = [
        "hex_centers_res2_weather_satellites.csv",
        "hex_centers_res3_weather_satellites.csv",
        "hex_centers_res4_weather_satellites.csv",
        "unique_lat_long_points_weather_satellites.csv",
    ]
    for fname in predict_inputs:
        inpath = data_dir / fname
        if inpath.exists():
            outpath = data_dir / fname.replace(".csv", "_predictions.csv")
            predict_file(inpath, outpath)

    logger.info("\n[5/5] Exporting frontend JSONs...")
    for res in [2, 3, 4]:
        csv_path = data_dir / f"hex_centers_res{res}_weather_satellites_predictions.csv"
        if csv_path.exists():
            export_hex_json(csv_path, target / f"predicted_hex_res{res}.json")

    dot_csv = data_dir / "unique_lat_long_points_weather_satellites_predictions.csv"
    if dot_csv.exists():
        export_dot_json(dot_csv, target / "dot_predictions.json")

    logger.info("\n" + "=" * 60)
    logger.info(f"PIPELINE COMPLETE - Output: {target}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Horizon prediction pipeline")
    parser.add_argument("--output", type=Path, help="Output directory for JSON files")
    args = parser.parse_args()
    run(args.output)
