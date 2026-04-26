import datetime
import time
from pathlib import Path

import pandas as pd
import requests

from .__init__ import data_dir, logger

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = "temperature_2m,precipitation,cloud_cover,wind_speed_10m"


def fetch_open_meteo_forecast(lat: float, lon: float, forecast_days: int = 3) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": HOURLY_VARS,
        "forecast_days": forecast_days,
        "timezone": "UTC",
    }
    resp = requests.get(OPEN_METEO_URL, params=params)
    resp.raise_for_status()
    data = resp.json()

    hourly = data["hourly"]
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(hourly["time"]),
            "temperature_2m": hourly["temperature_2m"],
            "precipitation": hourly["precipitation"],
            "cloud_cover": hourly["cloud_cover"],
            "wind_speed_10m": hourly["wind_speed_10m"],
        }
    )
    df["Date"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df["Hour"] = df["datetime"].dt.hour
    return df.drop(columns=["datetime"])


def enrich_weather(input_csv: Path, output_csv: Path, forecast_days: int = 3) -> None:
    df = pd.read_csv(input_csv)
    lat_col = "lat" if "lat" in df.columns else "Latitude"
    lon_col = "lon" if "lon" in df.columns else "Longitude"

    extra_cols = [c for c in df.columns if c not in (lat_col, lon_col)]
    unique_locations = df[[lat_col, lon_col]].drop_duplicates()

    results = []
    for _, loc in unique_locations.iterrows():
        lat, lon = loc[lat_col], loc[lon_col]
        try:
            weather_df = fetch_open_meteo_forecast(lat, lon, forecast_days)
            extras = df[(df[lat_col] == lat) & (df[lon_col] == lon)][extra_cols].iloc[0].to_dict() if extra_cols else {}
            for _, w_row in weather_df.iterrows():
                row = {lat_col: lat, lon_col: lon, **extras, **w_row.to_dict()}
                results.append(row)
            time.sleep(0.25)
        except Exception as e:
            logger.error(f"Weather fetch error for ({lat}, {lon}): {e}")

    out_df = pd.DataFrame(results)
    out_df.to_csv(output_csv, index=False)
    logger.info(f"Wrote {len(out_df)} rows to {output_csv}")


INPUT_FILES = [
    "hex_centers_res2.csv",
    "hex_centers_res3.csv",
    "hex_centers_res4.csv",
]


if __name__ == "__main__":
    for fname in INPUT_FILES:
        inpath = data_dir / fname
        if inpath.exists():
            outpath = data_dir / fname.replace(".csv", "_weather.csv")
            logger.info(f"Enriching {inpath} -> {outpath}")
            enrich_weather(inpath, outpath)
        else:
            logger.warning(f"Skipping {inpath} (not found)")
