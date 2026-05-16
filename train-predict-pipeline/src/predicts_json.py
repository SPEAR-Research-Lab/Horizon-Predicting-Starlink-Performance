import json
from pathlib import Path

import pandas as pd

from . import output_dir, logger


def performance_color(latency: float, throughput: float) -> str:
    if throughput < 10 or latency > 300:
        return "#800026"
    elif throughput < 20 or latency > 200:
        return "#d73027"
    elif throughput < 30 or latency > 150:
        return "#fc8d59"
    elif throughput < 45 or latency > 110:
        return "#fee08b"
    elif throughput < 60 or latency > 85:
        return "#d9ef8b"
    elif throughput < 80 or latency > 65:
        return "#91cf60"
    else:
        return "#1a9850"


def export_dot_json(csv_path: Path, out_json: Path) -> None:
    df = pd.read_csv(csv_path)
    df["color"] = df.apply(lambda row: performance_color(row["download_latency_ms"], row["download_throughput_mbps"]), axis=1)
    out = df.rename(
        columns={
            "download_latency_ms": "Pred_Latency",
            "download_throughput_mbps": "Pred_Throughput",
        }
    )
    cols = ["lat", "lon", "Date", "Hour", "sat_density", "Pred_Latency", "Pred_Throughput", "color"]
    available = [c for c in cols if c in out.columns]
    out[available].to_json(out_json, orient="records", indent=2)
    logger.info(f"Wrote {out_json}")


def export_hex_json(csv_path: Path, out_json: Path) -> None:
    df = pd.read_csv(csv_path)
    df["color"] = df.apply(lambda row: performance_color(row["download_latency_ms"], row["download_throughput_mbps"]), axis=1)

    date_col = "Date" if "Date" in df.columns else "test_time"
    hour_col = "Hour" if "Hour" in df.columns else "hour_with_minute"

    h3_col = "h3Index" if "h3Index" in df.columns else "h3_index" if "h3_index" in df.columns else None

    if h3_col:
        out = {}
        for h3_index, group in df.groupby(h3_col):
            out[h3_index] = [
                {
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "date": str(row[date_col]),
                    "hour": int(float(row[hour_col])),
                    "latency": float(row["download_latency_ms"]),
                    "throughput": float(row["download_throughput_mbps"]),
                    "sat_density": int(row["sat_density"]) if pd.notna(row.get("sat_density")) else 0,
                    "color": row["color"],
                }
                for _, row in group.iterrows()
            ]
        with open(out_json, "w") as f:
            json.dump(out, f)
    else:
        records = []
        for _, row in df.iterrows():
            records.append({
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "date": str(row[date_col]) if date_col in df.columns else "",
                "hour": int(float(row[hour_col])) if hour_col in df.columns else 0,
                "latency": float(row["download_latency_ms"]),
                "throughput": float(row["download_throughput_mbps"]),
                "sat_density": int(row["sat_density"]) if "sat_density" in df.columns and pd.notna(row.get("sat_density")) else 0,
                "color": row["color"],
            })
        with open(out_json, "w") as f:
            json.dump(records, f)

    logger.info(f"Wrote {out_json}")
    with open(out_json, "w") as f:
        json.dump(out, f)
    logger.info(f"Wrote {out_json}")


RESOLUTION_FILES = {
    2: "hex_centers_res2_weather_satellites_predictions.csv",
    3: "hex_centers_res3_weather_satellites_predictions.csv",
    4: "hex_centers_res4_weather_satellites_predictions.csv",
}


DOT_PREDICTIONS_FILE = "unique_lat_long_points_weather_satellites_predictions.csv"


if __name__ == "__main__":
    for res, fname in RESOLUTION_FILES.items():
        csv_path = output_dir / fname
        if csv_path.exists():
            json_path = output_dir / f"predicted_hex_res{res}.json"
            export_hex_json(csv_path, json_path)
        else:
            logger.warning(f"Skipping {csv_path} (not found)")

    dot_csv = output_dir / DOT_PREDICTIONS_FILE
    if dot_csv.exists():
        dot_json = output_dir / "dot_predictions.json"
        export_dot_json(dot_csv, dot_json)
    else:
        logger.warning(f"Skipping {dot_csv} (not found)")
