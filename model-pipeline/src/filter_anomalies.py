import argparse
from dataclasses import dataclass
from enum import Enum
from functools import partial
import os
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from config import filetered_csv_dir, logger
from custom_types import TargetFeatures
from logger import LogUtils

MIN_WINDOW_HOURS = 1.0
MAX_WINDOW_HOURS = 3.0
WINDOW_STEP_HOURS = 0.5
MIN_MATCHES_REQUIRED = 8
VOTING_THRESHOLD = 0.5
TEMPORAL_COLS = ['hour_with_minute', 'day_of_week']
CHOICES_TO_FILTRATION_NAME = {
    "p": "Percentile",
    "if": "Isolation Forest",
    "mad": "Directional MAD",
}


@dataclass(frozen=True)
class FiltrationParams:
    csv_dir: str
    latency_filtration: Callable[[pd.DataFrame], pd.DataFrame]
    throughput_filtration: Callable[[pd.DataFrame], pd.DataFrame]


class FilterDirection(Enum):
    UPPER = 0
    LOWER = 1
    BOTH = 2


def map_feature_to_filter_direction(feature: str) -> FilterDirection:
    if feature == TargetFeatures.download_latency:
        return FilterDirection.UPPER
    elif feature == TargetFeatures.download_throughput:
        return FilterDirection.LOWER
    else:
        raise ValueError(f"Feature not handled: {feature}")


def filter_incomplete_measurements(df: pd.DataFrame, target_feature: str) -> pd.DataFrame:
    bad_measurements = df[target_feature].isna() | (df[target_feature] <= 0)
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


def directional_mad_filter(values: np.ndarray, direction: FilterDirection, k: float) -> np.ndarray:
    median = np.median(values)
    mad = np.median(np.abs(values - median))

    if mad == 0:
        return np.ones(len(values), dtype=bool)

    if direction == FilterDirection.UPPER:
        threshold = median + k * mad
        return np.asarray(values <= threshold)
    elif direction == FilterDirection.LOWER:
        threshold = median - k * mad
        return np.asarray(values >= threshold)
    elif direction == FilterDirection.BOTH:
        upper_threshold = median + k * mad
        lower_threshold = median - k * mad
        return np.asarray((values >= lower_threshold) & (values <= upper_threshold))


def filter_outliers_directional_mad(
    df: pd.DataFrame,
    k: float,
    feature: str,
) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(["lat", "lon", "ts"]).reset_index(drop=True)

    vals = df[feature].values
    ts_vals = df["ts"].values

    flagged_count = np.zeros(len(df), dtype=int)
    window_count = np.zeros(len(df), dtype=int)

    for (lat, lon), group in df.groupby(["lat", "lon"], sort=False):
        group_idx = group.index.values
        group_ts = np.asarray(ts_vals[group_idx])
        n = len(group_idx)

        if n < MIN_MATCHES_REQUIRED:
            flagged_count[group_idx] += 1
            window_count[group_idx] += 1
            continue

        for i in range(n):
            center_time = group_ts[i]
            window_idx = get_window_idx(group_ts, group_idx, center_time)

            if window_idx is None:
                continue
            elif len(window_idx) < MIN_MATCHES_REQUIRED:
                flagged_count[window_idx] += 1
            else:
                window_vals = np.asarray(vals[window_idx], dtype=float)
                mask = directional_mad_filter(
                    window_vals,
                    map_feature_to_filter_direction(feature),
                    k,
                )
                flagged_count[window_idx[~mask]] += 1

            window_count[window_idx] += 1

    keep_mask = (flagged_count < VOTING_THRESHOLD * window_count) | (window_count == 0)
    filtered_df = df[keep_mask].reset_index(drop=True)

    return filtered_df


def filter_outliers_isolation_forest(
    df: pd.DataFrame,
    k: float,
    feature: str,
) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['lat', 'lon', 'ts']).reset_index(drop=True)

    keep_mask = np.ones(len(df), dtype=bool)

    if_train_cols = [feature] + TEMPORAL_COLS

    for (lat, lon), group in df.groupby(['lat', 'lon'], sort=False):
        group_idx = group.index.values
        n = len(group_idx)

        if n < MIN_MATCHES_REQUIRED:
            keep_mask[group_idx] = False
            continue

        X = df.loc[group_idx, if_train_cols].to_numpy(dtype=np.float64)
        X_norm = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-8)

        iso_forest = IsolationForest(contamination=1 - k, random_state=42, n_estimators=100, n_jobs=-1)
        predictions = iso_forest.fit_predict(X_norm)
        keep_mask[group_idx[predictions == -1]] = False

    return df[keep_mask].reset_index(drop=True)


