import json
from pathlib import Path

import pandas as pd

from . import logger

MAX_JSON_SIZE_MB = 50


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
    out = df.rename(columns={
        "download_latency_ms": "Pred_Latency",
        "download_throughput_mbps": "Pred_Throughput",
    })
    cols = ["lat", "lon", "Date", "Hour", "test_time", "hour_with_minute", "sat_density", "Pred_Latency", "Pred_Throughput", "color"]
    available = [c for c in cols if c in out.columns]
    out[available].to_json(out_json, orient="records")
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
            out[str(h3_index)] = [
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

        data = json.dumps(out)
        if len(data) > MAX_JSON_SIZE_MB * 1024 * 1024:
            _write_chunked(out, out_json)
        else:
            with open(out_json, "w") as f:
                f.write(data)
            logger.info(f"Wrote {out_json}")
    else:
        records = [
            {
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "date": str(row[date_col]) if date_col in df.columns else "",
                "hour": int(float(row[hour_col])) if hour_col in df.columns else 0,
                "latency": float(row["download_latency_ms"]),
                "throughput": float(row["download_throughput_mbps"]),
                "sat_density": int(row["sat_density"]) if "sat_density" in df.columns and pd.notna(row.get("sat_density")) else 0,
                "color": row["color"],
            }
            for _, row in df.iterrows()
        ]
        with open(out_json, "w") as f:
            json.dump(records, f)
        logger.info(f"Wrote {out_json}")


def _write_chunked(data: dict, out_json: Path) -> None:
    keys = list(data.keys())
    chunk_size = len(keys) // 4 + 1
    out_dir = out_json.parent
    stem = out_json.stem

    for i in range(4):
        chunk_keys = keys[i * chunk_size : (i + 1) * chunk_size]
        if not chunk_keys:
            break
        chunk = {k: data[k] for k in chunk_keys}
        chunk_path = out_dir / f"{stem}_part{i+1}.json"
        with open(chunk_path, "w") as f:
            json.dump(chunk, f)
        logger.info(f"Wrote {chunk_path}")
