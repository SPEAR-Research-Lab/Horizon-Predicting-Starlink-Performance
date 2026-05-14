import argparse
from dataclasses import dataclass
import gc
import os
from typing import Any, Optional

from joblib import dump
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler

from config import EnumFiles, df_features_download, df_features_upload, logger, models_dir
from explain_model_feature_imp import plot_feature_importances_and_save
from utils import ModelType, add_weather_index, get_file_matchers


@dataclass(frozen=True)
class TargetFeatures:
    download_latency = "download_latency_ms"
    download_throughput = "download_throughput_mbps"


features = [
    "lat",
    "lon",
    "client_server_distance_km",
    "hour_with_minute",
    "day_of_week",
    "sat_density",
    "temperature_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
]


def prepare_data_for_target(
    training_data_dir: str,
    target: str,
    model_type: ModelType,
    file_matchers: list[str],
) -> pd.DataFrame:
    column_set = df_features_download if model_type == ModelType.DOWNLOAD else df_features_upload
    column_set_with_time = column_set.union({"test_time"})
    concatenated_df = None

    for file in os.listdir(training_data_dir):
        if (
            file.endswith(".csv")
            and model_type.value in file
            and any(matcher in file for matcher in file_matchers)
            and target in file
        ):
            logger.info(f"Loading file: {file}")
            df = pd.read_csv(
                os.path.join(training_data_dir, file), usecols=list(column_set_with_time), low_memory=False
            )

            for col in df.select_dtypes(include=["float64"]).columns:
                df[col] = df[col].astype("float32")

            concatenated_df = pd.concat([concatenated_df, df], ignore_index=True) if concatenated_df is not None else df

            del df
            gc.collect()

    if concatenated_df is None:
        raise ValueError(f"No files found for preparing {model_type.value} data.")

    logger.info(f"Concatenated df size before dropping NA: {concatenated_df.shape}")
    concatenated_df = concatenated_df.dropna().reset_index(drop=True)
    logger.info(f"Concatenated df size after dropping NA: {concatenated_df.shape}")

    concatenated_df["test_time"] = pd.to_datetime(concatenated_df["test_time"], format="mixed")
    initial_size = len(concatenated_df)

    if "latency" in target:
        concatenated_df = concatenated_df[
            (concatenated_df["test_time"] >= "2025-09-23") & (concatenated_df["test_time"] <= "2025-11-23 23:59:59")
        ].reset_index(drop=True)
        logger.info(f"Filtered latency data to Sep 23 - Nov 23: {initial_size} -> {len(concatenated_df)} rows")
    elif "throughput" in target:
        concatenated_df = concatenated_df[
            (concatenated_df["test_time"] >= "2025-01-01") & (concatenated_df["test_time"] <= "2025-11-23 23:59:59")
        ].reset_index(drop=True)
        logger.info(f"Filtered throughput data to Jan 1 - Nov 23: {initial_size} -> {len(concatenated_df)} rows")

    concatenated_df = concatenated_df.drop(columns=["test_time"])
    concatenated_df = add_weather_index(concatenated_df, target)
    if "weather_index" not in features:
        features.append("weather_index")
        for col in [
            "cloud_cover",
            "precipitation",
            "wind_speed_10m",
            "temperature_2m",
        ]:
            if col in features:
                features.remove(col)

    return concatenated_df


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return mae, rmse, r2


def build_model_artifacts(
    ensemble_rmse: float,
    gbr_rmse: float,
    rf_rmse: float,
    best_weight: float,
    model_name: str,
    target: str,
    gbr_full: Any,
    rf_full: Any,
    scaler_full: Any,
) -> tuple[str, str, tuple[Any, ...]]:
    model_tuple: tuple[Any, ...]
    if ensemble_rmse < min(gbr_rmse, rf_rmse):
        model_type_name = "ensemble"
        model_name_full = f"ensemble_model_{model_name}_rf_weight_{int(best_weight * 100):d}_{target}"
        importances = (1 - best_weight) * gbr_full.feature_importances_ + best_weight * rf_full.feature_importances_
        model_tuple = (gbr_full, rf_full, scaler_full)
    elif gbr_rmse < rf_rmse:
        model_type_name = "GBR"
        model_name_full = f"gbr_model_{model_name}_{target}"
        importances = gbr_full.feature_importances_
        model_tuple = (gbr_full, scaler_full)
    else:
        model_type_name = "RF"
        model_name_full = f"rf_model_{model_name}_{target}"
        importances = rf_full.feature_importances_
        model_tuple = (rf_full, scaler_full)

    plot_feature_importances_and_save(importances, list(rf_full.feature_names_in_), model_name_full, models_dir)

    return model_type_name, model_name_full, model_tuple


