from dataclasses import dataclass
from typing import Any


@dataclass
class SatelliteData:
    satName: str
    lat: Any
    long: Any


@dataclass
class GroundStation:
    name: str
    lat: float
    long: float


SatelliteList = list[SatelliteData]
GroundStationList = list[GroundStation]
