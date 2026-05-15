from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime
import os
from pathlib import Path
import time
from typing import Optional

import numpy as np
import pandas as pd
from sgp4.api import Satrec, SatrecArray

from config import logger, tle_data_dir
from logger import LogUtils

CHUNK_SIZE = 500
CIRCLE_RADIUS_KM = 580
_A_KM = 6378.137
_E2 = 0.00669437999014
_KM_PER_DEG = 111.32


def _parse_tle_filename(path: Path) -> pd.Timestamp:
    return pd.Timestamp(datetime.strptime(path.stem, "%d-%m-%Y"), tz="UTC")


def _find_nearest_tle(target: date, available: list[Path]) -> tuple[Optional[Path], Optional[int]]:
    best_path, best_delta = None, None
    for path in available:
        file_date = _parse_tle_filename(path)
        if file_date is None:
            continue
        delta = abs((target - file_date.date()).days)
        if best_delta is None or delta < best_delta:
            best_path, best_delta = path, delta
    return best_path, best_delta


def _load_sats_from_tle_file(file_path: Path) -> SatrecArray:
    with open(file_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    satrecs = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i : i + 3]
        satrecs.append(Satrec.twoline2rv(l1, l2))
    return SatrecArray(satrecs)


def day_density_circle(
    args: tuple[pd.DataFrame, Path, float, str, bool, Optional[int]],
) -> tuple[np.ndarray, list[Optional[int]], dict]:
    group, tle_path, radius_km, date_label, is_fallback, fallback_delta = args
    t0 = time.monotonic()

    sat_array = _load_sats_from_tle_file(tle_path)

    valid_mask = (group["lat"].notna() & group["lon"].notna() & group["test_time"].notna()).to_numpy()

    filled_times = group["test_time"]
    unix_ns = filled_times.astype(np.int64).to_numpy() + 1000
    jd_full = unix_ns / (86400.0 * 1e9) + 2440587.5
    jd_arr = np.floor(jd_full)
    fr_arr = jd_full - jd_arr

    meas_lats = group["lat"].to_numpy()
    meas_lons = group["lon"].to_numpy()
    n_meas = len(group)

    counts = np.zeros(n_meas, dtype=np.int32)

    for start in range(0, n_meas, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, n_meas)
        jd_chunk = jd_arr[start:end]
        fr_chunk = fr_arr[start:end]

        e_chunk, r_chunk, _ = sat_array.sgp4(jd_chunk, fr_chunk)

        x_km = r_chunk[:, :, 0]
        y_km = r_chunk[:, :, 1]
        z_km = r_chunk[:, :, 2]

        lon_rad = np.arctan2(y_km, x_km)
        p = np.sqrt(x_km**2 + y_km**2)
        lat_rad = np.arctan2(z_km, p * (1.0 - _E2))
        for _ in range(3):
            sin_lat = np.sin(lat_rad)
            N = _A_KM / np.sqrt(1.0 - _E2 * sin_lat * sin_lat)
            lat_rad = np.arctan2(z_km + _E2 * N * sin_lat, p)

        sat_lats = np.degrees(lat_rad)
        sat_lons = np.degrees(lon_rad)

        chunk_lats = meas_lats[start:end]
        chunk_lons = meas_lons[start:end]

        dlat = sat_lats - chunk_lats[np.newaxis, :]
        dlon = sat_lons - chunk_lons[np.newaxis, :]
        cos_lat = np.cos(np.radians(chunk_lats))[np.newaxis, :]

        dist2 = (_KM_PER_DEG * dlat) ** 2 + (_KM_PER_DEG * cos_lat * dlon) ** 2
        within = (dist2 <= radius_km * radius_km) & (e_chunk == 0)
        counts[start:end] = within.sum(axis=0)

    density_list: list[Optional[int]] = [int(counts[i]) if valid_mask[i] else None for i in range(n_meas)]

    valid_counts = counts[valid_mask]
    stats = {
        "date": date_label,
        "n_measurements": len(group),
        "n_valid": int(valid_mask.sum()),
        "n_invalid": int((~valid_mask).sum()),
        "mean_density": (float(valid_counts.mean()) if valid_counts.size > 0 else float("nan")),
        "min_density": int(valid_counts.min()) if valid_counts.size > 0 else None,
        "max_density": int(valid_counts.max()) if valid_counts.size > 0 else None,
        "tle_file": tle_path.name,
        "is_fallback": is_fallback,
        "fallback_delta_days": fallback_delta,
        "elapsed_s": round(time.monotonic() - t0, 1),
    }

    return group.index.to_numpy(), density_list, stats


