from dataclasses import dataclass
from typing import List, Tuple, TypedDict


class HistoricalParams(TypedDict):
    latitude: float
    longitude: float
    start_date: str
    end_date: str
    hourly: List[str]
    timezone: str


class ForecastParams(TypedDict):
    latitude: float
    longitude: float
    hourly: List[str]
    past_days: int
    forecast_days: int


class WeatherData(TypedDict):
    temperature_2m: float
    precipitation: float
    cloud_cover: float
    wind_speed_10m: float


Coordinate = Tuple[float, float]


@dataclass(frozen=True)
class TargetFeatures:
    download_latency = "download_latency_ms"
    download_throughput = "download_throughput_mbps"
