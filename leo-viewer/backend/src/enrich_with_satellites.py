import math
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from sgp4.api import Satrec, jday
from skyfield.api import load
from skyfield.framelib import itrs
from skyfield.positionlib import ICRF
from tqdm import tqdm

from .__init__ import data_dir, logger

RADIUS_KM = 500
TLE_PATH = data_dir / "today-sat-tle.txt"
CELESTRAK_STARLINK = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"


def fetch_starlink_tle(tle_path: Path) -> None:
    resp = requests.get(CELESTRAK_STARLINK)
    resp.raise_for_status()
    tle_path.write_text(resp.text)
    logger.info(f"Downloaded Starlink TLE to {tle_path}")


def load_satellites_from_file(file_path: Path) -> list[tuple]:
    lines = [line.strip() for line in file_path.read_text().splitlines() if line.strip()]
    satellites = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i : i + 3]
        satellites.append((Satrec.twoline2rv(l1, l2), name, l1, l2))
    return satellites


def fast_density_per_row(lat: float, lon: float, dt, sats: list[tuple]) -> int:
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
    count = 0
    ts = load.timescale()
    t_sf = ts.tt_jd(jd + fr)
    for sat, name, l1, l2 in sats:
        e, r, v = sat.sgp4(jd, fr)
        if e != 0:
            continue
        x, y, z = r
        try:
            pos = ICRF([x * 1000, y * 1000, z * 1000], t=t_sf, center=399)
            lat_sgf, lon_sgf, _ = pos.frame_latlon(itrs)
            lon_deg = lon_sgf.degrees
            if lon_deg > 180:
                lon_deg -= 360
            lat_deg = lat_sgf.degrees
            if math.isnan(lat_deg) or math.isnan(lon_deg):
                continue
            from geopy.distance import geodesic

            dist = geodesic((lat, lon), (lat_deg, lon_deg)).km
            if dist <= RADIUS_KM:
                count += 1
        except Exception:
            continue
    return count


def enrich_with_sat_density(input_csv: Path, output_csv: Path) -> None:
    if not TLE_PATH.exists():
        fetch_starlink_tle(TLE_PATH)
    sats = load_satellites_from_file(TLE_PATH)
    logger.info(f"Loaded {len(sats)} satellites from TLE")

    df = pd.read_csv(input_csv)
    lat_col = "lat" if "lat" in df.columns else "Latitude"
    lon_col = "lon" if "lon" in df.columns else "Longitude"

    df["TestTimeUTC"] = pd.to_datetime(df["Date"] + " " + df["Hour"].astype(str) + ":00:00", utc=True)
    df = df[df[lat_col].notna() & df[lon_col].notna()]

    def row_worker(row):
        return fast_density_per_row(row[lat_col], row[lon_col], row["TestTimeUTC"], sats)

    logger.info(f"Computing satellite density for {len(df)} rows...")
    with ThreadPoolExecutor() as executor:
        densities = list(tqdm(executor.map(row_worker, [row for _, row in df.iterrows()]), total=len(df), desc="SatDensity"))

    df["sat_density"] = densities
    df.drop(columns=["TestTimeUTC"], inplace=True)
    df.to_csv(output_csv, index=False)
    logger.info(f"Wrote {output_csv}")


INPUT_FILES = [
    "hex_centers_res2_weather.csv",
    "hex_centers_res3_weather.csv",
    "hex_centers_res4_weather.csv",
]


if __name__ == "__main__":
    for fname in INPUT_FILES:
        inpath = data_dir / fname
        if inpath.exists():
            outpath = data_dir / fname.replace("_weather.csv", "_weather_satellites.csv")
            enrich_with_sat_density(inpath, outpath)
        else:
            logger.warning(f"Skipping {inpath} (not found)")
