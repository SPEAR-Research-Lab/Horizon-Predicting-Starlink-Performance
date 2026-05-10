from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import os
from typing import Optional

import pandas as pd

from config import weather_data_dir
from custom_types import WeatherData
from utils import get_previous_and_next_hours_utc


@dataclass
class WeatherDataFrames:
    historical: pd.DataFrame
    forecast: pd.DataFrame


class WeatherDataHandler:
    _city_to_df_map: dict[str, WeatherDataFrames] = defaultdict(
        lambda: WeatherDataFrames(historical=pd.DataFrame(), forecast=pd.DataFrame())
    )

    @staticmethod
    def _get_cache_key_from_file(file_name: str) -> str:
        return file_name.replace("_historical.csv", "").replace("_forecast.csv", "")

    @staticmethod
    def _get_cache_key(first: str, second: str) -> str:
        return f"{first}_{second}"

    @staticmethod
    def _get_point(df: pd.DataFrame, key: str) -> Optional[pd.Series] | pd.DataFrame:
        try:
            return df.loc[key]
        except KeyError:
            return None

    def initialize_weather_data(self, force: bool = False) -> None:
        if self._city_to_df_map and not force:
            return
        for file in os.listdir(weather_data_dir):
            df = pd.read_csv(weather_data_dir / file, parse_dates=["date"])
            df = df.drop_duplicates(subset=["date"], keep="first")
            df = df.set_index("date")
            if 'historical' in file:
                self._city_to_df_map[WeatherDataHandler._get_cache_key_from_file(file)].historical = df
            elif 'forecast' in file:
                self._city_to_df_map[WeatherDataHandler._get_cache_key_from_file(file)].forecast = df

    def get_weather_data(self, first: str, second: str, date_str: str) -> WeatherData:
        self.initialize_weather_data()
        dt = datetime.fromisoformat(date_str)
        prev_hour_str, next_hour_str = get_previous_and_next_hours_utc(dt)

        container = self._city_to_df_map.get(WeatherDataHandler._get_cache_key(first, second))
        if container is None:
            raise ValueError(f"No weather data found for {first}, {second}.")

        prev_hour_datapoint = None
        next_hour_datapoint = None

        prev_hour_datapoint = WeatherDataHandler._get_point(container.historical, prev_hour_str)
        next_hour_datapoint = WeatherDataHandler._get_point(container.historical, next_hour_str)

        if prev_hour_datapoint is None or next_hour_datapoint is None:
            if prev_hour_datapoint is None:
                prev_hour_datapoint = WeatherDataHandler._get_point(container.forecast, prev_hour_str)
            if next_hour_datapoint is None:
                next_hour_datapoint = WeatherDataHandler._get_point(container.forecast, next_hour_str)

        if prev_hour_datapoint is None or next_hour_datapoint is None:
            raise ValueError(
                f"Could not find weather data for {first}, {second} at {prev_hour_str} or {next_hour_str}."
            )

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
