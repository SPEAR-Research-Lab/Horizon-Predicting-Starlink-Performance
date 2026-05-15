import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import models_dir, logger

WEATHER_WEIGHTS = {
    "download_latency_ms": {"cloud_cover": 0.462, "precipitation": 0.232, "wind_speed_10m": 0.229, "temperature_2m": 0.077},
    "download_throughput_mbps": {"cloud_cover": 0.619, "precipitation": 0.289, "wind_speed_10m": 0.087, "temperature_2m": 0.005},
}


def find_model(target: str):
    matches = sorted(models_dir.glob(f"*_{target}.joblib"))
    if not matches:
        return None, None
    model_path = matches[-1]
    weight_match = re.search(r"rf_weight_(\d+)", model_path.name)
    rf_weight = int(weight_match.group(1)) / 100.0 if weight_match else 0.5
    return model_path, rf_weight


def compute_weather_index(df: pd.DataFrame, weights: dict) -> pd.Series:
    cloud_std = (df["cloud_cover"] - df["cloud_cover"].mean()) / (df["cloud_cover"].std() or 1)
    precip_std = (df["precipitation"] - df["precipitation"].mean()) / (df["precipitation"].std() or 1)
    wind_std = (df["wind_speed_10m"] - df["wind_speed_10m"].mean()) / (df["wind_speed_10m"].std() or 1)
    temp_std = (df["temperature_2m"] - df["temperature_2m"].mean()) / (df["temperature_2m"].std() or 1)
    return (
        weights["cloud_cover"] * cloud_std
        + weights["precipitation"] * precip_std
        + weights["wind_speed_10m"] * wind_std
        + weights["temperature_2m"] * temp_std
    )


def load_and_predict(model_path: Path, rf_weight: float, X: pd.DataFrame) -> np.ndarray:
    loaded = joblib.load(model_path, mmap_mode="r")
    gbr, rf, scaler = loaded
    X_scaled = scaler.transform(X)
    return rf_weight * rf.predict(X_scaled) + (1 - rf_weight) * gbr.predict(X_scaled)


def predict_file(input_csv: Path, output_csv: Path) -> None:
    df = pd.read_csv(input_csv)

    df["day_of_week"] = pd.to_datetime(df["Date"]).dt.dayofweek
    df["hour_with_minute"] = df["Hour"].astype(float)

    features = ["lat", "lon", "client_server_distance_km", "hour_with_minute", "day_of_week", "sat_density", "weather_index"]

    targets = ["download_latency_ms", "download_throughput_mbps"]
    for target in targets:
        logger.info(f"Predicting {target}...")
        df["weather_index"] = compute_weather_index(df, WEATHER_WEIGHTS[target])

        model_path, rf_weight = find_model(target)
        if model_path is None:
            logger.warning(f"No model found for {target}")
            continue
        logger.info(f"  Using {model_path.name} (rf_weight={rf_weight})")

        X = df[features]
        df[target] = load_and_predict(model_path, rf_weight, X)

    df.to_csv(output_csv, index=False)
    logger.info(f"Wrote predictions to {output_csv}")
