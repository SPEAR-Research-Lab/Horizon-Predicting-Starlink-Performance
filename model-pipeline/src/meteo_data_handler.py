from datetime import datetime
import os

import pandas as pd

from config import logger, weather_data_dir
from custom_types import WeatherData
from utils import get_previous_and_next_hours_utc, get_weather_file_name


class WeatherDataHandler:
    _file_to_df_map: dict[str, pd.DataFrame] = {}

    def initialize_weather_data(self, force: bool = False) -> None:
        if self._file_to_df_map and not force:
            return
        for file in os.listdir(weather_data_dir):
            df = pd.read_csv(weather_data_dir / file, parse_dates=["date"])
            df = df.drop_duplicates(subset=["date"], keep="first")
            df = df.set_index("date")
            self._file_to_df_map[file] = df

    def get_weather_data_for_city_and_time(self, city: str, country: str, date_str: str) -> WeatherData:
        self.initialize_weather_data()
        dt = datetime.fromisoformat(date_str)
        prev_hour_str, next_hour_str = get_previous_and_next_hours_utc(dt)

        file_name = get_weather_file_name(city, country, is_historical=True)
        df = self._file_to_df_map.get(file_name)
        if df is None:
            raise ValueError(f"No weather data found for {city}, {country}.")

        try:
            prev_hour_datapoint = df.loc[prev_hour_str]
            next_hour_datapoint = df.loc[next_hour_str]
        except KeyError:
            logger.error(f"No data available for city {city}, country {country} at time {date_str}.")
            return WeatherData(
                temperature_2m=float("nan"),
                precipitation=float("nan"),
                cloud_cover=float("nan"),
                wind_speed_10m=float("nan"),
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
