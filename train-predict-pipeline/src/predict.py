import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import data_dir, models_dir, logger

MODEL_CONFIGS = {
    "download_latency_ms": {
        "path": models_dir / "ensemble_model_filtered_percentile_0-75_2m_rf_weight_55_download_latency_ms.joblib",
        "rf_weight": 0.55,
        "weather_weights": {"cloud_cover": 0.462, "precipitation": 0.232, "wind_speed_10m": 0.229, "temperature_2m": 0.077},
    },
    "download_throughput_mbps": {
        "path": models_dir / "ensemble_model_filtered_isolation_forest_0-75_11m_rf_weight_40_download_throughput_mbps.joblib",
        "rf_weight": 0.40,
        "weather_weights": {"cloud_cover": 0.619, "precipitation": 0.289, "wind_speed_10m": 0.087, "temperature_2m": 0.005},
    },
}

SERVER_LOCATIONS = data_dir / "server_locations.csv"
WORLD_COORDS = data_dir / "world_cities_coordinates.csv"

WEATHER_COLS = ["cloud_cover", "temperature_2m", "wind_speed_10m", "precipitation"]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_server_coordinates() -> list[dict]:
    servers = pd.read_csv(SERVER_LOCATIONS)
    coords = pd.read_csv(WORLD_COORDS)

    coords["city_key"] = coords["city"].astype(str).str.strip()
    coords["country_key"] = coords["country"].astype(str).str.strip().str.upper()
    servers["server_city_key"] = servers["server_city"].astype(str).str.strip()
    servers["server_country_key"] = servers["server_country_code"].astype(str).str.strip().str.upper()

    merged = servers.merge(
        coords,
        left_on=["server_city_key", "server_country_key"],
        right_on=["city_key", "country_key"],
        how="left",
    )
    merged = merged[["server_city", "server_country_code", "lat", "lng"]].rename(columns={"lng": "lon"})
    merged = merged.dropna(subset=["lat", "lon"])
    return merged.to_dict("records")


_server_list: list[dict] | None = None


def get_server_list() -> list[dict]:
    global _server_list
    if _server_list is None:
        _server_list = load_server_coordinates()
    return _server_list


def find_nearest_server_distance(lat: float, lon: float) -> float:
    servers = get_server_list()
    best_dist = float("inf")
    for s in servers:
        dist = haversine(lat, lon, s["lat"], s["lon"])
        if dist < best_dist:
            best_dist = dist
    return best_dist


def add_nearest_server_distances(df: pd.DataFrame) -> pd.DataFrame:
    servers = get_server_list()
    server_lats = np.array([s["lat"] for s in servers])
    server_lons = np.array([s["lon"] for s in servers])

    distances = []
    for _, row in df.iterrows():
        dists = [haversine(row["lat"], row["lon"], slat, slon) for slat, slon in zip(server_lats, server_lons)]
        distances.append(min(dists))
    df["client_server_distance_km"] = distances
    return df


def compute_weather_index(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
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


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df["day_of_week"] = pd.to_datetime(df["Date"]).dt.dayofweek
    df["hour_with_minute"] = df["Hour"].astype(float)
    return df


def load_and_predict(model_path: Path, rf_weight: float, X: pd.DataFrame) -> np.ndarray:
    loaded = joblib.load(model_path, mmap_mode="r")
    gbr, rf, scaler = loaded
    X_scaled = scaler.transform(X)
    return rf_weight * rf.predict(X_scaled) + (1 - rf_weight) * gbr.predict(X_scaled)


def predict_file(input_csv: Path, output_csv: Path) -> None:
    df = pd.read_csv(input_csv)

    if "Latitude" in df.columns:
        df = df.rename(columns={"Latitude": "lat", "Longitude": "lon"})

    df = add_time_features(df)

    if "client_server_distance_km" not in df.columns:
        logger.info("Computing nearest server distances...")
        df = add_nearest_server_distances(df)

    if "sat_density" not in df.columns and "SatDensity" in df.columns:
        df = df.rename(columns={"SatDensity": "sat_density"})

    features = ["lat", "lon", "client_server_distance_km", "hour_with_minute", "day_of_week", "sat_density", "weather_index"]

    for target, config in MODEL_CONFIGS.items():
        logger.info(f"Predicting {target}...")
        df["weather_index"] = compute_weather_index(df, config["weather_weights"])

        if not config["path"].exists():
            logger.warning(f"Model not found: {config['path']}")
            continue

        X = df[features]
        df[target] = load_and_predict(config["path"], config["rf_weight"], X)

    df.to_csv(output_csv, index=False)
    logger.info(f"Wrote predictions to {output_csv}")
