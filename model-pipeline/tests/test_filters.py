"""
Unit tests for anomaly filters
"""

import numpy as np
import pandas as pd
import pytest

from src.anomaly.filters import (
    filter_incomplete_measurements,
    filter_outliers_directional_mad,
    filter_outliers_isolation_forest,
    filter_outliers_percentile,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=100, freq="h")
    return pd.DataFrame(
        {
            "lat": np.random.rand(100) * 90,
            "lon": np.random.rand(100) * 180,
            "ts": dates,
            "download_latency_ms": np.random.gamma(2, 50, 100),
            "download_throughput_mbps": np.random.gamma(2, 50, 100),
            "hour_with_minute": np.random.rand(100) * 24,
            "day_of_week": np.random.randint(0, 7, 100),
        }
    )


def test_filter_incomplete_measurements(sample_data: pd.DataFrame) -> None:
    df = sample_data.copy()
    df.loc[0, "download_latency_ms"] = -1
    df.loc[1, "download_latency_ms"] = np.nan

    result = filter_incomplete_measurements(df, ["download_latency_ms"])

    assert len(result) < len(df)
    assert (result["download_latency_ms"] > 0).all()
    assert result["download_latency_ms"].notna().all()


def test_percentile_filtering(sample_data: pd.DataFrame) -> None:
    result = filter_outliers_percentile(sample_data, 0.75, ["download_latency_ms"])

    assert len(result) <= len(sample_data)
    assert "download_latency_ms" in result.columns


def test_directional_mad_filtering(sample_data: pd.DataFrame) -> None:
    result = filter_outliers_directional_mad(sample_data, 2.5, ["download_latency_ms"])

    assert len(result) <= len(sample_data)
    assert "download_latency_ms" in result.columns


def test_isolation_forest_filtering(sample_data: pd.DataFrame) -> None:
    result = filter_outliers_isolation_forest(sample_data, 0.75, ["download_latency_ms"])

    assert len(result) <= len(sample_data)
    assert "download_latency_ms" in result.columns
