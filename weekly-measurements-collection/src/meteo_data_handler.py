from dataclasses import dataclass, field
from datetime import datetime
import os
from typing import Optional

import pandas as pd

from config import logger, weather_data_dir
from custom_types import WeatherData
from utils import get_previous_and_next_hours_utc


@dataclass
class WeatherDataFrames:
    historical: pd.DataFrame = field(default_factory=pd.DataFrame)
    forecast: pd.DataFrame = field(default_factory=pd.DataFrame)


class WeatherDataHandler:
    def __init__(self) -> None:
        self._city_to_df_map: dict[str, WeatherDataFrames] = {}
        self._initialized: bool = False

    @staticmethod
    def _get_cache_key_from_file(file_name: str) -> str:
        return file_name.replace("_historical.csv", "").replace("_forecast.csv", "")

    @staticmethod
    def _get_cache_key(first: str, second: str) -> str:
        return f"{first}_{second}".lower()

    @staticmethod
    def _get_point(df: pd.DataFrame, key: str) -> Optional[pd.Series]:
        try:
            result = df.loc[key]
        except KeyError:
            return None

        if isinstance(result, pd.DataFrame):
            logger.warning(f"Duplicate timestamp {key} found in weather data; using first occurrence.")
            result = result.iloc[0]

        return result

    def initialize_weather_data(self, force: bool = False) -> None:
        if self._initialized and not force:
            return
        city_map: dict[str, WeatherDataFrames] = {}
        for file in os.listdir(weather_data_dir):
            df = pd.read_csv(weather_data_dir / file, parse_dates=["date"])
            df = df.drop_duplicates(subset=["date"], keep="first")
            df = df.set_index("date")
            cache_key = WeatherDataHandler._get_cache_key_from_file(file).lower()

            if cache_key not in city_map:
                city_map[cache_key] = WeatherDataFrames()

            if "historical" in file:
                city_map[cache_key].historical = df
            elif "forecast" in file:
                city_map[cache_key].forecast = df

        self._city_to_df_map = city_map
        self._initialized = True
        logger.info(
            "Initialized weather data cache with keys: %s",
            list(self._city_to_df_map.keys()),
        )

    def get_weather_data(self, first: str, second: str, date_str: str) -> WeatherData:
        self.initialize_weather_data()
        dt = datetime.fromisoformat(date_str)
        prev_hour_str, next_hour_str = get_previous_and_next_hours_utc(dt)

        cache_key = WeatherDataHandler._get_cache_key(first, second)
        container = self._city_to_df_map.get(cache_key)
        if container is None:
            available = list(self._city_to_df_map.keys())
            raise ValueError(f"No weather data found for '{cache_key}'. Available keys: {available}")

        prev_hour_datapoint = WeatherDataHandler._get_point(container.historical, prev_hour_str)
        next_hour_datapoint = WeatherDataHandler._get_point(container.historical, next_hour_str)

        if prev_hour_datapoint is None:
            prev_hour_datapoint = WeatherDataHandler._get_point(container.forecast, prev_hour_str)
        if next_hour_datapoint is None:
            next_hour_datapoint = WeatherDataHandler._get_point(container.forecast, next_hour_str)

        if prev_hour_datapoint is None or next_hour_datapoint is None:
            raise ValueError(f"Could not find weather data for '{cache_key}' at {prev_hour_str} or {next_hour_str}.")

        beta = (dt - datetime.fromisoformat(prev_hour_str)).total_seconds() / 3600.0
        alpha = 1.0 - beta

        return {
            "temperature_2m": float(
                alpha * prev_hour_datapoint["temperature_2m"].item()
                + beta * next_hour_datapoint["temperature_2m"].item()
            ),
            "precipitation": float(
                alpha * prev_hour_datapoint["precipitation"].item() + beta * next_hour_datapoint["precipitation"].item()
            ),
            "cloud_cover": float(
                alpha * prev_hour_datapoint["cloud_cover"].item() + beta * next_hour_datapoint["cloud_cover"].item()
            ),
            "wind_speed_10m": float(
                alpha * prev_hour_datapoint["wind_speed_10m"].item()
                + beta * next_hour_datapoint["wind_speed_10m"].item()
            ),
        }
