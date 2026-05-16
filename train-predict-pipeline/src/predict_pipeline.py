"""
Horizon Prediction Pipeline

Downloads pre-enriched CSVs from S3, runs ML predictions, exports JSONs.
All enrichment (weather, sat density, distance) is done by weekly-measurements-collection.

Usage:
    python -m src.predict_pipeline --output ../leo-viewer/frontend/public
"""

import argparse
from pathlib import Path

from . import output_dir, logger
from .predict import predict_file
from .predicts_json import export_hex_json, export_dot_json

PREDICTIONS_DIR = Path("/tmp/predictions")


def run(output_path=None) -> None:
    target = output_path or output_dir
    target.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("HORIZON PREDICTION PIPELINE")
    logger.info("=" * 60)

    hex_input = PREDICTIONS_DIR / "hexagon_centers_features.csv"
    dot_input = PREDICTIONS_DIR / "prediction_points_features.csv"

    logger.info("\n[1/2] Running ML predictions...")

    hex_predictions_csv = Path("/tmp/hex_predictions.csv")
    if hex_input.exists():
        logger.info(f"  Predicting for hexagon centers...")
        predict_file(hex_input, hex_predictions_csv)
    else:
        logger.error(f"  {hex_input} not found!")

    dot_predictions_csv = Path("/tmp/dot_predictions.csv")
    if dot_input.exists():
        logger.info(f"  Predicting for dot/city points...")
        predict_file(dot_input, dot_predictions_csv)
    else:
        logger.warning(f"  {dot_input} not found, skipping dots")

    logger.info("\n[2/2] Exporting frontend JSONs...")

    if hex_predictions_csv.exists():
        export_hex_json(hex_predictions_csv, target / "predicted_hex_res2.json")

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
