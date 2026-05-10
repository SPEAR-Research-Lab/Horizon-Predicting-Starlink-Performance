from pathlib import Path
from logger import LogUtils
from collections import defaultdict
import os

script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent.parent

root_dir = project_root
data_dir = project_root / 'data'
client_cities_file = data_dir / 'client_cities.csv'
model_pipeline_dir = project_root / 'model-pipeline'
data_training_dir = model_pipeline_dir / 'data' / 'processed'
weather_data_dir = model_pipeline_dir / 'weather_data'
starlink_data_dir = model_pipeline_dir / 'starlink_data'
models_dir = model_pipeline_dir / 'models'
os.makedirs(models_dir, exist_ok=True)
os.makedirs(weather_data_dir, exist_ok=True)
os.makedirs(starlink_data_dir, exist_ok=True)

filtration_dir_base = {'filtered_percentile', 'filtered_directional_mad', 'filtered_isolation_forest'}


df_final_columns = [
    "uuid", "test_time", "data_source", "client_city", "client_country_code",
    "server_city", "server_country_code", "packet_loss_rate",
    "download_throughput_mbps", "download_latency_ms", "download_jitter_ms",
    "lat", "lon", "sat_density", "hour", "hour_with_minute", "day_of_week",
    "month", "year", "client_server_distance_km", "temperature_2m",
    "precipitation", "cloud_cover", "wind_speed_10m"
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

df_features_download = df_common_features.union({
    'download_latency_ms',
    'download_jitter_ms',
    'download_throughput_mbps',
})

df_features_upload = df_common_features.union({
    'upload_latency_ms',
    'upload_jitter_ms',
    'upload_throughput_mbps',
})

dtype_spec = defaultdict(lambda: 'string', {
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
})

logger = LogUtils.init_logger()
