from enum import Enum
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import pycountry


class Aggregation(Enum):
    MEDIAN = "median"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    NONE = "none"


def iso2_to_iso3(iso2_code: str) -> Optional[str]:
    """
    Convert ISO2 country code to ISO3.
    """
    try:
        country = pycountry.countries.get(alpha_2=iso2_code)
        return country.alpha_3 if country else None
    except:
        return None


def filter_df_by_min_measurements(
    df: pd.DataFrame,
    min_measurements: int,
    allowed_countries: Optional[set] = None,
) -> pd.DataFrame:
    """
    Filter out countries that have fewer than min_measurements in the dataframe.
    """
    country_counts = df["client_country_code"].value_counts()
    valid_countries = country_counts[country_counts >= min_measurements].index

    if allowed_countries is not None:
        valid_countries = valid_countries[valid_countries.isin(allowed_countries)]

    return df[df["client_country_code"].isin(valid_countries)]


def filter_filtration_dfs_by_min_measurements(
    df_all: pd.DataFrame,
    df_filtered: pd.DataFrame,
    df_after: pd.DataFrame,
    min_measurements: int,
    allowed_countries: Optional[list[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Filter out countries that have fewer than min_measurements in df_all from all datasets.
    """
    country_counts = df_all["client_country_code"].value_counts()
    valid_countries = country_counts[country_counts >= min_measurements].index

    if allowed_countries is not None:
        valid_countries = valid_countries[valid_countries.isin(allowed_countries)]
        print(f"Countries after allowed list filter: {len(valid_countries)}")

    print(f"Countries removed: {len(country_counts) - len(valid_countries)}")

    df_all_filtered = df_all[df_all["client_country_code"].isin(valid_countries)]
    df_filtered_filtered = df_filtered[
        df_filtered["client_country_code"].isin(valid_countries)
    ]
    df_after_filtered = df_after[df_after["client_country_code"].isin(valid_countries)]

    print(
        f"\nRecords before: df_all={len(df_all)}, df_filtered={len(df_filtered)}, df_after={len(df_after)}"
    )
    print(
        f"Records after: df_all={len(df_all_filtered)}, df_filtered={len(df_filtered_filtered)}, df_after={len(df_after_filtered)}"
    )

    return df_all_filtered, df_filtered_filtered, df_after_filtered


def get_download_and_upload_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split dataframe into download and upload measurements.
    """
    df_download = df[~df["download_throughput_mbps"].isna()]
    df_upload = df[~df["upload_throughput_mbps"].isna()]
    return df_download, df_upload


def get_histogram(data: pd.DataFrame, bin_width: Optional[int] = None):
    """
    Generate histogram with density normalization.
    Handles empty data gracefully by returning empty arrays.
    """
    if len(data) == 0:
        return np.array([]), np.array([0, 1])

    if len(data) == 1 or np.max(data) == np.min(data):
        val = data.iloc[0] if hasattr(data, "iloc") else data[0]
        return np.array([1.0]), np.array([val, val + 1])

    num_bins = 100
    if bin_width is not None and bin_width > 0:
        data_range = np.max(data) - np.min(data)
        if data_range > 0:
            num_bins = max(1, int(data_range / bin_width))

    return np.histogram(data, bins=num_bins, density=True)


def get_country_name(iso_code: str) -> str:
    """
    Get the full country name from ISO2 country code.
    """
    country = pycountry.countries.get(alpha_2=iso_code.upper())
    if country:
        return country.name
    else:
        raise ValueError(f"Unknown country code: {iso_code}")


def rgb_to_hex(rgb) -> str:
    """
    Convert RGB tuple to HEX string.
    """
    r, g, b = [int(255 * x) for x in rgb]
    return f"#{r:02x}{g:02x}{b:02x}"
