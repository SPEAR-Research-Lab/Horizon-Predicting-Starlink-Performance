import os
from datetime import datetime
from typing import Optional

import pandas as pd

from constants import logger, starlink_data_dir, weather_data_dir
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

    def get_weather_data_for_city_and_time(
        self, city: str, country: str, date_str: str
    ) -> WeatherData:
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
            logger.error(
                f"No data available for city {city}, country {country} at time {date_str}."
            )
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
                alpha * prev_hour_datapoint["precipitation"].item()
                + beta * next_hour_datapoint["precipitation"].item()
            ),
            "cloud_cover": float(
                alpha * prev_hour_datapoint["cloud_cover"].item()
                + beta * next_hour_datapoint["cloud_cover"].item()
            ),
            "wind_speed_10m": float(
                alpha * prev_hour_datapoint["wind_speed_10m"].item()
                + beta * next_hour_datapoint["wind_speed_10m"].item()
            ),
        }

    def populate_csv_with_weather_data(self, csv_name: str) -> None:
        df = pd.read_csv(starlink_data_dir / csv_name)
        weather_features = WeatherData.__annotations__.keys()
        for feature in weather_features:
            df[feature] = None

        for idx, row in df.iterrows():
            weather_data: Optional[WeatherData] = None
            if (
                pd.notna(row.get("client_city"))
                and pd.notna(row.get("client_country_code"))
                and pd.notna(row.get("test_time"))
                and str(row.get("client_city")).strip() != ""
                and str(row.get("client_country_code")).strip() != ""
                and str(row.get("test_time")).strip() != ""
            ):
                weather_data = self.get_weather_data_for_city_and_time(
                    str(row["client_city"]),
                    str(row["client_country_code"]),
                    str(row["test_time"]),
                )
            if not weather_data:
                continue
            for feature, value in weather_data.items():
                df.at[idx, feature] = value

        df.to_csv(starlink_data_dir / csv_name, index=False)
