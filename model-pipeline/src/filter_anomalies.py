import os
from typing import Any
import pandas as pd
import numpy as np
from constants import dtype_spec
from enum import Enum
from sklearn.ensemble import IsolationForest


MIN_WINDOW_HOURS = 1.0
MAX_WINDOW_HOURS = 3.0
WINDOW_STEP_HOURS = 0.5
MIN_MATCHES_REQUIRED = 8

class FilterDirection(Enum):
    UPPER = 0
    LOWER = 1
    BOTH = 2

def map_feature_to_filter_direction(feature: str) -> FilterDirection:
    if "latency" in feature or "jitter" in feature or "packet_loss" in feature:
        return FilterDirection.UPPER
    if "throughput" in feature:
        return FilterDirection.LOWER
    return FilterDirection.BOTH

def filter_incomplete_measurements(df: pd.DataFrame, target_feature_group: list[str]) -> pd.DataFrame:
    df = df.copy()
    bad_measurements = df[target_feature_group].isna().any(axis=1)
    for feature in target_feature_group:
        if 'jitter' in feature or 'packet_loss' in feature:
            continue
        bad_measurements |= (df[feature] <= 0)
    return df[~bad_measurements].reset_index(drop=True)

def get_window_idx(group_ts: np.ndarray, group_idx: np.ndarray, center_time: np.datetime64) -> np.ndarray | None:
    window_idx = None
    for window_hours in np.arange(MIN_WINDOW_HOURS, MAX_WINDOW_HOURS + WINDOW_STEP_HOURS, WINDOW_STEP_HOURS):
        time_diff = np.abs(group_ts - center_time)
        window_mask = time_diff <= np.timedelta64(int(window_hours * 30), 'm')
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
        return values <= threshold
    elif direction == FilterDirection.LOWER:
        threshold = median - k * mad
        return values >= threshold
    elif direction == FilterDirection.BOTH:
        upper_threshold = median + k * mad
        lower_threshold = median - k * mad
        return (values >= lower_threshold) & (values <= upper_threshold)


def filter_outliers_directional_mad(df: pd.DataFrame, k: float, target_feature_group: list[str], detailed_stats=False,
                                    voting_threshold: float = 0.5) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['lat', 'lon', 'ts']).reset_index(drop=True)

    violated_sets: dict[str, set[int]] = {feature: set() for feature in target_feature_group}
    vals: dict[str, Any] = {feature: df[feature].values for feature in target_feature_group}
    ts_vals = df['ts'].values

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
            center_time = group_ts[i]
            window_idx = get_window_idx(group_ts, group_idx, center_time)

            if window_idx is None:
                continue
            elif len(window_idx) < MIN_MATCHES_REQUIRED:
                flagged_count[window_idx] += 1
                if detailed_stats:
                    for feature in target_feature_group:
                        violated_sets[feature].update(window_idx)
            else:
                window_vals = {feature: vals[feature][window_idx] for feature in target_feature_group}
                masks = {
                    feature:
                        directional_mad_filter(window_vals[feature], map_feature_to_filter_direction(feature), k) for
                    feature in target_feature_group
                }

                if detailed_stats:
                    for feature in target_feature_group:
                        violated_sets[feature].update(window_idx[~masks[feature]])

                combined_mask = masks[target_feature_group[0]]
                for feature in target_feature_group[1:]:
                    combined_mask &= masks[feature]
                flagged_count[window_idx[~combined_mask]] += 1

            window_count[window_idx] += 1

    keep_mask = (flagged_count < voting_threshold * window_count) | (window_count == 0)
    filtered_df = df[keep_mask].reset_index(drop=True)

    if detailed_stats:
        print("Filtering statistics:")
        for feature in target_feature_group:
            print(f"Violated {feature}: {len(violated_sets[feature])}")
        print("\n")

    return filtered_df


def filter_outliers_isolation_forest(df: pd.DataFrame, keep_frac: float, target_feature_group: list[str],
                                     temporal_cols=['hour_with_minute', 'day_of_week']) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['lat', 'lon', 'ts']).reset_index(drop=True)

    keep_mask = np.ones(len(df), dtype=bool)

    if_train_cols = target_feature_group + temporal_cols

    for (lat, lon), group in df.groupby(['lat', 'lon'], sort=False):
        group_idx = group.index.values
        n = len(group_idx)

        if n < MIN_MATCHES_REQUIRED:
            keep_mask[group_idx] = False
            continue

        X = df.loc[group_idx, if_train_cols].values
        X_norm = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-8)

        iso_forest = IsolationForest(
            contamination=1 - keep_frac,
            random_state=42,
            n_estimators=100,
            n_jobs=-1
        )
        predictions = iso_forest.fit_predict(X_norm)
        keep_mask[group_idx[predictions == -1]] = False

    return df[keep_mask].reset_index(drop=True)


def composite_badness_vectorized(target_feature_group: list[str], window_vals: dict[str, np.ndarray],
                                 max_vals: dict[str, float]) -> np.ndarray:
    norms = {feature: np.minimum(window_vals[feature] / (max_vals[feature]), 1.0) for feature in target_feature_group}
    for feature in target_feature_group:
        if map_feature_to_filter_direction(feature) == FilterDirection.LOWER:
            norms[feature] = 1 - norms[feature]
    return np.sum(list(norms.values()), axis=0)


def filter_outliers_percentile(df: pd.DataFrame, keep_frac: float, target_feature_group: list[str],
                               voting_threshold: float = 0.5) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['lat', 'lon', 'ts']).reset_index(drop=True)
    ts_vals = df['ts'].values
    vals = {feature: df[feature].values for feature in target_feature_group}

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
                window_vals: dict[str, Any] = {feature: vals[feature][window_idx] for feature in target_feature_group}
                max_vals = {feature: window_vals[feature].max() for feature in target_feature_group}
                badness = composite_badness_vectorized(target_feature_group, window_vals, max_vals)

                threshold = np.quantile(badness, keep_frac)
                flagged_count[window_idx[badness > threshold]] += 1

            window_count[window_idx] += 1

    keep_mask = (flagged_count < voting_threshold * window_count) | (window_count == 0)

    return df[keep_mask].reset_index(drop=True)