def train_target_model_and_evaluate(df: pd.DataFrame, target: str, model_name: str, save_model: bool) -> dict:
    logger.info(f"Starting model training for {target}...")
    y = df[target]
    X = df[features]

    logger.info("Step 1: Finding optimal weights with 80-20 split...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler_validation = RobustScaler()
    X_train_scaled = pd.DataFrame(scaler_validation.fit_transform(X_train), columns=X_train.columns)
    X_test_scaled = pd.DataFrame(scaler_validation.transform(X_test), columns=X_test.columns)

    gbr_validation = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
    )
    rf_validation = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)

    logger.info("Training GradientBoosting for validation...")
    gbr_validation.fit(X_train_scaled, y_train)
    gbr_pred = gbr_validation.predict(X_test_scaled)

    logger.info("Training RandomForest for validation...")
    rf_validation.fit(X_train_scaled, y_train)
    rf_pred = rf_validation.predict(X_test_scaled)

    logger.info(f"Optimizing ensemble weights for {target}...")
    best_weight = 0.5
    best_rmse = float("inf")
    for rf_weight in np.arange(0.05, 1, 0.05):
        gbr_weight = 1.0 - rf_weight
        ensemble_pred = rf_weight * rf_pred + gbr_weight * gbr_pred
        rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred))

        if rmse < best_rmse:
            best_rmse = rmse
            best_weight = float(rf_weight)

    logger.info(f"Best ensemble weights - RF: {best_weight:.2f}, GBR: {1 - best_weight:.2f}")
    final_pred = best_weight * rf_pred + (1 - best_weight) * gbr_pred

    gbr_mae, gbr_rmse, gbr_r2 = evaluate(y_test, gbr_pred)
    rf_mae, rf_rmse, rf_r2 = evaluate(y_test, rf_pred)
    ensemble_mae, ensemble_rmse, ensemble_r2 = evaluate(y_test, final_pred)

    stats = {
        "model_name": model_name,
        "gbr_mae": gbr_mae,
        "gbr_rmse": gbr_rmse,
        "gbr_r2": gbr_r2,
        "rf_mae": rf_mae,
        "rf_rmse": rf_rmse,
        "rf_r2": rf_r2,
        "rf_weight": best_weight,
        "gbr_weight": 1 - best_weight,
        "ensemble_mae": ensemble_mae,
        "ensemble_rmse": ensemble_rmse,
        "ensemble_r2": ensemble_r2,
    }

    if not save_model:
        build_model_artifacts(
            ensemble_rmse,
            gbr_rmse,
            rf_rmse,
            best_weight,
            model_name,
            target,
            gbr_validation,
            rf_validation,
            scaler_validation,
        )
        logger.info(f"Model training for {target} completed without saving the model.")
        return stats

    del X_train_scaled, X_test_scaled, y_train, y_test, gbr_pred, rf_pred, final_pred
    del gbr_validation, rf_validation, scaler_validation
    gc.collect()

    logger.info(f"Step 2: Retraining on 100% of data with weights RF={best_weight:.2f}, GBR={1 - best_weight:.2f}...")

    scaler_full = RobustScaler()
    X_scaled_full = pd.DataFrame(scaler_full.fit_transform(X), columns=X.columns)

    gbr_full = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
    )
    rf_full = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)

    logger.info("Training final GradientBoosting on 100% data...")
    gbr_full.fit(X_scaled_full, y)

    logger.info("Training final RandomForest on 100% data...")
    rf_full.fit(X_scaled_full, y)

    del X, y, X_scaled_full
    gc.collect()

    model_type_name, model_name_full, model_tuple = build_model_artifacts(
        ensemble_rmse,
        gbr_rmse,
        rf_rmse,
        best_weight,
        model_name,
        target,
        gbr_full,
        rf_full,
        scaler_full,
    )

    dump(model_tuple, os.path.join(models_dir, f"{model_name_full}.joblib"))
    logger.info(f"Saved {model_type_name} model (trained on 100% data) for {target}")

    gc.collect()
    return stats


def train_model(
    target: str,
    training_data_dir: str,
    save_model: bool,
    number_of_months: int,
    last_month: Optional[str] = None,
) -> None:
    model_type = ModelType.DOWNLOAD if "download" in target else ModelType.UPLOAD
    data_files = os.listdir(training_data_dir)
    file_matchers = get_file_matchers(data_files, model_type, number_of_months, last_month)
    df = prepare_data_for_target(training_data_dir, target, model_type, file_matchers)
    model_name = f"{target}_{number_of_months}m"
    logger.info(f"Training model for {target} with {number_of_months} months of data and matchers {file_matchers}")
    stats = train_target_model_and_evaluate(df, target, model_name, save_model)
    stats["data_dir"] = training_data_dir
    stats["target"] = target
    all_stats.append(stats)
    del df
    gc.collect()


all_stats: list[dict] = []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trains the models with the given configuration.")
    parser.add_argument(
        "--src",
        "-s",
        type=str,
        help="Source directory or file path containing raw CSV data",
    )
    parser.add_argument(
        "--download-latency-months", type=int, default=2, help="Number of months to use for the download latency model"
    )

    parser.add_argument(
        "--download-throughput-months",
        type=int,
        default=11,
        help="Number of months to use for the download throughput model",
    )

    parser.add_argument("--save-models", action="store_true", help="Whether to save the trained models or not")
    args = parser.parse_args()
    training_data_dir = args.src
    if not training_data_dir:
        logger.error("Source directory is required")
        raise ValueError("Source directory is required")

    train_model(
        TargetFeatures.download_latency,
        training_data_dir,
        args.save_models,
        args.download_latency_months,
    )
    train_model(
        TargetFeatures.download_throughput,
        training_data_dir,
        args.save_models,
        args.download_throughput_months,
    )

    stats_df = pd.DataFrame(all_stats)
    stats_df.to_csv(models_dir / EnumFiles.model_training_stats, index=False)
    logger.info("Saved training statistics.")
