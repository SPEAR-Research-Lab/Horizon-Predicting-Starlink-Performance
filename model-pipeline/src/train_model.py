import os
from typing import Any, Optional
import pandas as pd
import gc
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from joblib import dump
from constants import models_dir, filtration_dir_base, root_dir, df_features_download, df_features_upload
from utils import get_file_matchers, ModelType, add_weather_index
from explain_model_feature_imp import plot_feature_importances_and_save
from pathlib import Path
from typing import Optional
from custom_types import TargetConfig

features = [
    'lat',
    'lon',
    'client_server_distance_km',
    'hour_with_minute',
    'day_of_week',
    'sat_density',
    'temperature_2m',
    'precipitation',
    'cloud_cover',
    'wind_speed_10m',
]

def prepare_data_for_target(path_to_training_data: Path, target: str, model_type: ModelType, file_matchers: list[str],
                            useWeatherIndex: bool) -> pd.DataFrame:
    column_set = df_features_download if model_type == ModelType.DOWNLOAD else df_features_upload
    column_set_with_time = column_set.union({'test_time'})
    concatenated_df = None

    for file in os.listdir(path_to_training_data):
        if file.endswith(".csv") and model_type.value in file and any(matcher in file for matcher in file_matchers) \
                and target in file:
            print(f"Loading file: {file}")
            file_path = path_to_training_data / file
            df = pd.read_csv(file_path, usecols=list(column_set_with_time), low_memory=False)

            for col in df.select_dtypes(include=['float64']).columns:
                df[col] = df[col].astype('float32')

            concatenated_df = pd.concat([concatenated_df, df], ignore_index=True) if concatenated_df is not None else df

            del df
            gc.collect()

    if concatenated_df is None:
        raise ValueError(f"No files found for preparing {model_type.value} data.")

    print("Concatenated df size before dropping NA:", concatenated_df.shape)
    concatenated_df = concatenated_df.dropna().reset_index(drop=True)
    print("Concatenated df size after dropping NA:", concatenated_df.shape)

    concatenated_df['test_time'] = pd.to_datetime(concatenated_df['test_time'], format='mixed')
    initial_size = len(concatenated_df)

    if 'latency' in target:
        concatenated_df = concatenated_df[
            (concatenated_df['test_time'] >= '2025-09-23') &
            (concatenated_df['test_time'] <= '2025-11-23 23:59:59')
        ].reset_index(drop=True)
        print(f"Filtered latency data to Sep 23 - Nov 23: {initial_size} -> {len(concatenated_df)} rows")
    elif 'throughput' in target:
        concatenated_df = concatenated_df[
            (concatenated_df['test_time'] >= '2025-01-01') &
            (concatenated_df['test_time'] <= '2025-11-23 23:59:59')
        ].reset_index(drop=True)
        print(f"Filtered throughput data to Jan 1 - Nov 23: {initial_size} -> {len(concatenated_df)} rows")

    concatenated_df = concatenated_df.drop(columns=['test_time'])

    if useWeatherIndex:
        concatenated_df = add_weather_index(concatenated_df, target)
        if 'weather_index' not in features:
            features.append('weather_index')
            for col in ['cloud_cover', 'precipitation', 'wind_speed_10m', 'temperature_2m']:
                if col in features:
                    features.remove(col)

    return concatenated_df


def evaluate(y_true, y_pred):
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


