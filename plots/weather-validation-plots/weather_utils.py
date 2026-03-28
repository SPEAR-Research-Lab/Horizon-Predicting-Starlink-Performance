import os
import re

import numpy as np
import pandas as pd
import requests
from constants import weather_data_dir


def mae(a, b) -> float:
    """Mean Absolute Error"""
    mask = ~(np.isnan(a) | np.isnan(b))
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(np.abs(a[mask] - b[mask])))


def rmse(a, b) -> float:
    """Root Mean Squared Error"""
    mask = ~(np.isnan(a) | np.isnan(b))
    if mask.sum() == 0:
        return np.nan
    return float(np.sqrt(np.mean((a[mask] - b[mask]) ** 2)))


def get_weather_file_name(lat: float, lon: float) -> str:
    """Generate a standardized weather file name based on latitude and longitude"""
    return (
        f"weather_lat{str(lat).replace('.', '_')}_lon{str(lon).replace('.', '_')}.csv"
    )


def get_and_maybe_fetch_openmeteo_data(lat, lon, start_date, end_date):
    weather_file = get_weather_file_name(lat, lon)
    if os.path.exists(weather_data_dir / weather_file):
        print(f"Loading cached Open-Meteo data from {weather_file}")
        om_df = pd.read_csv(f"{weather_data_dir}/{weather_file}")
        om_df["datetime"] = pd.to_datetime(om_df["datetime"])
        if (
            start_date <= om_df["datetime"].min().date()
            and end_date >= om_df["datetime"].max().date()
        ):
            return om_df

    return fetch_and_save_historical(
        lat, lon, start_date, end_date, weather_file, weather_data_dir
    )


def fetch_and_save_historical(
    lat, lon, start_date, end_date, weather_file, weather_data_dir
):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "timezone": "UTC",
        "hourly": ["temperature_2m", "precipitation", "wind_speed_10m", "cloud_cover"],
        "wind_speed_unit": "ms",
    }

    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data["hourly"])
    df["datetime"] = pd.to_datetime(df["time"], utc=True)
    df.drop(columns=["time"], inplace=True)

    file_path = weather_data_dir / weather_file
    df.to_csv(file_path, index=False)

    return df


def format_feature_name(f: str) -> str:
    name = re.sub(r"_(?:\d+m|2m|10m)$", "", f)
    name = name.replace("_", " ").strip()
    return name.title()
