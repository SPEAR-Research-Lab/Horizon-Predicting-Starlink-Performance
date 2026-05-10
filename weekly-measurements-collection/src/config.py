from collections import defaultdict
import os
from pathlib import Path

from attr import dataclass

from logger import LogUtils

logger = LogUtils.init_logger()
data_dir = (Path(__file__).parent / ".." / "data").resolve()
measurements_dir = (Path(__file__).parent / ".." / "measurements").resolve()
tle_data_dir = (Path(__file__).parent / ".." / ".." / "satellite-data" / "data").resolve()
weather_data_dir = (Path(__file__).parent / ".." / "weather_data").resolve()


os.makedirs(data_dir, exist_ok=True)
os.makedirs(measurements_dir, exist_ok=True)
os.makedirs(weather_data_dir, exist_ok=True)


@dataclass(frozen=True)
class CsvFiles:
    cities = "cities.csv"
    airport_codes = "airport-codes.csv"
    ndt_best_starlink_servers = "ndt-best-starlink-servers.csv"
    cf_best_starlink_servers = "cf-best-starlink-servers.csv"
    last_update_file = "last_update.csv"
    client_cities = "client_cities.csv"
    client_server_distance = "client_server_distance.csv"
    world_cities_coordinates = "world_cities_coordinates.csv"
    unresolved_cities = "unresolved_cities.csv"
    server_locations = "server_locations.csv"
    prediction_points = "prediction_points.csv"


columns = [
    "uuid",
    "test_time",
    "client_city",
    "client_region",
    "client_country_code",
    "server_city",
    "server_country_code",
    "data_source",
    "asn",
    "packet_loss_rate",
    "download_throughput_mbps",
    "download_latency_ms",
    "download_jitter_ms",
    "upload_throughput_mbps",
    "upload_latency_ms",
    "upload_jitter_ms",
]
df_final_columns = [
    "uuid",
    "test_time",
    "data_source",
    "asn",
    "client_city",
    "client_country_code",
    "server_city",
    "server_country_code",
    "packet_loss_rate",
    "download_throughput_mbps",
    "download_latency_ms",
    "download_jitter_ms",
    "lat",
    "lon",
    "sat_density",
    "hour",
    "hour_with_minute",
    "day_of_week",
    "month",
    "year",
    "client_server_distance_km",
    "temperature_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
]

df_common_features = {
    'lat',
    'lon',
    'client_server_distance_km',
    'temperature_2m',
    'precipitation',
    'cloud_cover',
    'wind_speed_10m',
    'hour',
    'hour_with_minute',
    'day_of_week',
    'month',
    'year',
    'sat_density',
}

dtype_spec = defaultdict(
    lambda: 'string',
    {
        'asn': 'int64',
        'packet_loss_rate': 'float32',
        'download_throughput_mbps': 'float32',
        'download_latency_ms': 'float32',
        'download_jitter_ms': 'float32',
        'upload_throughput_mbps': 'float32',
        'upload_latency_ms': 'float32',
        'upload_jitter_ms': 'float32',
        'lat': 'float32',
        'lon': 'float32',
        'sat_density': 'int64',
        'client_server_distance_km': 'float32',
        'hour': 'int64',
        'hour_with_minute': 'float32',
        'day_of_week': 'int64',
        'month': 'int64',
        'year': 'int64',
        'temperature_2m': 'float32',
        'precipitation': 'float32',
        'cloud_cover': 'float32',
        'wind_speed_10m': 'float32',
    },
)
