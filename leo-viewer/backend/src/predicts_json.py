import json
from pathlib import Path

import pandas as pd

from .__init__ import data_dir, logger

FRONTEND_PUBLIC = Path(__file__).parent.parent.parent / "frontend" / "public"


def performance_color(latency: float, throughput: float) -> str:
    if throughput < 10:
        return "#800026"
    if latency > 300 or throughput < 20:
        return "#800026"
    elif latency > 220 or throughput < 35:
        return "#d73027"
    elif latency > 170 or throughput < 50:
        return "#fc8d59"
    elif latency > 130 or throughput < 75:
        return "#fee08b"
    elif latency > 100 or throughput < 120:
        return "#d9ef8b"
    elif latency > 70 or throughput < 200:
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

    out: dict[str, list] = {}
    for h3_index, group in df.groupby("h3Index"):
        out[h3_index] = [
            {
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "date": str(row["Date"]),
                "hour": int(row["Hour"]),
                "latency": float(row["download_latency_ms"]),
                "throughput": float(row["download_throughput_mbps"]),
                "sat_density": int(row["sat_density"]) if pd.notna(row.get("sat_density")) else 0,
                "color": row["color"],
            }
            for _, row in group.iterrows()
        ]
    with open(out_json, "w") as f:
        json.dump(out, f)
    logger.info(f"Wrote {out_json}")


RESOLUTION_FILES = {
    2: "hex_centers_res2_weather_satellites_predictions.csv",
    3: "hex_centers_res3_weather_satellites_predictions.csv",
    4: "hex_centers_res4_weather_satellites_predictions.csv",
}


if __name__ == "__main__":
    for res, fname in RESOLUTION_FILES.items():
        csv_path = data_dir / fname
        if csv_path.exists():
            json_path = FRONTEND_PUBLIC / f"predicted_hex_res{res}.json"
            export_hex_json(csv_path, json_path)
        else:
            logger.warning(f"Skipping {csv_path} (not found)")
