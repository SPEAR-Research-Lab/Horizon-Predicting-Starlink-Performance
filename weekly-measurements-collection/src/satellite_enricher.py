from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
import math
from pathlib import Path
import re
from typing import Optional
import unicodedata

import numpy as np
import pandas as pd
from pyproj import Transformer
from sgp4.api import Satrec, jday
from tqdm import tqdm

from config import data_dir, logger, tle_data_dir
from enums import CsvFiles

CIRCLE_RADIUS_KM = 580

_SUFFIXES = [
    " municipality",
    " district",
    " region",
    " province",
    " state",
    " city",
    " town",
    " village",
    " shire",
    " borough",
    " county",
]

_ALIASES = {
    "ulan bator": "ulaanbaatar",
    "nukualofa": "nuku'alofa",
    "st peter port": "saint peter port",
    "yaren district": "yaren",
    "haganta": "hagatna",
    "hagatna": "hagatna",
    "mariehamns stad": "mariehamn",
    "adelaide hills": "adelaide",
    "lima region": "lima",
}

_SPACES = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s']+")


def _strip_diacritics(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def norm_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    if s.lower() in {"nan", "none", ""}:
        return ""
    s = _strip_diacritics(s).lower()
    s = _PUNCT.sub(" ", s)
    for suf in _SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)]
    s = _SPACES.sub(" ", s).strip()
    return _ALIASES.get(s, s)


def _enu_distance_km(lat0_deg: float, lon0_deg: float, lat1_deg: float, lon1_deg: float) -> float:
    km_per_deg = 111.32
    dlat = lat1_deg - lat0_deg
    dlon = lon1_deg - lon0_deg
    east_km = km_per_deg * math.cos(math.radians(lat0_deg)) * dlon
    north_km = km_per_deg * dlat
    return math.sqrt(east_km**2 + north_km**2)


def _in_circle(lat0: float, lon0: float, lat1: float, lon1: float, radius_km: float) -> bool:
    return _enu_distance_km(lat0, lon0, lat1, lon1) <= radius_km


def sat_density_circle_fast(
    lat0: float, lon0: float, dt_utc: datetime, sats: list, transformer: Transformer, radius_km: float
) -> int:
    jd, fr = jday(
        dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute, dt_utc.second + dt_utc.microsecond / 1e6
    )

    cnt = 0
    for sat, name, l1, l2 in sats:
        e, r, v = sat.sgp4(jd, fr)
        if e != 0:
            continue
        x, y, z = r
        try:
            lon_deg, lat_deg, _ = transformer.transform(x * 1000, y * 1000, z * 1000, radians=False)
        except Exception as e:
            logger.warning(f"Error occurred while transforming satellite position for {name}: {e}")
            continue
        if math.isnan(lat_deg) or math.isnan(lon_deg):
            continue
        if _in_circle(lat0, lon0, lat_deg, lon_deg, radius_km):
            cnt += 1
    return cnt


def build_city_index() -> tuple[dict[tuple[str, str], tuple[float, float]], dict[str, tuple[float, float]]]:
    logger.info("Building city index from world cities coordinates...")
    df = pd.read_csv(data_dir / CsvFiles.WORLD_CITIES_COORDINATES.value)
    logger.info(f"Loaded {len(df)} cities from database")
    df["_city_key"] = df["city"].astype(str).map(norm_text)
    df["_iso2_key"] = df["country"].astype(str).str.upper().fillna("")

    by_pair = {}
    by_city = defaultdict(list)

    for _, r in df.iterrows():
        ckey = r["_city_key"]
        iso2 = r["_iso2_key"]
        try:
            lat = float(r["lat"])
            lng = float(r["lng"])
        except Exception as e:
            logger.warning(f"Error occurred while parsing coordinates for {r['city']}: {e}")
            continue
        if ckey and iso2:
            by_pair[(ckey, iso2)] = (lat, lng)
        if ckey:
            by_city[ckey].append((lat, lng))

    city_unique = {ck: vals[0] for ck, vals in by_city.items() if len(vals) == 1}
    logger.info(f"City index built: {len(by_pair)} city-country pairs, {len(city_unique)} unique cities")
    return by_pair, city_unique


