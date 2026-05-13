"""
Adaptive Hex Center Generation for LEO-Viewer.

Generates H3 hexagon centers at adaptive resolutions based on training data density.
Areas with more measurement data get finer (higher resolution) hexagons.

Filters:
- Removes hexes over water (land coverage < 10%)
- Removes hexes in countries where Starlink is not available
  (derived from training data country codes)
- Applies percentile-based adaptive resolution:
  - High density (> P75): subdivide to res 4
  - Medium density (P25-P75): subdivide to res 3
  - Low density (< P25 or no data): keep at res 2
"""

import json
from pathlib import Path

import h3
import numpy as np
import pandas as pd

from . import data_dir, logger

COVERAGE_JSON = data_dir / "h3-country-coverage.json"
TRAIN_DATA_DIR = data_dir / "train-data" / "filtered_percentile_0.75"

MIN_LAND_COVERAGE_PCT = 10.0
RESOLUTIONS = [2, 3, 4]

# ISO 3166-1 alpha-2 to country name mapping (matching coverage JSON names)
COUNTRY_CODE_TO_NAME: dict[str, str] = {
    "AE": "United Arab Emirates", "AG": "Antigua and Barb.", "AL": "Albania",
    "AR": "Argentina", "AS": "American Samoa", "AT": "Austria", "AU": "Australia",
    "BA": "Bosnia and Herz.", "BB": "Barbados", "BD": "Bangladesh", "BE": "Belgium",
    "BF": "Burkina Faso", "BG": "Bulgaria", "BI": "Burundi", "BJ": "Benin",
    "BL": "St-Barth\u00e9lemy", "BR": "Brazil", "BS": "Bahamas", "BT": "Bhutan",
    "BW": "Botswana", "CA": "Canada", "CD": "Dem. Rep. Congo", "CH": "Switzerland",
    "CK": "Cook Is.", "CL": "Chile", "CM": "Cameroon", "CO": "Colombia",
    "CR": "Costa Rica", "CV": "Cabo Verde", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "DM": "Dominica", "DO": "Dominican Rep.",
    "EC": "Ecuador", "EE": "Estonia", "ES": "Spain", "FI": "Finland",
    "FJ": "Fiji", "FM": "Micronesia", "FR": "France", "GB": "United Kingdom",
    "GE": "Georgia", "GF": "Fr. S. Antarctic Lands", "GG": "Guernsey",
    "GH": "Ghana", "GM": "Gambia", "GP": "Guadeloupe", "GR": "Greece",
    "GT": "Guatemala", "GU": "Guam", "GY": "Guyana", "HN": "Honduras",
    "HR": "Croatia", "HT": "Haiti", "HU": "Hungary", "IE": "Ireland",
    "IL": "Israel", "IS": "Iceland", "IT": "Italy", "JM": "Jamaica",
    "JP": "Japan", "KE": "Kenya", "KI": "Kiribati", "KR": "Korea",
    "KZ": "Kazakhstan", "LK": "Sri Lanka", "LR": "Liberia", "LS": "Lesotho",
    "LT": "Lithuania", "LV": "Latvia", "MF": "St-Martin", "MG": "Madagascar",
    "MH": "Marshall Is.", "MM": "Myanmar", "MN": "Mongolia", "MP": "N. Mariana Is.",
    "MQ": "Martinique", "MT": "Malta", "MV": "Maldives", "MW": "Malawi",
    "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique", "NE": "Niger",
    "NG": "Nigeria", "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand",
    "OM": "Oman", "PA": "Panama", "PE": "Peru", "PH": "Philippines",
    "PL": "Poland", "PR": "Puerto Rico", "PT": "Portugal", "PY": "Paraguay",
    "QA": "Qatar", "RE": "R\u00e9union", "RO": "Romania", "RS": "Serbia",
    "RW": "Rwanda", "SB": "Solomon Is.", "SD": "Sudan", "SE": "Sweden",
    "SG": "Singapore", "SI": "Slovenia", "SK": "Slovakia", "SL": "Sierra Leone",
    "SO": "Somalia", "SS": "S. Sudan", "SV": "El Salvador", "SX": "Sint Maarten",
    "SZ": "eSwatini", "TD": "Chad", "TL": "Timor-Leste", "TO": "Tonga",
    "TT": "Trinidad and Tobago", "UA": "Ukraine", "US": "United States",
    "UY": "Uruguay", "VE": "Venezuela", "VI": "U.S. Virgin Is.", "VU": "Vanuatu",
    "WS": "Samoa", "YE": "Yemen", "YT": "Mayotte", "ZA": "South Africa",
    "ZM": "Zambia", "ZW": "Zimbabwe",
}


