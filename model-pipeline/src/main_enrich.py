import pandas as pd
from inter_city_distance_calculator import DistanceCalculator
from meteo_data_handler import WeatherDataHandler
from open_meteo_fetcher import OpenMeteoFetcher
from constants import df_common_features, logger, dtype_spec, df_final_columns
import os

distance_calculator = DistanceCalculator()
weather_data_handler = WeatherDataHandler()
open_meteo_fetcher = OpenMeteoFetcher()

CLIENT_CITIES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "client_cities.csv")
all_client_cities: set[tuple[str, str]] = set()


def enrich_data_file(src_file_path: str, dst_file_path: str) -> None:
    df = pd.read_csv(src_file_path, dtype=dtype_spec, low_memory=False)

    df = df.dropna(subset=["client_city", "client_country_code", "server_city", "server_country_code", "test_time"])
    df = df.reset_index(drop=True)
    df = df.rename(columns={"SatDensityCircle": "sat_density"})
    logger.info(f"Processing {src_file_path} with {len(df)} rows...")

    logger.info(f"Time feature extraction...")
    test_time_dt = pd.to_datetime(df['test_time'], format='mixed', utc=True)
    df['hour'] = test_time_dt.dt.hour
    df['hour_with_minute'] = round(test_time_dt.dt.hour + test_time_dt.dt.minute / 60.0, 2)
    df['day_of_week'] = test_time_dt.dt.dayofweek
    df['month'] = test_time_dt.dt.month
    df['year'] = test_time_dt.dt.year

    logger.info(f"Latitude and longitude extraction...")
    unique_clients = df[['client_city', 'client_country_code']].drop_duplicates()

    for _, row in unique_clients.iterrows():
        all_client_cities.add((str(row['client_city']), str(row['client_country_code'])))

    coords_map = {}
    cities_not_found = []
    for _, row in unique_clients.iterrows():
        city = row['client_city']
        country = row['client_country_code']
        coords = distance_calculator.get_city_coordinates(city, country)
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
        lambda row: coords_map.get((row['client_city'], row['client_country_code'])), axis=1)
    df['lat'] = df['coords'].apply(lambda x: x[0] if x and len(x) >= 2 else float('nan'))
    df['lon'] = df['coords'].apply(lambda x: x[1] if x and len(x) >= 2 else float('nan'))
    df = df.drop('coords', axis=1)

    logger.info(f"Client-server distances extraction...")
    unique_routes = df[['client_city', 'client_country_code', 'server_city', 'server_country_code']].drop_duplicates()
    distance_map = {}

    for _, row in unique_routes.iterrows():
        key = (row['client_city'], row['client_country_code'], row['server_city'], row['server_country_code'])
        distance = distance_calculator.get_distance_between_cities(*key)
        distance_map[key] = distance

    df['client_server_distance_km'] = df[
        ['client_city', 'client_country_code', 'server_city', 'server_country_code']].apply(
        lambda row: distance_map.get((row['client_city'], row['client_country_code'],
                                      row['server_city'], row['server_country_code']), float('nan')),
        axis=1
    )

    logger.info(f"Weather feature extraction...")
    open_meteo_fetcher.fetch_weather_data_for_dataframe(df)
    def add_weather_data(row):
        try:
            weather_data = weather_data_handler.get_weather_data_for_city_and_time(
                str(row['client_city']),
                str(row['client_country_code']),
                str(row['test_time']))
            row['temperature_2m'] = weather_data.get('temperature_2m', float('nan'))
            row['precipitation'] = weather_data.get('precipitation', float('nan'))
            row['cloud_cover'] = weather_data.get('cloud_cover', float('nan'))
            row['wind_speed_10m'] = weather_data.get('wind_speed_10m', float('nan'))
        except Exception as e:
            logger.error(
                f"Error fetching weather for {row['client_city']}, {row['client_country_code']} at {row['test_time']}: {e}")
            row['temperature_2m'] = float('nan')
            row['precipitation'] = float('nan')
            row['cloud_cover'] = float('nan')
            row['wind_speed_10m'] = float('nan')
        return row

    df = df.apply(add_weather_data, axis=1)

    df = df.dropna(subset=list(df_common_features))
    df = df[df_final_columns].reset_index(drop=True)
    df.to_csv(dst_file_path, index=False)
    logger.info(f"Completed enrichment of {dst_file_path}. Final row count: {len(df)}")


def enrich_data_directory(src_dir: str, dst_dir: str) -> None:
    if os.path.exists(CLIENT_CITIES_FILE):
        existing_cities_df = pd.read_csv(CLIENT_CITIES_FILE)
        for _, row in existing_cities_df.iterrows():
            all_client_cities.add((str(row['city']), str(row['country'])))
        logger.info(f"Loaded {len(all_client_cities)} existing client cities")

    for file in os.listdir(src_dir):
        if file.endswith(".csv"):
            logger.info(f"Enriching data file: {file}")
            base_name = file.split(".")[0]
            enrich_data_file(os.path.join(src_dir, file), os.path.join(dst_dir, base_name + "_enriched.csv"))
    cities_df = pd.DataFrame(sorted(all_client_cities), columns=['city', 'country'])
    cities_df.to_csv(CLIENT_CITIES_FILE, index=False)
    logger.info(f"Saved {len(all_client_cities)} unique client cities to {CLIENT_CITIES_FILE}")

if __name__ == "__main__":
    src_dir = "/Users/user/Documents/slides/_RP/model-data-pipeline/data/__enrich-training"
    dst_dir = "/Users/user/Documents/slides/_RP/model-data-pipeline/data/__enrich-training"
    enrich_data_directory(src_dir, dst_dir)
