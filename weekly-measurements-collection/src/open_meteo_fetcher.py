from datetime import date, timedelta
import time
from typing import Any, Union

from openmeteo_requests import Client as OpenMeteoClient
import pandas as pd
import requests_cache
from retry_requests import retry

from config import logger, weather_data_dir
from custom_types import ForecastParams, HistoricalParams
from inter_city_distance_calculator import DistanceCalculator
from utils import get_weather_file_name


class OpenMeteoFetcher:
    _historical_url = "https://archive-api.open-meteo.com/v1/archive"
    _forecast_url = "https://api.open-meteo.com/v1/forecast"
    _client: OpenMeteoClient
    _distance_calculator: DistanceCalculator

    def __init__(self, distance_calculator: DistanceCalculator) -> None:
        cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self._client = OpenMeteoClient(session=retry_session)
        self._distance_calculator = distance_calculator

    def _getParams_historical(
        self, latitude: float, longitude: float, start_date: date, end_date: date
    ) -> HistoricalParams:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "hourly": ["temperature_2m", "precipitation", "cloud_cover", "wind_speed_10m"],
            "timezone": "GMT",
        }

    def _getParams_forecast(
        self, latitude: float, longitude: float, past_days: int, forecast_days: int
    ) -> ForecastParams:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ["temperature_2m", "precipitation", "cloud_cover", "wind_speed_10m"],
            "past_days": past_days,
            "forecast_days": forecast_days,
        }

    def _fetch(self, url: str, params: Union[HistoricalParams, ForecastParams]) -> pd.DataFrame:
        logger.info(
            f"Fetching {'historical' if url == self._historical_url else 'forecast'} data with params: {params}"
        )
        responses = self._client.weather_api(url, params=params)
        response = responses[0]
        response = responses[0]

        hourly = response.Hourly()
        if hourly is None:
            raise ValueError("No hourly data returned from Open-Meteo API.")

        var0 = hourly.Variables(0)
        var1 = hourly.Variables(1)
        var2 = hourly.Variables(2)
        var3 = hourly.Variables(3)

        if var0 is None or var1 is None or var2 is None or var3 is None:
            logger.warning(f"Missing variable data from Open-Meteo API for params: {params}")
            raise ValueError("Missing variable data from Open-Meteo API.")

        hourly_temperature_2m = var0.ValuesAsNumpy()
        hourly_precipitation = var1.ValuesAsNumpy()
        hourly_cloud_cover = var2.ValuesAsNumpy()
        hourly_wind_speed_10m = var3.ValuesAsNumpy()

        hourly_data: dict[str, Any] = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )
        }

        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["precipitation"] = hourly_precipitation
        hourly_data["cloud_cover"] = hourly_cloud_cover
        hourly_data["wind_speed_10m"] = hourly_wind_speed_10m

        return pd.DataFrame(data=hourly_data)

    def fetch_and_save_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        file_name: str,
    ) -> None:
        params = self._getParams_historical(latitude, longitude, start_date, end_date)
        new_df = self._fetch(self._historical_url, params)
        file_path = weather_data_dir / file_name

        if file_path.exists():
            existing_df = pd.read_csv(file_path, parse_dates=['date'])
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date').reset_index(drop=True)
            combined_df.to_csv(file_path, index=False)
        else:
            new_df.to_csv(file_path, index=False)

    def fetch_and_save_forecast(
        self, latitude: float, longitude: float, file_name: str, past_days: int, forecast_days: int
    ) -> None:
        params = self._getParams_forecast(latitude, longitude, past_days, forecast_days)
        df = self._fetch(self._forecast_url, params)
        file_path = weather_data_dir / file_name
        if file_path.exists():
            df.to_csv(file_path, mode='a', header=False, index=False)
        else:
            df.to_csv(file_path, index=False)

    def _fetch_weather_data(
        self, city_country_set: set[tuple[str, str]], ref_date: date, historical_days: int = 15, forecast_days: int = 15
    ) -> None:
        for city, country in city_country_set:
            historical_file_name = get_weather_file_name(city, country, is_historical=True)
            forecast_file_name = get_weather_file_name(city, country, is_historical=False)

            coords = self._distance_calculator.get_city_coordinates(city, country)
            if coords is None or len(coords) < 2:
                logger.warning(f"Could not get coordinates for {city}, {country}. Skipping weather fetch.")
                continue

            latitude, longitude = coords[0], coords[1]
            self.fetch_and_save_historical(
                latitude=latitude,
                longitude=longitude,
                start_date=pd.to_datetime(ref_date, utc=True).date() - timedelta(days=historical_days),
                end_date=ref_date,
                file_name=historical_file_name,
            )
            self.fetch_and_save_forecast(
                latitude=latitude,
                longitude=longitude,
                file_name=forecast_file_name,
                past_days=historical_days,
                forecast_days=forecast_days,
            )

            time.sleep(1)  # Rate limiting between cities
