from enum import Enum
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from config import logger
from logger import LogUtils

MIN_WINDOW_HOURS = 1.0
MAX_WINDOW_HOURS = 3.0
WINDOW_STEP_HOURS = 0.5
MIN_MATCHES_REQUIRED = 8


class FilterDirection(Enum):
    UPPER = 0
    LOWER = 1
    BOTH = 2


class TargetFeature(Enum):
    DOWNLOAD_LATENCY = 'download_latency_ms'
    DOWNLOAD_THROUGHPUT = 'download_throughput_mbps'


def map_feature_to_filter_direction(feature: TargetFeature) -> FilterDirection:
    if feature == TargetFeature.DOWNLOAD_LATENCY:
        return FilterDirection.UPPER
    elif feature == TargetFeature.DOWNLOAD_THROUGHPUT:
        return FilterDirection.LOWER
    else:
        raise ValueError(f"Feature not handled: {feature}")


def filter_incomplete_measurements(df: pd.DataFrame, target_feature: TargetFeature) -> pd.DataFrame:
    bad_measurements = df[target_feature.value].isna() | (df[target_feature.value] <= 0)
    return df[~bad_measurements].reset_index(drop=True)


def get_window_idx(group_ts: np.ndarray, group_idx: np.ndarray, center_time: np.datetime64) -> np.ndarray | None:
    window_idx = None
    for window_hours in np.arange(MIN_WINDOW_HOURS, MAX_WINDOW_HOURS + WINDOW_STEP_HOURS, WINDOW_STEP_HOURS):
        time_diff = np.abs(group_ts - center_time)
        window_mask = time_diff <= np.timedelta64(int(window_hours * 30), 'm')  # half window both sides
        window_idx = group_idx[window_mask]

        if len(window_idx) >= MIN_MATCHES_REQUIRED:
            break
    return window_idx


def filter_outliers_isolation_forest(
    df: pd.DataFrame,
    feature: TargetFeature,
    keep_frac: float = 0.7,
    temporal_cols: list = ['hour_with_minute', 'day_of_week'],
) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['lat', 'lon', 'ts']).reset_index(drop=True)

    keep_mask = np.ones(len(df), dtype=bool)

    if_train_cols = [feature.value] + temporal_cols

    for (lat, lon), group in df.groupby(['lat', 'lon'], sort=False):
        group_idx = group.index.values
        n = len(group_idx)

        if n < MIN_MATCHES_REQUIRED:
            keep_mask[group_idx] = False
            continue

        X = df.loc[group_idx, if_train_cols].to_numpy(dtype=np.float64)
        X_norm = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-8)

        iso_forest = IsolationForest(contamination=1 - keep_frac, random_state=42, n_estimators=100, n_jobs=-1)
        predictions = iso_forest.fit_predict(X_norm)
        keep_mask[group_idx[predictions == -1]] = False

    return df[keep_mask].reset_index(drop=True)


def composite_badness_vectorized(feature: TargetFeature, window_vals: np.ndarray, max_val: float) -> np.ndarray:
    norm = np.minimum(window_vals / (max_val + 1e-8), 1.0)
    if map_feature_to_filter_direction(feature) == FilterDirection.LOWER:
        norm = 1 - norm
    return norm


def filter_outliers_percentile(
    df: pd.DataFrame, feature: TargetFeature, keep_frac: float = 0.7, voting_threshold: float = 0.5
) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['lat', 'lon', 'ts']).reset_index(drop=True)
    ts_vals = df['ts'].values
    vals = df[feature.value].values

    flagged_count = np.zeros(len(df), dtype=int)
    window_count = np.zeros(len(df), dtype=int)

    for (lat, lon), group in df.groupby(['lat', 'lon'], sort=False):
        group_idx = group.index.values
        group_ts = np.asarray(ts_vals[group_idx])
        n = len(group_idx)

        if n < MIN_MATCHES_REQUIRED:
            flagged_count[group_idx] += 1
            window_count[group_idx] += 1
            continue

        for i in range(n):
            window_idx = get_window_idx(group_ts, group_idx, group_ts[i])
            if window_idx is None:
                continue
            elif len(window_idx) < MIN_MATCHES_REQUIRED:
                flagged_count[window_idx] += 1
            else:
                window_vals = np.asarray(vals[window_idx], dtype=float)
                max_val = window_vals.max()
                badness = composite_badness_vectorized(feature, window_vals, max_val)

                threshold = np.quantile(badness, keep_frac)
                flagged_count[window_idx[badness > threshold]] += 1

            window_count[window_idx] += 1

    keep_mask = (flagged_count < voting_threshold * window_count) | (window_count == 0)

    return df[keep_mask].reset_index(drop=True)


@LogUtils.log_function
def filter_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    logger.info(f"Filtering anomalies from {len(df)} measurements...")
    latency_df = filter_incomplete_measurements(df.copy(), TargetFeature.DOWNLOAD_LATENCY)
    latency_df['ts'] = pd.to_datetime(latency_df['test_time'], format='mixed', utc=True)
    latency_df = filter_outliers_percentile(latency_df, TargetFeature.DOWNLOAD_LATENCY)
    latency_df = latency_df.drop(columns=['ts'])
    logger.info(f"Latency filtering complete: {len(latency_df)} rows ({len(latency_df) / len(df) * 100:.2f}%)")

    throughput_df = filter_incomplete_measurements(df.copy(), TargetFeature.DOWNLOAD_THROUGHPUT)
    throughput_df['ts'] = pd.to_datetime(throughput_df['test_time'], format='mixed', utc=True)
    throughput_df = filter_outliers_percentile(throughput_df, TargetFeature.DOWNLOAD_THROUGHPUT)
    throughput_df = throughput_df.drop(columns=['ts'])
    logger.info(f"Throughput filtering complete: {len(throughput_df)} rows ({len(throughput_df) / len(df) * 100:.2f}%)")

    return latency_df, throughput_df