def load_training_data_locations() -> pd.DataFrame:
    """Load lat/lon and country codes from percentile-filtered training data."""
    csv_files = sorted(TRAIN_DATA_DIR.glob("filtered_download_latency_ms_download_*.csv"))
    if not csv_files:
        logger.warning(f"No training data found in {TRAIN_DATA_DIR}")
        return pd.DataFrame(columns=["lat", "lon", "client_country_code"])

    dfs = []
    for f in csv_files:
        df = pd.read_csv(f, usecols=["lat", "lon", "client_country_code"])
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(combined)} training data points from {len(csv_files)} files")
    return combined


def get_starlink_countries(train_df: pd.DataFrame) -> set[str]:
    """Derive Starlink-available country names (as used in coverage JSON) from training data."""
    codes = set(train_df["client_country_code"].dropna().unique())
    names = set()
    for code in codes:
        name = COUNTRY_CODE_TO_NAME.get(code)
        if name:
            names.add(name)
    logger.info(f"Starlink available in {len(names)} countries (from {len(codes)} codes)")
    return names


def count_points_per_hex(train_df: pd.DataFrame, resolution: int = 2) -> dict[str, int]:
    """Count training data points falling within each H3 hex at given resolution."""
    location_counts = train_df.groupby(["lat", "lon"]).size().reset_index(name="count")

    counts: dict[str, int] = {}
    for _, row in location_counts.iterrows():
        h3_index = h3.latlng_to_cell(row["lat"], row["lon"], resolution)
        counts[h3_index] = counts.get(h3_index, 0) + row["count"]
    return counts


def get_hex_land_coverage(coverage: dict, h3_index: str, resolution: int) -> tuple[float, set[str]]:
    """Get total land coverage percentage and countries for a hex."""
    res_key = str(resolution)
    if res_key not in coverage or h3_index not in coverage[res_key]:
        return 0.0, set()

    country_data = coverage[res_key][h3_index]
    total_coverage = sum(country_data.values())
    countries = set(country_data.keys())
    return total_coverage, countries


def filter_children_by_coverage(
    children: list[str],
    resolution: int,
    coverage: dict,
    starlink_countries: set[str],
) -> list[str]:
    """Filter child hexes for land coverage and Starlink availability."""
    valid = []
    res_key = str(resolution)
    coverage_at_res = coverage.get(res_key, {})

    for child in children:
        if child not in coverage_at_res:
            continue
        country_data = coverage_at_res[child]
        total_coverage = sum(country_data.values())
        if total_coverage < MIN_LAND_COVERAGE_PCT:
            continue
        countries = set(country_data.keys())
        if not countries.intersection(starlink_countries):
            continue
        valid.append(child)
    return valid


