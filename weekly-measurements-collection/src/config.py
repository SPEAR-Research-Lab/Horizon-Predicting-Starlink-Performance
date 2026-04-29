import os
from pathlib import Path

from logger import LogUtils

logger = LogUtils.init_logger()
data_dir = (Path(__file__).parent / ".." / "data").resolve()
measurements_dir = (Path(__file__).parent / ".." / "measurements").resolve()

os.makedirs(data_dir, exist_ok=True)
os.makedirs(measurements_dir, exist_ok=True)

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
