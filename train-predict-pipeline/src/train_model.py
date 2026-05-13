"""
Horizon Model Training

Trains ensemble models (Random Forest + Gradient Boosting) on filtered measurement
data from weekly-measurements-collection/measurements/.

Usage:
    python -m src.train_model
    python -m src.train_model --data-dir /path/to/measurements
"""

import os
import gc
import argparse
from pathlib import Path
from enum import Enum

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from joblib import dump

from . import models_dir, logger

FEATURES = [
    'lat',
    'lon',
    'client_server_distance_km',
    'hour_with_minute',
    'day_of_week',
    'sat_density',
    'weather_index',
]

WEATHER_WEIGHTS = {
    "download_latency_ms": {"cloud_cover": 0.462, "precipitation": 0.232, "wind_speed_10m": 0.229, "temperature_2m": 0.077},
    "download_throughput_mbps": {"cloud_cover": 0.619, "precipitation": 0.289, "wind_speed_10m": 0.087, "temperature_2m": 0.005},
}

TARGETS = {
    "download_latency_ms": {
        "time_filter": ("2025-09-23", None),
        "months_label": "2m",
    },
    "download_throughput_mbps": {
        "time_filter": ("2025-01-01", None),
        "months_label": "11m",
    },
}


def add_weather_index(df: pd.DataFrame, target: str) -> pd.DataFrame:
    weights = WEATHER_WEIGHTS[target]
    for col in ['cloud_cover', 'precipitation', 'wind_speed_10m', 'temperature_2m']:
        df[f'{col}_std'] = (df[col] - df[col].mean()) / (df[col].std() or 1)
    df['weather_index'] = (
        weights['cloud_cover'] * df['cloud_cover_std']
        + weights['precipitation'] * df['precipitation_std']
        + weights['wind_speed_10m'] * df['wind_speed_10m_std']
        + weights['temperature_2m'] * df['temperature_2m_std']
    )
    df = df.drop(columns=[f'{c}_std' for c in ['cloud_cover', 'precipitation', 'wind_speed_10m', 'temperature_2m']])
    return df


def load_training_data(data_dir: Path, target: str) -> pd.DataFrame:
    """Load all measurement CSVs containing the target metric."""
    csv_files = sorted(data_dir.glob("*.csv"))
    keyword = "latency" if "latency" in target else "throughput"
    matching = [f for f in csv_files if keyword in f.name]

    if not matching:
        raise ValueError(f"No CSV files matching '{keyword}' found in {data_dir}")

    dfs = []
    for f in matching:
        logger.info(f"Loading {f.name}")
        df = pd.read_csv(f, low_memory=False)
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = df[col].astype('float32')
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(combined)} rows from {len(matching)} files")
    return combined


def prepare_data(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Filter by time range and add weather index."""
    df = df.dropna(subset=[target]).reset_index(drop=True)
    df = df[df[target] > 0].reset_index(drop=True)

    if 'test_time' in df.columns:
        df['test_time'] = pd.to_datetime(df['test_time'], format='mixed')
        start_date = TARGETS[target]["time_filter"][0]
        df = df[df['test_time'] >= start_date].reset_index(drop=True)
        df = df.drop(columns=['test_time'])

    df = add_weather_index(df, target)

    required = FEATURES + [target]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = df[required].dropna().reset_index(drop=True)
    logger.info(f"Prepared {len(df)} rows for {target}")
    return df


def train_and_save(df: pd.DataFrame, target: str) -> dict:
    """Train ensemble model with weight optimization, save to models_dir."""
    y = df[target]
    X = df[FEATURES]

    logger.info(f"Finding optimal ensemble weights (80/20 split)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = RobustScaler()
    X_train_s = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns)
    X_test_s = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns)

    gbr = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    rf = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)

    gbr.fit(X_train_s, y_train)
    rf.fit(X_train_s, y_train)

    gbr_pred = gbr.predict(X_test_s)
    rf_pred = rf.predict(X_test_s)

    best_weight, best_rmse = 0.5, float('inf')
    for w in np.arange(0.05, 1.0, 0.05):
        ensemble_pred = w * rf_pred + (1 - w) * gbr_pred
        rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred))
        if rmse < best_rmse:
            best_rmse = rmse
            best_weight = float(w)

    logger.info(f"Optimal weights: RF={best_weight:.2f}, GBR={1-best_weight:.2f}")

    final_pred = best_weight * rf_pred + (1 - best_weight) * gbr_pred
    mae = mean_absolute_error(y_test, final_pred)
    rmse = np.sqrt(mean_squared_error(y_test, final_pred))
    r2 = r2_score(y_test, final_pred)
    logger.info(f"Validation: MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.4f}")

    del X_train_s, X_test_s, gbr, rf, scaler
    gc.collect()

    logger.info(f"Retraining on 100% data...")
    scaler_full = RobustScaler()
    X_full = pd.DataFrame(scaler_full.fit_transform(X), columns=X.columns)

    gbr_full = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    rf_full = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)

    gbr_full.fit(X_full, y)
    rf_full.fit(X_full, y)

    months_label = TARGETS[target]["months_label"]
    model_name = f"ensemble_model_filtered_percentile_0-75_{months_label}_rf_weight_{int(best_weight*100)}_{target}"

    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"{model_name}.joblib"
    dump((gbr_full, rf_full, scaler_full), model_path, compress=0)
    logger.info(f"Saved: {model_path} ({model_path.stat().st_size / 1024**3:.1f} GB)")

    return {"target": target, "mae": mae, "rmse": rmse, "r2": r2, "rf_weight": best_weight, "model": model_name}


def run(data_dir: Path) -> None:
    """Run training for all targets."""
    logger.info("=" * 60)
    logger.info("HORIZON MODEL TRAINING")
    logger.info("=" * 60)

    all_stats = []
    for target in TARGETS:
        logger.info(f"\nTraining: {target}")
        df = load_training_data(data_dir, target)
        df = prepare_data(df, target)
        stats = train_and_save(df, target)
        all_stats.append(stats)
        del df
        gc.collect()

    stats_df = pd.DataFrame(all_stats)
    stats_path = models_dir / "model_training_stats.csv"
    stats_df.to_csv(stats_path, index=False)
    logger.info(f"\nTraining stats: {stats_path}")
    logger.info("TRAINING COMPLETE")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Horizon prediction models")
    default_data = Path(__file__).parent.parent.parent / "weekly-measurements-collection" / "measurements"
    parser.add_argument("--data-dir", type=Path, default=default_data, help="Directory with filtered measurement CSVs")
    args = parser.parse_args()

    if not args.data_dir.exists():
        logger.error(f"Data directory not found: {args.data_dir}")
        raise SystemExit(1)

    run(args.data_dir)
