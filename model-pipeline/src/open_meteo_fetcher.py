from datetime import date, timedelta
import time
from typing import Any, MutableMapping, Union, cast

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

    def __init__(self) -> None:
        cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self._client = OpenMeteoClient(session=retry_session)
        self._distance_calculator = DistanceCalculator()

    def _getParams_historical(
        self, latitude: float, longitude: float, start_date: date, end_date: date
    ) -> HistoricalParams:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "hourly": [
                "temperature_2m",
                "precipitation",
                "cloud_cover",
                "wind_speed_10m",
            ],
            "timezone": "GMT",
        }

    def _getParams_forecast(
        self, latitude: float, longitude: float, past_days: int, forecast_days: int
    ) -> ForecastParams:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": [
                "temperature_2m",
                "precipitation",
                "cloud_cover",
                "wind_speed_10m",
            ],
            "past_days": past_days,
            "forecast_days": forecast_days,
        }

    def _fetch(self, url: str, params: Union[HistoricalParams, ForecastParams]) -> pd.DataFrame:
        logger.info(
            f"Fetching {'historical' if url == self._historical_url else 'forecast'} data with params: {params}"
        )
        responses = self._client.weather_api(url, params=cast(MutableMapping[str, Any], params))
        response = responses[0]

        hourly = response.Hourly()
        if hourly is None:
            raise ValueError("No hourly data returned from Open-Meteo API.")

        var0 = hourly.Variables(0)
        var1 = hourly.Variables(1)
        var2 = hourly.Variables(2)
        var3 = hourly.Variables(3)

        if var0 is None or var1 is None or var2 is None or var3 is None:
            logger.error(f"Missing variable data from Open-Meteo API for params: {params}")
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
            existing_df = pd.read_csv(file_path, parse_dates=["date"])
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["date"], keep="last")
            combined_df = combined_df.sort_values("date").reset_index(drop=True)
            combined_df.to_csv(file_path, index=False)
        else:
            new_df.to_csv(file_path, index=False)

    def fetch_and_save_forecast(
        self,
        latitude: float,
        longitude: float,
        file_name: str,
        past_days: int = 3,
        forecast_days: int = 3,
    ) -> None:
        params = self._getParams_forecast(latitude, longitude, past_days, forecast_days)
        df = self._fetch(self._forecast_url, params)
        file_path = weather_data_dir / file_name
        if file_path.exists():
            df.to_csv(file_path, mode="a", header=False, index=False)
        else:
            df.to_csv(file_path, index=False)

    def _fetch_missing_weather_data(self, min_max_date_map: dict[tuple[str, str], dict]) -> bool:
        fetched_any_file = False
        for (city, country), date_range in min_max_date_map.items():
            file_name = get_weather_file_name(city, country, is_historical=True)
            file_path = weather_data_dir / file_name

            coords = self._distance_calculator.get_city_coordinates(city, country)
            if coords is None or len(coords) < 2:
                logger.warning(f"Could not get coordinates for {city}, {country}. Skipping weather fetch.")
                continue

            latitude, longitude = coords[0], coords[1]
            required_start_date = pd.to_datetime(date_range["earliest"], utc=True).date() - timedelta(days=1)
            required_end_date = pd.to_datetime(date_range["latest"], utc=True).date() + timedelta(days=1)

            if not file_path.exists():
                logger.info(
                    f"Weather file not found for {city}, {country}. Fetching data from {required_start_date} to {required_end_date}"
                )
                fetched_any_file = True
                self.fetch_and_save_historical(
                    latitude=latitude,
                    longitude=longitude,
                    start_date=required_start_date,
                    end_date=required_end_date,
                    file_name=file_name,
                )
            else:
                try:
                    existing_df = pd.read_csv(file_path, parse_dates=["date"])
                    date_series = pd.to_datetime(existing_df["date"], utc=True)
                    existing_start_date = date_series.min().date()
                    existing_end_date = date_series.max().date()
                    distinct_dates_in_file = date_series.dt.date.nunique()
                    expected_days_in_range = (existing_end_date - existing_start_date).days + 1

                    has_gaps = distinct_dates_in_file != expected_days_in_range
                    needs_earlier_data = required_start_date < existing_start_date
                    needs_later_data = required_end_date > existing_end_date

                    fetch_start_date = min(required_start_date, existing_start_date)
                    fetch_end_date = max(required_end_date, existing_end_date)

                    if has_gaps:
                        logger.info(
                            f"Weather data for {city}, {country} has gaps ({distinct_dates_in_file}/{expected_days_in_range} days). Refetching entire range."
                        )
                    elif needs_earlier_data and needs_later_data:
                        logger.info(
                            f"Extending weather data for {city}, {country} in both directions: {fetch_start_date} to {fetch_end_date}"
                        )
                    elif needs_earlier_data:
                        logger.info(
                            f"Fetching earlier weather data for {city}, {country}: {fetch_start_date} to {existing_start_date - timedelta(days=1)}"
                        )
                        fetch_end_date = existing_start_date - timedelta(days=1)
                    elif needs_later_data:
                        logger.info(
                            f"Fetching later weather data for {city}, {country}: {existing_end_date + timedelta(days=1)} to {fetch_end_date}"
                        )
                        fetch_start_date = existing_end_date + timedelta(days=1)
                    else:
                        logger.info(f"Weather data for {city}, {country} already covers required range.")
                        continue

                    fetched_any_file = True
                    self.fetch_and_save_historical(
                        latitude=latitude,
                        longitude=longitude,
                        start_date=fetch_start_date,
                        end_date=fetch_end_date,
                        file_name=file_name,
                    )
                except Exception as e:
                    logger.exception(f"Error checking existing weather file for {city}, {country}: {e}")
                    logger.info(f"Refetching complete range for {city}, {country}")
                    fetched_any_file = True
                    self.fetch_and_save_historical(
                        latitude=latitude,
                        longitude=longitude,
                        start_date=required_start_date,
                        end_date=required_end_date,
                        file_name=file_name,
                    )
            time.sleep(1)
        return fetched_any_file

    def fetch_weather_data_for_dataframe(self, df: pd.DataFrame) -> bool:
        logger.info("Extracting timestamp ranges for cities...")
        df_copy = df.copy()
        df_copy["test_time"] = pd.to_datetime(df_copy["test_time"], utc=True, format="mixed")

        grouped = df_copy.groupby(["client_city", "client_country_code"])["test_time"].agg(["min", "max"])

        min_max_date_map = {}
        for (city, country), row in grouped.iterrows():
            key = (city, country)
            min_max_date_map[key] = {"earliest": row["min"], "latest": row["max"]}
        logger.info(f"Found {len(min_max_date_map)} unique city-country combinations")
        return self._fetch_missing_weather_data(min_max_date_map)
