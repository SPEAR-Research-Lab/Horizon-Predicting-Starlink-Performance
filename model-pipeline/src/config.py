from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path

from logger import LogUtils

logger = LogUtils.init_logger()

src_dir = Path(__file__).resolve().parent
model_pipeline_root = src_dir.parent
project_root = model_pipeline_root.parent

data_dir = model_pipeline_root / "data"
weather_data_dir = model_pipeline_root / "weather_data"
models_dir = model_pipeline_root / "models"
filetered_csv_dir = model_pipeline_root / "filtered"

sat_dir = project_root / "satellite-data" / "data"

os.makedirs(models_dir, exist_ok=True)
os.makedirs(weather_data_dir, exist_ok=True)
os.makedirs(filetered_csv_dir, exist_ok=True)


@dataclass(frozen=True)
class EnumFiles:
    world_cities_coords = "world_cities_coordinates.csv"
    client_server_distance = "client_server_distance.csv"
    model_training_stats = "model_training_stats.csv"


df_final_columns = [
    "uuid",
    "test_time",
    "data_source",
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
    "lat",
    "lon",
    "client_server_distance_km",
    "temperature_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "hour",
    "hour_with_minute",
    "day_of_week",
    "month",
    "year",
    "sat_density",
}

df_features_download = df_common_features.union(
    {
        "download_latency_ms",
        "download_jitter_ms",
        "download_throughput_mbps",
    }
)

df_features_upload = df_common_features.union(
    {
        "upload_latency_ms",
        "upload_jitter_ms",
        "upload_throughput_mbps",
    }
)

dtype_spec = defaultdict(
    lambda: "string",
    {
        "asn": "int64",
        "packet_loss_rate": "float32",
        "download_throughput_mbps": "float32",
        "download_latency_ms": "float32",
        "download_jitter_ms": "float32",
        "upload_throughput_mbps": "float32",
        "upload_latency_ms": "float32",
        "upload_jitter_ms": "float32",
        "lat": "float32",
        "lon": "float32",
        "sat_density": "int64",
        "client_server_distance_km": "float32",
        "hour": "int64",
        "hour_with_minute": "float32",
        "day_of_week": "int64",
        "month": "int64",
        "year": "int64",
        "temperature_2m": "float32",
        "precipitation": "float32",
        "cloud_cover": "float32",
        "wind_speed_10m": "float32",
    },
)
