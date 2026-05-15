import time
from typing import Optional, Tuple

from geopy.distance import geodesic
import pandas as pd
import requests

from config import CsvFiles, data_dir, logger
from custom_types import Coordinate


class DistanceCalculator:
    _client_server_distance: pd.DataFrame
    _world_cities: Optional[pd.DataFrame]
    _distance_cache_dirty: bool
    _coordinates_cache_dirty: bool
    _failed_lookups: set[Tuple[str, str]]

    def __init__(self) -> None:
        self._client_server_distance = pd.read_csv(data_dir / CsvFiles.client_server_distance)
        self._world_cities = None
        self._server_locations = None
        self._distance_cache_dirty = False
        self._failed_lookups = set()
        self._coordinates_cache_dirty = False

    def get_distance_between_cities(self, city_from: str, country_from: str, city_to: str, country_to: str) -> float:
        cached_distance = self._client_server_distance[
            (self._client_server_distance["client_city"] == city_from)
            & (self._client_server_distance["client_country_code"] == country_from)
            & (self._client_server_distance["server_city"] == city_to)
            & (self._client_server_distance["server_country_code"] == country_to)
        ]["distance"]

        if cached_distance.notnull().any():
            return float(cached_distance.values[0])

        coord_from = self.get_city_coordinates(city_from, country_from)
        coord_to = self.get_city_coordinates(city_to, country_to)

        if coord_from is None or coord_to is None:
            logger.error(f"Could not retrieve coordinates for {city_from}, {country_from} or {city_to}, {country_to}")
            return float("nan")

        distance = geodesic(coord_from, coord_to).kilometers
        self._client_server_distance.loc[len(self._client_server_distance)] = {
            "client_city": city_from,
            "client_country_code": country_from,
            "server_city": city_to,
            "server_country_code": country_to,
            "distance": distance,
        }
        self._client_server_distance.to_csv(data_dir / CsvFiles.client_server_distance, index=False)
        return float(distance)

    def update_unresolved_cities(self) -> None:
        if len(self._failed_lookups) == 0:
            return
        unresolved_cities_path = data_dir / CsvFiles.unresolved_cities
        if unresolved_cities_path.exists():
            df = pd.read_csv(unresolved_cities_path)
        else:
            df = pd.DataFrame(columns=["city", "country"])
        unresolved_cities: set[Tuple[str, str]] = set(zip(df["city"], df["country"]))
        unresolved_cities.update(self._failed_lookups)
        unresolved_cities_df = pd.DataFrame(unresolved_cities, columns=["city", "country"])
        unresolved_cities_df.to_csv(unresolved_cities_path, index=False)

    def get_closest_server_for_location(self, lat: float, lon: float) -> float:
        if self._server_locations is None:
            self._server_locations = pd.read_csv(data_dir / CsvFiles.server_locations)

        min_distance = float("inf")
        for _, row in self._server_locations.iterrows():  # type: ignore
            server_coords = self.get_city_coordinates(row["server_city"], row["server_country_code"])
            if server_coords is None:
                continue
            distance = geodesic((lat, lon), server_coords).kilometers
            if distance < min_distance:
                min_distance = distance
        if min_distance == float("inf"):
            raise ValueError(f"No valid server locations found to calculate distance for coordinates ({lat}, {lon})")
        return min_distance

    def get_city_coordinates(self, city: str, country: str) -> Optional[Coordinate]:
        if self._world_cities is None:
            self._world_cities = pd.read_csv(data_dir / CsvFiles.world_cities_coordinates)

        # Try exact match first
        coords = self._world_cities[(self._world_cities["city"] == city) & (self._world_cities["country"] == country)][
            ["lat", "lng"]
        ].values

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

    def _save_city_coordinates(self, city: str, country: str, lat: float, lng: float) -> None:
        logger.info(f"Saving coordinates for {city}, {country}: ({lat}, {lng})")
        new_row = pd.DataFrame([{"city": city, "country": country, "lat": lat, "lng": lng}])
        self._world_cities = pd.concat([self._world_cities, new_row], ignore_index=True)
        self._world_cities.to_csv(data_dir / CsvFiles.world_cities_coordinates, index=False)

    @staticmethod
    def _fetch_coordinates(city: str, country_code: str) -> Tuple[Optional[float], Optional[float]]:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "CityCoordinateFetcher/1.0"}

        try:
            logger.info(f"Fetching coordinates for {city}, {country_code}")
            params: dict[str, str | int] = {
                "city": city,
                "country": country_code,
                "format": "json",
                "limit": 1,
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
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

                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()

                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    logger.info(f"Successfully found coordinates using cleaned name: {cleaned_city}")
                    return lat, lng

            except Exception as e:
                logger.error(f"Error fetching coordinates for cleaned name {cleaned_city}, {country_code}: {e}")

        logger.warning(f"Could not find coordinates for {city}, {country_code}")
        return None, None
