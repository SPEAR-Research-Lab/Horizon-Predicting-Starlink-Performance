from typing import (Callable, List, Literal, Optional, Tuple, TypeAlias,
                    TypedDict)

import pandas as pd


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


class Timefeatures(TypedDict):
    day_of_week: int
    month: int
    hour: int


Coordinate = Tuple[float, float]

FilterFunction: TypeAlias = Callable[[pd.DataFrame, float, list[str]], pd.DataFrame]


class FiltrationConfig(TypedDict):
    args: list[float]
    name: str


FiltrationDict: TypeAlias = dict[FilterFunction, FiltrationConfig]

FeatureName: TypeAlias = Literal[
    "download_latency_ms",
    "download_throughput_mbps",
]

FeatureGroup: TypeAlias = Tuple[FeatureName, ...]


class TargetConfig(TypedDict):
    preferred_filtration: Optional[str]
    preferred_months: Optional[list[int]]
    save_model: bool
