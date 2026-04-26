import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from skyfield.api import EarthSatellite, load, wgs84

from .__init__ import data_dir, logger
from .custom_types import SatelliteData, SatelliteList


def calculate_satellites(dt: Optional[datetime] = None) -> SatelliteList:
    csv_path = data_dir / "starlink.csv"
    try:
        with load.open(str(csv_path), mode="r") as f:
            data = list(csv.DictReader(f))
    except FileNotFoundError:
        raise FileNotFoundError("No orbital element data found. Place starlink.csv in backend/data/.")

    ts = load.timescale()
    sats = [EarthSatellite.from_omm(ts, fields) for fields in data]
    logger.info(f"Loaded {len(sats)} satellites")

    result: SatelliteList = []
    t = ts.from_datetime(dt) if dt else ts.now()
    logger.info(f"Calculated satellite locations at {t}")

    for sat in sats:
        geocentric = sat.at(t)
        lat, lon = wgs84.latlon_of(geocentric)
        if lat.degrees == lat.degrees and lon.degrees == lon.degrees:
            result.append(SatelliteData(satName=str(sat.name), lat=lat.degrees, long=lon.degrees))

    return result