@LogUtils.log_function
def enrich_with_sat_density(df: pd.DataFrame) -> pd.DataFrame:
    t_start = time.monotonic()

    df = df.copy()
    df["test_time"] = pd.to_datetime(df["test_time"], format="mixed", utc=True)
    df["date"] = df["test_time"].dt.date

    day_groups: list[tuple[date, pd.DataFrame]] = [(day, group) for day, group in df.groupby("date")]
    n_days = len(day_groups)
    logger.info(f"Satellite density enrichment starting — {len(df):,} measurements across {n_days} dates")

    available_tle_files = sorted([p for p in tle_data_dir.glob("*.tle") if _parse_tle_filename(p) is not None])
    logger.info(f"Found {len(available_tle_files)} TLE files in {tle_data_dir}")

    args: list[tuple[pd.DataFrame, Path, float, date, bool, Optional[int]]] = []
    skipped_dates: list[str] = []
    for day, group in day_groups:
        exact_path = tle_data_dir / day.strftime("%d-%m-%Y.tle")
        if exact_path.exists():
            args.append((group, exact_path, CIRCLE_RADIUS_KM, day, False, None))
        else:
            fallback_path, delta = _find_nearest_tle(day, available_tle_files)
            if fallback_path is not None:
                fallback_date = _parse_tle_filename(fallback_path)
                sign = "+" if (day - fallback_date.date()).days >= 0 else "-"
                logger.warning(f"No exact TLE for {day} — using fallback {fallback_path.name} ({sign}{delta}d)")
                args.append((group, fallback_path, CIRCLE_RADIUS_KM, day, True, delta))
            else:
                logger.error(f"No TLE found for {day} — {len(group):,} measurements will be NaN")
                skipped_dates.append(str(day))

    n_scheduled = len(args)
    n_skipped = len(skipped_dates)
    logger.info(f"TLE resolution complete: {n_scheduled}/{n_days} dates scheduled, {n_skipped} skipped (no TLE found)")

    satdens = pd.Series(index=df.index, dtype="float64")
    max_workers = min(n_scheduled, os.cpu_count() or 2)
    completed = 0

    with ProcessPoolExecutor(max_workers=max_workers) as pex:
        for idxs, dens, stats in pex.map(day_density_circle, args):
            completed += 1
            satdens.loc[idxs] = np.asarray([np.nan if v is None else float(v) for v in dens], dtype="float64")

            tle_note = (
                f"fallback {stats['tle_file']} (±{stats['fallback_delta_days']}d)"
                if stats["is_fallback"]
                else stats["tle_file"]
            )
            invalid_note = f", {stats['n_invalid']} invalid" if stats["n_invalid"] > 0 else ""
            logger.info(
                f"[{completed}/{n_scheduled}] {stats['date']} — "
                f"{stats['n_valid']:,} measurements{invalid_note} — "
                f"density min/mean/max: {stats['min_density']}/{stats['mean_density']:.1f}/{stats['max_density']} — "
                f"TLE: {tle_note} — "
                f"{stats['elapsed_s']}s"
            )

    df["sat_density"] = satdens.reindex(df.index).tolist()
    df.drop(columns=["date"], inplace=True)

    elapsed = round(time.monotonic() - t_start, 1)
    n_enriched = int(satdens.notna().sum())
    n_null = int(satdens.isna().sum())
    logger.info(
        f"Satellite density enrichment complete — "
        f"{n_enriched:,} enriched, {n_null:,} null — "
        f"total time: {elapsed}s"
    )

    return df