def train_target_model_and_evaluate(df: pd.DataFrame, target: str, model_name: str, save_model=False) -> dict:
    print(f"Starting model training for {target}...")
    y = df[target]
    X = df[features]

    print(f"Step 1: Finding optimal weights with 80-20 split...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler_validation = RobustScaler()
    X_train_scaled = pd.DataFrame(scaler_validation.fit_transform(X_train), columns=X_train.columns)
    X_test_scaled = pd.DataFrame(scaler_validation.transform(X_test), columns=X_test.columns)

    gbr_validation = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
    )
    rf_validation = RandomForestRegressor(
        n_estimators=100,
        n_jobs=-1,
        random_state=42
    )

    print(f"Training GradientBoosting for validation...")
    gbr_validation.fit(X_train_scaled, y_train)
    gbr_pred = gbr_validation.predict(X_test_scaled)

    print(f"Training RandomForest for validation...")
    rf_validation.fit(X_train_scaled, y_train)
    rf_pred = rf_validation.predict(X_test_scaled)

    print(f"Optimizing ensemble weights for {target}...")
    best_weight = 0.5
    best_rmse = float('inf')
    for rf_weight in np.arange(0.05, 1, 0.05):
        gbr_weight = 1.0 - rf_weight
        ensemble_pred = rf_weight * rf_pred + gbr_weight * gbr_pred
        rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred))

        if rmse < best_rmse:
            best_rmse = rmse
            best_weight = float(rf_weight)

    print(f"Best ensemble weights - RF: {best_weight:.2f}, GBR: {1 - best_weight:.2f}")
    final_pred = best_weight * rf_pred + (1 - best_weight) * gbr_pred

    gbr_mae, gbr_rmse, gbr_r2 = evaluate(y_test, gbr_pred)
    rf_mae, rf_rmse, rf_r2 = evaluate(y_test, rf_pred)
    ensemble_mae, ensemble_rmse, ensemble_r2 = evaluate(y_test, final_pred)

    stats = {
        'model_name': model_name,
        'gbr_mae': gbr_mae,
        'gbr_rmse': gbr_rmse,
        'gbr_r2': gbr_r2,
        'rf_mae': rf_mae,
        'rf_rmse': rf_rmse,
        'rf_r2': rf_r2,
        'rf_weight': best_weight,
        'gbr_weight': 1 - best_weight,
        'ensemble_mae': ensemble_mae,
        'ensemble_rmse': ensemble_rmse,
        'ensemble_r2': ensemble_r2,
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
        print(f"Model training for {target} completed without saving the model.")
        return stats


    del X_train_scaled, X_test_scaled, y_train, y_test, gbr_pred, rf_pred, final_pred
    del gbr_validation, rf_validation, scaler_validation
    gc.collect()

    print(f"Step 2: Retraining on 100% of data with weights RF={best_weight:.2f}, GBR={1-best_weight:.2f}...")

    scaler_full = RobustScaler()
    X_scaled_full = pd.DataFrame(scaler_full.fit_transform(X), columns=X.columns)

    gbr_full = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        random_state=42,
    )
    rf_full = RandomForestRegressor(
        n_estimators=100,
        n_jobs=-1,
        random_state=42
    )

    print(f"Training final GradientBoosting on 100% data...")
    gbr_full.fit(X_scaled_full, y)

    print(f"Training final RandomForest on 100% data...")
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
    print(f"Saved {model_type_name} model (trained on 100% data) for {target}")

    gc.collect()
    return stats

months_to_use = [3]
use_weather_index = True

targets: dict[str, TargetConfig] = {
    "download_latency_ms": {
        'preferred_filtration': 'percentile_0.75',
        'preferred_months': [2],
        'save_model': True,
    },
    "download_throughput_mbps": {
        'preferred_filtration': 'isolation_forest_0.75',
        'preferred_months': [11],
        'save_model': True,
    },
}
all_stats = []


def train_model(target: str, data_dir: str, useWeatherIndex: bool, save_model: bool, number_of_months=3,
                last_month: Optional[str] = None) -> None:
    from pathlib import Path as PathLib
    model_type = ModelType.DOWNLOAD if 'download' in target else ModelType.UPLOAD
    data_path = PathLib(data_dir) if os.path.isabs(data_dir) else root_dir / data_dir
    data_files = os.listdir(data_path)
    file_matchers = get_file_matchers(data_files, model_type, number_of_months, last_month)
    df = prepare_data_for_target(data_path, target, model_type, file_matchers, useWeatherIndex)
    dir_name = os.path.basename(str(data_path).rstrip('/'))
    model_name = f"{dir_name.replace('.', '-')}_{number_of_months}m"
    print(f"Training model for {target} with {number_of_months} months of data and matchers {file_matchers}")
    stats = train_target_model_and_evaluate(df, target, model_name, save_model)
    stats['data_dir'] = data_dir
    stats['target'] = target
    all_stats.append(stats)
    del df
    gc.collect()


if __name__ == "__main__":
    from pathlib import Path as PathLib
    script_dir = PathLib(__file__).parent.absolute()
    project_root = script_dir.parent
    train_data_dir = project_root / 'data' / 'train-data'
    models_output_dir = project_root / 'models'
    os.makedirs(models_output_dir, exist_ok=True)

    data_dirs = [entry.name for entry in os.scandir(train_data_dir)
                 if entry.is_dir() and any(filt in entry.name for filt in filtration_dir_base)]

    for target, config in targets.items():
        preferred_months = config.get('preferred_months')
        months_list = preferred_months if preferred_months else months_to_use

        if (preferred_filtration := config.get('preferred_filtration')) is not None:
            data_dir = next((d for d in data_dirs if preferred_filtration in d), None)
            if data_dir is None:
                raise ValueError(f"No data directory found for filtration {preferred_filtration} and target {target}.")
            print(f"Using preferred data directory {data_dir} for target {target}.")
            dirs_to_process = [data_dir]
        else:
            print(f"No preferred filtration for target {target}, training on all data dirs.")
            dirs_to_process = data_dirs

        for data_dir in dirs_to_process:
            for months in months_list:
                train_model(target, f'data/train-data/{data_dir}', use_weather_index, config['save_model'], number_of_months=months)
    stats_df = pd.DataFrame(all_stats)
    stats_csv_path = os.path.join(models_output_dir, 'model_training_stats.csv')
    stats_df.to_csv(stats_csv_path, index=False)
    print(f"\nSaved training statistics to {stats_csv_path}")
