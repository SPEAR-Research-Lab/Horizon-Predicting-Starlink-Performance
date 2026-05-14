import time
from typing import Any, Optional, Tuple

import pandas as pd
import requests
from geopy.distance import geodesic

from constants import logger, model_pipeline_dir
from custom_types import Coordinate

data_dir = model_pipeline_dir / "data"


class DistanceCalculator:
    _client_server_distance: pd.DataFrame
    _world_cities: Optional[pd.DataFrame]
    _distance_cache_dirty: bool
    _coordinates_cache_dirty: bool
    _failed_lookups: set[Tuple[str, str]]

    def __init__(self):
        self._client_server_distance = pd.read_csv(
            data_dir / "client_server_distance.csv"
        )
        self._world_cities = None
        self._distance_cache_dirty = False
        self._failed_lookups = set()
        self._coordinates_cache_dirty = False

    def get_distance_between_cities(
        self, city_from: str, country_from: str, city_to: str, country_to: str
    ) -> float:
        cached_distance = self._client_server_distance[
            (self._client_server_distance["client_city"] == city_from)
            & (self._client_server_distance["client_country_code"] == country_from)
            & (self._client_server_distance["server_city"] == city_to)
            & (self._client_server_distance["server_country_code"] == country_to)
        ]["distance"]

        if cached_distance.notnull().any():
            return cached_distance.values[0]

        coord_from = self.get_city_coordinates(city_from, country_from)
        coord_to = self.get_city_coordinates(city_to, country_to)

        if coord_from is None or coord_to is None:
            logger.error(
                f"Could not retrieve coordinates for {city_from}, {country_from} or {city_to}, {country_to}"
            )
            return float("nan")

        distance = geodesic(coord_from, coord_to).kilometers
        self._client_server_distance.loc[len(self._client_server_distance)] = {
            "client_city": city_from,
            "client_country_code": country_from,
            "server_city": city_to,
            "server_country_code": country_to,
            "distance": distance,
        }
        self._client_server_distance.to_csv(
            data_dir / "client_server_distance.csv", index=False
        )
        return distance

    def get_city_coordinates(self, city: str, country: str) -> Optional[Coordinate]:
        if self._world_cities is None:
            self._world_cities = pd.read_csv(data_dir / "world_cities_coordinates.csv")

        coords = self._world_cities[
            (self._world_cities["city"] == city)
            & (self._world_cities["country"] == country)
        ][["lat", "lng"]].values

        if len(coords) == 0:
            if (city, country) in self._failed_lookups:
                logger.debug(f"Skipping previously failed lookup for {city}, {country}")
                return None

            lat, lng = DistanceCalculator._fetch_coordinates(city, country)
            if lat is not None and lng is not None:
                self._save_city_coordinates(city, country, lat, lng)
                return (lat, lng)
            else:
                self._failed_lookups.add((city, country))
                return None

        return tuple(coords[0])

    def _save_city_coordinates(
        self, city: str, country: str, lat: float, lng: float
    ) -> None:
        logger.info(f"Saving coordinates for {city}, {country}: ({lat}, {lng})")
        new_row = pd.DataFrame(
            [{"city": city, "country": country, "lat": lat, "lng": lng}]
        )
        self._world_cities = pd.concat([self._world_cities, new_row], ignore_index=True)
        self._world_cities.to_csv(
            data_dir / "world_cities_coordinates.csv", index=False
        )

    @staticmethod
    def _fetch_coordinates(
        city: str, country_code: str
    ) -> Tuple[Optional[float], Optional[float]]:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "CityCoordinateFetcher/1.0"}

        try:
            logger.info(f"Fetching coordinates for {city}, {country_code}")
            params: dict[str, Any] = {
                "city": city,
                "country": country_code,
                "format": "json",
                "limit": 1,
            }

            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                return lat, lng

        except Exception as e:
            logger.error(f"Error fetching coordinates for {city}, {country_code}: {e}")

        time.sleep(1)
        logger.info(f"Retrying with cleaned city name for {city}, {country_code}")
        cleaned_city = city
        if "(" in cleaned_city:
            cleaned_city = cleaned_city.split("(")[0].strip()
        if "," in cleaned_city:
            cleaned_city = cleaned_city.split(",")[0].strip()
        suffixes_to_remove = [
            " municipality",
            " city",
            " town",
            " village",
            " district",
            " region",
            " province",
            " county",
            " bay area",
            " metropolitan area",
            " metro",
        ]

        cleaned_city_lower = cleaned_city.lower()
        for suffix in suffixes_to_remove:
            cleaned_city_lower = cleaned_city_lower.replace(suffix, "")

        if cleaned_city != city and cleaned_city:
            try:
                logger.info(f"Retrying with cleaned name: {cleaned_city}")
                params = {
                    "city": cleaned_city,
                    "country": country_code,
                    "format": "json",
                    "limit": 1,
                }

                response = requests.get(url, params=params, headers=headers)
                response.raise_for_status()

                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    logger.info(
                        f"Successfully found coordinates using cleaned name: {cleaned_city}"
                    )
                    return lat, lng

            except Exception as e:
                logger.error(
                    f"Error fetching coordinates for cleaned name {cleaned_city}, {country_code}: {e}"
                )

        logger.warning(f"Could not find coordinates for {city}, {country_code}")
        return None, None
