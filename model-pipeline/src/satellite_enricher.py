import os
import re
import math
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from sgp4.api import Satrec, jday
from pyproj import Transformer
from datetime import date
import unicodedata
from collections import defaultdict

CIRCLE_RADIUS_KM = 580

TRANSFORMER = transformer = Transformer.from_crs(
    {"proj": "geocent", "ellps": "WGS84"},
    {"proj": "latlong", "ellps": "WGS84"},
    always_xy=True
)

_SUFFIXES = [
    " municipality", " district", " region", " province", " state",
    " city", " town", " village", " shire", " borough", " county"
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

def _enu_distance_km(lat0_deg: float, lon0_deg: float,
                     lat1_deg: float, lon1_deg: float) -> float:
    km_per_deg = 111.32
    dlat = lat1_deg - lat0_deg
    dlon = lon1_deg - lon0_deg
    east_km = km_per_deg * math.cos(math.radians(lat0_deg)) * dlon
    north_km = km_per_deg * dlat
    return math.sqrt(east_km**2 + north_km**2)

def _in_circle(lat0, lon0, lat1, lon1, radius_km):
    return _enu_distance_km(lat0, lon0, lat1, lon1) <= radius_km

def sat_density_circle_fast(lat0, lon0, dt_utc, sats, radius_km):
    jd, fr = jday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour, dt_utc.minute,
        dt_utc.second + dt_utc.microsecond / 1e6
    )

    cnt = 0
    for sat, name, l1, l2 in sats:
        e, r, v = sat.sgp4(jd, fr)
        if e != 0:
            continue
        x, y, z = r
        try:
            lon_deg, lat_deg, _ = TRANSFORMER.transform(
                x * 1000, y * 1000, z * 1000, radians=False
            )
        except:
            continue
        if math.isnan(lat_deg) or math.isnan(lon_deg):
            continue
        if _in_circle(lat0, lon0, lat_deg, lon_deg, radius_km):
            cnt += 1
    return cnt

def build_city_index(coords_csv: str):
    df = pd.read_csv(coords_csv)
    df["_city_key"] = df["city"].astype(str).map(norm_text)
    df["_iso2_key"] = df["country"].astype(str).str.upper().fillna("")

    by_pair = {}
    by_city = defaultdict(list)

    for _, r in df.iterrows():
        ckey = r["_city_key"]
        iso2 = r["_iso2_key"]
        try:
            lat = float(r["lat"]); lng = float(r["lng"])
        except:
            continue
        if ckey and iso2:
            by_pair[(ckey, iso2)] = (lat, lng)
        if ckey:
            by_city[ckey].append((lat, lng))

    city_unique = {ck: vals[0] for ck, vals in by_city.items() if len(vals) == 1}
    return by_pair, city_unique

TLE_RE = re.compile(r"^tle_(\d{8})T140001\.txt$")
TLE_DATE_ONLY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})$")

def index_tle_1400_paths(sat_dir: str):
    paths = {}
    date_only_paths = {}
    for fn in os.listdir(sat_dir):
        m = TLE_RE.match(fn)
        if m:
            paths[m.group(1)] = os.path.join(sat_dir, fn)
        else:
            m_date = TLE_DATE_ONLY_RE.match(fn)
            if m_date:
                date_str = m_date.group(1).replace("-", "")
                date_only_paths[date_str] = os.path.join(sat_dir, fn)
    return paths, date_only_paths

def load_sats_from_tle_file(file_path):
    with open(file_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    sats = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i:i+3]
        sats.append((Satrec.twoline2rv(l1, l2), name, l1, l2))
    return sats

def day_density_circle(args):
    group, tle_path, radius_km = args
    sats = load_sats_from_tle_file(tle_path)

    def row_worker(row):
        lat0 = row["lat"]
        lon0 = row["lon"]
        dt = row["test_time"]
        if pd.isna(dt):
            return None
        return sat_density_circle_fast(lat0, lon0, dt.to_pydatetime(), sats, radius_km)

    with ThreadPoolExecutor() as executor:
        densities = list(
            tqdm(
                executor.map(row_worker, (r[1] for r in group.iterrows())),
                total=len(group),
                desc=f"Circle {group['date'].iloc[0]}"
            )
        )

    return group.index.to_numpy(), densities

def enrich_with_sat_density(df: pd.DataFrame, coords_csv: str, sat_dir: str, radius_km: int = CIRCLE_RADIUS_KM) -> pd.DataFrame:
    """Enrich dataframe with satellite density in circle.

    Args:
        df: Input dataframe with 'lat', 'lon', 'test_time' columns
        coords_csv: Path to world_cities_coordinates.csv
        sat_dir: Path to directory containing TLE files
        radius_km: Circle radius in km

    Returns:
        DataFrame with 'sat_density' column added
    """
    df = df.copy()
    df["test_time"] = pd.to_datetime(df["test_time"], utc=True, errors="coerce")

    df["date"] = df["test_time"].dt.date
    day_groups: list[tuple[date, pd.DataFrame]] = [(day, group) for day, group in df.groupby("date")]
    tle_paths, date_only_paths = index_tle_1400_paths(sat_dir)

    args = []
    for day, group in day_groups:
        key = day.strftime("%Y%m%d")
        if key in tle_paths:
            args.append((group, tle_paths[key], radius_km))
        elif key in date_only_paths:
            args.append((group, date_only_paths[key], radius_km))

    satdens = pd.Series(index=df.index, dtype="float64")

    with ProcessPoolExecutor() as pex:
        for idxs, dens in tqdm(pex.map(day_density_circle, args), total=len(args), desc="Calculating satellite density"):
            satdens.loc[idxs] = dens

    df["sat_density"] = satdens.reindex(df.index).tolist()
    df.drop(columns=["date"], inplace=True)

    return df