CITY_BY_PAIR: dict[tuple[str, str], tuple[float, float]] = {}
CITY_UNIQUE: dict[str, tuple[float, float]] = {}


@lru_cache(maxsize=500_000)
def resolve_lat_lon_cached(
    city_raw: str, region_raw: str, iso2_raw: str
) -> tuple[Optional[float], Optional[float], int]:
    city_k = norm_text(city_raw)
    region_k = norm_text(region_raw)
    iso2_k = (iso2_raw or "").upper()

    if city_k and iso2_k and (city_k, iso2_k) in CITY_BY_PAIR:
        return *CITY_BY_PAIR[(city_k, iso2_k)], 1

    if region_k and iso2_k and (region_k, iso2_k) in CITY_BY_PAIR:
        return *CITY_BY_PAIR[(region_k, iso2_k)], 2

    if city_k and city_k in CITY_UNIQUE:
        return *CITY_UNIQUE[city_k], 3

    return None, None, 0


def load_sats_from_tle_file(file_path: Path) -> list[tuple[Satrec, str, str, str]]:
    with open(file_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    sats = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i : i + 3]
        sats.append((Satrec.twoline2rv(l1, l2), name, l1, l2))
    logger.debug(f"Loaded {len(sats)} satellites from {file_path.name}")
    return sats


def day_density_circle(args: tuple[pd.DataFrame, Path, float]) -> tuple[np.ndarray, list[Optional[int]]]:
    group, tle_path, radius_km = args

    sats = load_sats_from_tle_file(tle_path)
    transformer = Transformer.from_crs(
        {"proj": "geocent", "ellps": "WGS84"}, {"proj": "latlong", "ellps": "WGS84"}, always_xy=True
    )

    def row_worker(row: pd.Series) -> Optional[int]:
        lat0 = row["lat"]
        lon0 = row["lon"]
        dt = row["test_time"]
        if pd.isna(dt) or pd.isna(lat0) or pd.isna(lon0):
            return None
        return sat_density_circle_fast(lat0, lon0, dt.to_pydatetime(), sats, transformer, radius_km)

    with ThreadPoolExecutor() as executor:
        densities = list(
            tqdm(
                executor.map(row_worker, (r[1] for r in group.iterrows())),
                total=len(group),
                desc=f"Circle {group['date'].iloc[0]}",
            )
        )

    return group.index.to_numpy(), densities


def enrich_with_sat_density(df: pd.DataFrame) -> pd.DataFrame:
    global CITY_BY_PAIR, CITY_UNIQUE

    logger.info(f"Starting satellite density enrichment for {len(df)} rows")
    if not CITY_BY_PAIR:
        CITY_BY_PAIR, CITY_UNIQUE = build_city_index()

    df = df.copy()
    df["test_time"] = pd.to_datetime(df["test_time"], utc=True, errors="coerce")

    df["date"] = df["test_time"].dt.date
    day_groups = [(d, g) for d, g in df.groupby("date")]
    logger.info(f"Data spans {len(day_groups)} unique dates")

    args = []
    missing_dates = []
    for d, g in day_groups:
        d = pd.Timestamp(str(d))
        tle_filename = d.strftime("%d-%m-%Y.tle")
        tle_path = tle_data_dir / tle_filename

        if tle_path.exists():
            args.append((g, tle_path, CIRCLE_RADIUS_KM))
        else:
            missing_dates.append(str(d))

    if missing_dates:
        logger.warning(f"No TLE data found for {len(missing_dates)} dates: {missing_dates}")

    satdens = pd.Series(index=df.index, dtype="float64")

    with ProcessPoolExecutor() as pex:
        for idxs, dens in tqdm(
            pex.map(day_density_circle, args), total=len(args), desc="Calculating satellite density"
        ):
            satdens.loc[idxs] = np.asarray(dens, dtype="float64")

    df["sat_density"] = satdens.reindex(df.index).tolist()
    df.drop(columns=["date"], inplace=True)
    logger.info("Satellite density enrichment complete.")

    return df
