from typing import Optional

import pandas as pd
from constants import data_dir, feature_to_units, output_dir
from weather_utils import get_and_maybe_fetch_openmeteo_data, mae, rmse

knmi_to_open_meteo_names = {
    "cloud_cover_octa": "cloud_cover",
    "wind_speed": "wind_speed_10m",
    "precipitation_total": "precipitation",
    "temperature": "temperature_2m",
}
openmeteo_to_knmi_names = {v: k for k, v in knmi_to_open_meteo_names.items()}


def ensure_hour_in_df(df: pd.DataFrame) -> pd.DataFrame:
    s = df["time"].astype(str).copy()
    mask = ~s.str.contains(":")
    if mask.any():
        s.loc[mask] = s.loc[mask] + " 00:00:00"
    df["time"] = pd.to_datetime(s, utc=True)
    return df


def cross_validate_location(
    lat: float, lon: float, loc_df: pd.DataFrame, start_date, end_date
) -> Optional[dict]:
    station_name = str(loc_df["stationname"].dropna().iloc[0])
    om_df = get_and_maybe_fetch_openmeteo_data(lat, lon, start_date, end_date)
    merged = pd.merge(loc_df, om_df, left_on="time", right_on="datetime", how="inner")
    if merged.empty:
        print(f"  [WARN] No overlapping timestamps for {station_name}")
        return None

    metrics = {}

    for feat in feature_to_units.keys():
        knmi_col = next(
            (k for k, v in knmi_to_open_meteo_names.items() if v == feat), None
        )
        if knmi_col is None:
            continue

        knmi_name, om_name = openmeteo_to_knmi_names.get(feat), feat
        if knmi_name is None or om_name is None:
            raise RuntimeError(
                f"Could not find columns for feature {feat} in merged data for {station_name}"
            )

        a = pd.to_numeric(merged[knmi_name], errors="coerce").values
        b = pd.to_numeric(merged[om_name], errors="coerce").values
        if len(a) == 0 or len(b) == 0:
            continue
        mae_val = mae(a, b)
        rmse_val = rmse(a, b)
        metrics[feat] = {"MAE": float(mae_val), "RMSE": float(rmse_val)}
        print(f"  {feat}: MAE={mae_val:.3f}, RMSE={rmse_val:.3f}")

    output_path = output_dir / f"{station_name}_validation.csv"
    merged.to_csv(output_path, index=False)
    print(f"  Saved merged data to {output_path}")

    return {
        "station": station_name,
        "lat": lat,
        "lon": lon,
        "metrics": metrics,
        "merged_df": merged,
    }


def main() -> None:
    df = pd.read_csv(data_dir / "netherlands.csv")
    df_filtered = df.dropna(subset=list(knmi_to_open_meteo_names.keys()))
    df_filtered = ensure_hour_in_df(df_filtered)

    times_dt = df_filtered["time"]
    start_time = (times_dt.min() - pd.Timedelta(hours=1)).date()
    end_time = (times_dt.max() + pd.Timedelta(hours=1)).date()

    locations = df_filtered[["lat", "lon"]].drop_duplicates().reset_index(drop=True)

    results = []
    summary = []
    for lat, lon in locations[["lat", "lon"]].itertuples(index=False):
        loc_df = df_filtered[
            (df_filtered["lat"] == lat) & (df_filtered["lon"] == lon)
        ].copy()
        res = cross_validate_location(lat, lon, loc_df, start_time, end_time)
        results.append(res)
        if res is not None:
            summary.append(
                {
                    "station": res["station"],
                    "lat": lat,
                    "lon": lon,
                    "metrics": res["metrics"],
                }
            )

    summary_df = pd.DataFrame(summary)
    summary_df.to_json(
        output_dir / "netherlands_validation_summary.json", orient="records", indent=4
    )
    print(f"Saved summary to {output_dir / 'netherlands_validation_summary.json'}")


if __name__ == "__main__":
    main()
