import pandas as pd

from config import df_common_features, df_final_columns, logger
from inter_city_distance_calculator import DistanceCalculator
from meteo_data_handler import WeatherDataHandler
from satellite_enricher import enrich_with_sat_density


class DataEnricher:
    def __init__(self, distance_calculator: DistanceCalculator, weather_data_handler: WeatherDataHandler):
        self._distance_calculator = distance_calculator
        self._weather_data_handler = weather_data_handler

    def enrich_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(subset=["client_city", "client_country_code", "server_city", "server_country_code", "test_time"])
        df = df.reset_index(drop=True)
        logger.info(f"Processing DataFrame with {len(df)} rows...")

        logger.info("Time feature extraction...")
        test_time_dt = pd.to_datetime(df['test_time'], format='mixed', utc=True)
        df['hour'] = test_time_dt.dt.hour
        df['hour_with_minute'] = round(test_time_dt.dt.hour + test_time_dt.dt.minute / 60.0, 2)
        df['day_of_week'] = test_time_dt.dt.dayofweek
        df['month'] = test_time_dt.dt.month
        df['year'] = test_time_dt.dt.year

        logger.info("Latitude and longitude extraction...")
        unique_clients = df[['client_city', 'client_country_code']].drop_duplicates()

        coords_map = {}
        cities_not_found = []
        for _, row in unique_clients.iterrows():
            city = row['client_city']
            country = row['client_country_code']
            coords = self._distance_calculator.get_city_coordinates(city, country)
            coords_map[(city, country)] = coords
            if coords is None or len(coords) < 2 or any(pd.isna(c) for c in coords[:2]):
                cities_not_found.append((city, country))

        if cities_not_found:
            logger.warning(f"Coordinates not found for {len(cities_not_found)} cities:")
            for city, country in cities_not_found:
                logger.warning(f"  - {city}, {country}")
            if len(cities_not_found) > 20:
                logger.warning(f"  ... and {len(cities_not_found) - 20} more")

        df['coords'] = df[['client_city', 'client_country_code']].apply(
            lambda row: coords_map.get((row['client_city'], row['client_country_code'])), axis=1
        )
        df['lat'] = df['coords'].apply(lambda x: x[0] if x and len(x) >= 2 else float('nan'))
        df['lon'] = df['coords'].apply(lambda x: x[1] if x and len(x) >= 2 else float('nan'))
        df = df.drop('coords', axis=1)

        logger.info("Client-server distances extraction...")
        unique_routes = df[
            ['client_city', 'client_country_code', 'server_city', 'server_country_code']
        ].drop_duplicates()
        distance_map = {}

        for _, row in unique_routes.iterrows():
            key = (row['client_city'], row['client_country_code'], row['server_city'], row['server_country_code'])
            distance = self._distance_calculator.get_distance_between_cities(*key)
            distance_map[key] = distance

        df['client_server_distance_km'] = df[
            ['client_city', 'client_country_code', 'server_city', 'server_country_code']
        ].apply(
            lambda row: distance_map.get(
                (row['client_city'], row['client_country_code'], row['server_city'], row['server_country_code']),
                float('nan'),
            ),
            axis=1,
        )

        logger.info("Weather feature extraction...")
        df = self.enrich_df_with_weather(df)

        logger.info("Satellite density extraction...")
        df = enrich_with_sat_density(df)

        df = df.dropna(subset=list(df_common_features))
        df = df[df_final_columns].reset_index(drop=True)
        logger.info(f"Final DataFrame has {len(df)} rows.")
        return df

    def enrich_df_with_weather(self, df: pd.DataFrame) -> pd.DataFrame:
        def add_weather_data(row: pd.Series) -> pd.Series:
            try:
                weather_data = self._weather_data_handler.get_weather_data_for_city_and_time(
                    str(row['client_city']), str(row['client_country_code']), str(row['test_time'])
                )
                row['temperature_2m'] = weather_data.get('temperature_2m', float('nan'))
                row['precipitation'] = weather_data.get('precipitation', float('nan'))
                row['cloud_cover'] = weather_data.get('cloud_cover', float('nan'))
                row['wind_speed_10m'] = weather_data.get('wind_speed_10m', float('nan'))
            except Exception:
                logger.exception(
                    f"Error fetching weather for {row['client_city']}, {row['client_country_code']} at {row['test_time']}"
                )
                row['temperature_2m'] = float('nan')
                row['precipitation'] = float('nan')
                row['cloud_cover'] = float('nan')
                row['wind_speed_10m'] = float('nan')
            return row

        return df.apply(add_weather_data, axis=1)
