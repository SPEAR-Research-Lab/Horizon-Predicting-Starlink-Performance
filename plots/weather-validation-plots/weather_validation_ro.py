from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import pytz

from constants import BANEASA_RO, PITESTI_RO, data_dir, feature_to_units, output_dir
from weather_utils import get_and_maybe_fetch_openmeteo_data, mae, rmse

STATIONS = [
    ("Baneasa", BANEASA_RO[0], BANEASA_RO[1], data_dir / "Baneasa_01.09.2025.xlsx"),
    ("Pitesti", PITESTI_RO[0], PITESTI_RO[1], data_dir / "Pitesti_01.09.2025.xlsx"),
]


def load_station_data(filepath, station_name) -> pd.DataFrame:
    df = pd.read_excel(filepath)

    processed_rows = []

    for _, row in df.iterrows():
        try:
            ora_locala = row["Oră locală"]
            if hasattr(ora_locala, "hour"):
                hour = ora_locala.hour
            else:
                # Try to parse as string if it's not a time object
                ora_str = str(ora_locala).strip()
                if ":" in ora_str:
                    hour = int(ora_str.split(":")[0])
                elif "-" in ora_str:
                    hour = int(ora_str.split("-")[0])
                else:
                    continue

            day = int(row["Zi"])
            month = int(row["Lună"])
            year = int(row["An"])

            romania_tz = pytz.timezone("Europe/Bucharest")
            dt_local = romania_tz.localize(datetime(year, month, day, hour, 0, 0))
            dt_utc = dt_local.astimezone(pytz.UTC)

            precip = float(row["Cantitatea de precipitații (mm)"])

            cloud_str = str(row["Nebulozitetea totala"]).strip()
            if cloud_str == "/" or cloud_str == "":
                cloud_cover = np.nan
            else:
                try:
                    cloud_cover = float(cloud_str) * 10  # 5 -> 50%
                except:
                    cloud_cover = np.nan

            temp = float(row["Temperatura aerului (°C)"])
            wind = float(row["Viteza vântului (m/s)"])

            processed_rows.append(
                {
                    "datetime": dt_utc,
                    "hour": hour,
                    "temperature_2m": temp,
                    "precipitation": precip,
                    "wind_speed_10m": wind,
                    "cloud_cover": cloud_cover,
                }
            )
        except Exception as e:
            print(f"[WARN] Skipping row in {station_name}: {e}")
            continue

    result_df = pd.DataFrame(processed_rows)
    if not result_df.empty:
        result_df["datetime"] = pd.to_datetime(result_df["datetime"])

    return result_df


def cross_validate_station(station_name, lat, lon, excel_path) -> Optional[dict]:
    print(f"\n=== {station_name} ===")
    station_df = load_station_data(excel_path, station_name)
    print(f"Station data loaded: {len(station_df)} records")

    min_date = station_df["datetime"].min().date() - timedelta(days=1)
    max_date = station_df["datetime"].max().date() + timedelta(days=1)
    om_df = get_and_maybe_fetch_openmeteo_data(lat, lon, min_date, max_date)
    print(f"Open-Meteo data loaded: {len(om_df)} records")

    # Merge on exact datetime (both are now in UTC)
    merged = pd.merge(
        station_df, om_df, on="datetime", suffixes=("_station", "_openmeteo")
    )

    print(f"Merged records: {len(merged)}")
    print(f"Date range (UTC): {merged['datetime'].min()} to {merged['datetime'].max()}")

    if merged.empty:
        print(f"[ERROR] No overlapping data for {station_name}")
        return None

    # Calculate metrics
    metrics = {}
    for feat in feature_to_y_label.keys():
        station_col = f"{feat}_station"
        om_col = f"{feat}_openmeteo"

        if station_col in merged.columns and om_col in merged.columns:
            mae_val = mae(merged[station_col].values, merged[om_col].values)
            rmse_val = rmse(merged[station_col].values, merged[om_col].values)

            metrics[feat] = {"MAE": mae_val, "RMSE": rmse_val}

            print(f"{feat}: MAE={mae_val:.3f}, RMSE={rmse_val:.3f}")

    output_path = output_dir / f"{station_name}_validation.csv"
    merged.to_csv(output_path, index=False)
    print(f"Saved merged data to {output_path}")

    return {
        "station": station_name,
        "lat": lat,
        "lon": lon,
        "metrics": metrics,
        "merged_df": merged,
    }


def main() -> None:
    results = []
    summary = []

    for station_name, lat, lon, excel_path in STATIONS:
        result = cross_validate_station(station_name, lat, lon, excel_path)
        results.append(result)

        if result:
            summary.append(
                {
                    "station": station_name,
                    "lat": lat,
                    "lon": lon,
                    "metrics": result["metrics"],
                }
            )

    summary_df = pd.DataFrame(summary)
    summary_df.to_json(
        output_dir / "romania_validation_summary.json", orient="records", indent=4
    )
    print("\n==== VALIDATION COMPLETE ====")


if __name__ == "__main__":
    main()
