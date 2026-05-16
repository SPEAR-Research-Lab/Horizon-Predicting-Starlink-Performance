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

HEX_FILES = {
    2: "hex_centers_res2_features.csv",
    3: "hex_centers_res3_features.csv",
    4: "hex_centers_res4_features.csv",
}
DOT_FILE = "prediction_points_features.csv"
FALLBACK_HEX = "hexagon_centers_features.csv"


def run(output_path=None) -> None:
    target = output_path or output_dir
    target.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("HORIZON PREDICTION PIPELINE")
    logger.info("=" * 60)

    logger.info("\n[1/2] Running ML predictions...")

    hex_found = False
    for res, fname in HEX_FILES.items():
        hex_input = PREDICTIONS_DIR / fname
        if hex_input.exists():
            hex_found = True
            hex_output = Path(f"/tmp/hex_predictions_res{res}.csv")
            logger.info(f"  Predicting for hex res{res}...")
            predict_file(hex_input, hex_output)

    if not hex_found:
        fallback = PREDICTIONS_DIR / FALLBACK_HEX
        if fallback.exists():
            logger.info(f"  Predicting for combined hexagons (fallback)...")
            predict_file(fallback, Path("/tmp/hex_predictions_res2.csv"))
            hex_found = True

    dot_input = PREDICTIONS_DIR / DOT_FILE
    dot_output = Path("/tmp/dot_predictions.csv")
    if dot_input.exists():
        logger.info(f"  Predicting for dot/city points...")
        predict_file(dot_input, dot_output)

    logger.info("\n[2/2] Exporting frontend JSONs...")

    for res in [2, 3, 4]:
        hex_csv = Path(f"/tmp/hex_predictions_res{res}.csv")
        if hex_csv.exists():
            export_hex_json(hex_csv, target / f"predicted_hex_res{res}.json")

    if dot_output.exists():
        export_dot_json(dot_output, target / "dot_predictions.json")

    logger.info("\n" + "=" * 60)
    logger.info(f"PIPELINE COMPLETE - Output: {target}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Horizon prediction pipeline")
    parser.add_argument("--output", type=Path, help="Output directory for JSON files")
    args = parser.parse_args()
    run(args.output)