def generate_adaptive_hex_centers() -> dict[int, pd.DataFrame]:
    """
    Generate hex centers with adaptive resolution based on data density.

    Returns dict mapping resolution -> DataFrame of hex centers at that resolution.
    """
    logger.info("Loading coverage data...")
    with open(COVERAGE_JSON) as f:
        coverage = json.load(f)

    logger.info("Loading training data for density analysis...")
    train_df = load_training_data_locations()

    if train_df.empty:
        logger.warning("No training data available, falling back to static generation")
        return _fallback_static_generation(coverage)

    starlink_countries = get_starlink_countries(train_df)
    logger.info("Counting data points per res-2 hex...")
    hex_counts = count_points_per_hex(train_df, resolution=2)

    counts_with_data = [c for c in hex_counts.values() if c > 0]
    if counts_with_data:
        p25 = np.percentile(counts_with_data, 25)
        p75 = np.percentile(counts_with_data, 75)
    else:
        p25, p75 = 0, 0

    logger.info(f"Density percentiles - P25: {p25:.0f}, P75: {p75:.0f} points")

    res2_hexes = list(coverage.get("2", {}).keys())
    results: dict[int, list[dict]] = {2: [], 3: [], 4: []}

    for h3_index in res2_hexes:
        total_coverage, countries = get_hex_land_coverage(coverage, h3_index, 2)

        if total_coverage < MIN_LAND_COVERAGE_PCT:
            continue

        if not countries.intersection(starlink_countries):
            continue

        point_count = hex_counts.get(h3_index, 0)

        lat, lon = h3.cell_to_latlng(h3_index)
        results[2].append({
            "h3Index": h3_index,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "parent_data_points": point_count,
        })

        if point_count > p75 and p75 > 0:
            children_3 = list(h3.cell_to_children(h3_index, 3))
            valid_children_3 = filter_children_by_coverage(children_3, 3, coverage, starlink_countries)
            for child in valid_children_3:
                lat, lon = h3.cell_to_latlng(child)
                results[3].append({
                    "h3Index": child,
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "parent_data_points": point_count,
                })
            children_4 = list(h3.cell_to_children(h3_index, 4))
            valid_children_4 = filter_children_by_coverage(children_4, 4, coverage, starlink_countries)
            for child in valid_children_4:
                lat, lon = h3.cell_to_latlng(child)
                results[4].append({
                    "h3Index": child,
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "parent_data_points": point_count,
                })
        elif point_count > p25 and p25 > 0:
            children = list(h3.cell_to_children(h3_index, 3))
            valid_children = filter_children_by_coverage(children, 3, coverage, starlink_countries)
            for child in valid_children:
                lat, lon = h3.cell_to_latlng(child)
                results[3].append({
                    "h3Index": child,
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "parent_data_points": point_count,
                })

    output_dfs: dict[int, pd.DataFrame] = {}
    all_rows = []

    for res in RESOLUTIONS:
        df = pd.DataFrame(results[res])
        if df.empty:
            df = pd.DataFrame(columns=["h3Index", "lat", "lon", "parent_data_points"])

        out_path = data_dir / f"hex_centers_res{res}.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"Resolution {res}: {len(df)} hexes -> {out_path}")
        output_dfs[res] = df

        for _, row in df.iterrows():
            all_rows.append({**row.to_dict(), "resolution": res})

    combined_df = pd.DataFrame(all_rows)
    combined_path = data_dir / "hex_centers_adaptive.csv"
    combined_df.to_csv(combined_path, index=False)
    logger.info(f"Combined adaptive: {len(combined_df)} total hexes -> {combined_path}")

    return output_dfs


def _fallback_static_generation(coverage: dict) -> dict[int, pd.DataFrame]:
    """Fallback: generate all hexes from coverage JSON without adaptive logic."""
    output_dfs: dict[int, pd.DataFrame] = {}
    for res in RESOLUTIONS:
        res_key = str(res)
        if res_key not in coverage:
            continue
        hex_indexes = list(coverage[res_key].keys())
        rows = []
        for h3_index in hex_indexes:
            lat, lon = h3.cell_to_latlng(h3_index)
            rows.append({"h3Index": h3_index, "lat": round(lat, 6), "lon": round(lon, 6)})
        df = pd.DataFrame(rows)
        out_path = data_dir / f"hex_centers_res{res}.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"[fallback] Resolution {res}: {len(df)} hexes -> {out_path}")
        output_dfs[res] = df
    return output_dfs


if __name__ == "__main__":
    generate_adaptive_hex_centers()