def composite_badness_vectorized(feature: str, window_vals: np.ndarray, max_val: float) -> np.ndarray:
    norm = np.minimum(window_vals / (max_val + 1e-8), 1.0)
    if map_feature_to_filter_direction(feature) == FilterDirection.LOWER:
        norm = 1 - norm
    return norm


def filter_outliers_percentile(df: pd.DataFrame, k: float, feature: str) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['lat', 'lon', 'ts']).reset_index(drop=True)
    ts_vals = df['ts'].values
    vals = df[feature].values

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

                threshold = np.quantile(badness, k)
                flagged_count[window_idx[badness > threshold]] += 1

            window_count[window_idx] += 1

    keep_mask = (flagged_count < VOTING_THRESHOLD * window_count) | (window_count == 0)

    return df[keep_mask].reset_index(drop=True)


def parse_args() -> FiltrationParams:
    parser = argparse.ArgumentParser(description="Filters CSVs using the selected filtration(s).")
    parser.add_argument(
        "--src",
        "-s",
        type=str,
        help="Source directory or file path containing CSV data",
    )
    parser.add_argument(
        "--percentile-k", type=float, default=0.75, help="Param value `k` to use for percentile filtration"
    )
    parser.add_argument(
        "--if-k", type=float, default=0.75, help="Param value `k` to use for isolation forest filtration"
    )
    parser.add_argument("--mad-k", type=float, default=3, help="Param value `k` to use for directional MAD filtration")
    parser.add_argument(
        "--latency",
        type=str,
        choices=list(CHOICES_TO_FILTRATION_NAME.keys()),
        default="p",
        help="Filtration for download latency: " "p=percentile, if=isolation forest, mad=directional MAD",
    )
    parser.add_argument(
        "--throughput",
        type=str,
        choices=list(CHOICES_TO_FILTRATION_NAME.keys()),
        default="if",
        help="Filtration for download throughput: " "p=percentile, if=isolation forest, mad=directional MAD",
    )
    args = parser.parse_args()

    if args.percentile_k <= 0 or args.percentile_k >= 1:
        raise ValueError("Percentile k must be between 0 and 1.")
    if args.if_k <= 0 or args.if_k >= 1:
        raise ValueError("Isolation Forest k must be between 0 and 1.")
    if args.mad_k <= 0:
        raise ValueError("Percentile k must be positive.")

    latency_k = args.percentile_k
    if args.latency == "if":
        latency_k = args.if_k
    elif args.latency == "mad":
        latency_k = args.mad_k

    throughput_k = args.percentile_k
    if args.throughput == "if":
        throughput_k = args.if_k
    elif args.throughput == "mad":
        throughput_k = args.mad_k

    logger.info(f"Proceeding with  {CHOICES_TO_FILTRATION_NAME[args.latency]} for latency, with k={latency_k}")
    logger.info(f"Proceeding with {CHOICES_TO_FILTRATION_NAME[args.throughput]} for throughput, with k={throughput_k}")

    return FiltrationParams(
        csv_dir=args.src,
        latency_filtration=partial(filter_outliers_percentile, k=latency_k, feature=TargetFeatures.download_latency),
        throughput_filtration=partial(
            filter_outliers_isolation_forest, k=throughput_k, feature=TargetFeatures.download_throughput
        ),
    )


@LogUtils.log_function
def main() -> None:
    params = parse_args()
    for file in os.listdir(params.csv_dir):
        if file.endswith(".csv"):
            logger.info(f"Processing {file}")
            df = pd.read_csv(os.path.join(params.csv_dir, file))
            df['ts'] = pd.to_datetime(df['test_time'], format='mixed', utc=True)

            latency_df = params.latency_filtration(df)
            latency_df = latency_df.drop(columns=['ts'])
            latency_df.to_csv(filetered_csv_dir / f"download_latency_filtered_{file}", index=False)
            logger.info(f"Latency filtering complete: {len(latency_df)} rows ({len(latency_df) / len(df) * 100:.2f}%)")

            throughput_df = params.throughput_filtration(df)
            throughput_df = throughput_df.drop(columns=['ts'])
            throughput_df.to_csv(filetered_csv_dir / f"download_throughput_filtered_{file}", index=False)
            logger.info(
                f"Throughput filtering complete: {len(throughput_df)} rows ({len(throughput_df) / len(df) * 100:.2f}%)"
            )


if __name__ == "__main__":
    main()
