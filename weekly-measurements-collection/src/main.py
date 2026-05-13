from datetime import date, datetime, timedelta, timezone

import pandas as pd

from big_query_data_manager import BigQueryDataManager
from config import CsvFiles, columns, data_dir, logger, measurements_dir, predictions_dir
from data_enricher import DataEnricher
from data_processer import DataProcesser
from data_updater import DataUpdater
from filter_anomalies import filter_df
from inter_city_distance_calculator import DistanceCalculator
from logger import LogUtils
from meteo_data_handler import WeatherDataHandler
from open_meteo_fetcher import OpenMeteoFetcher
from utils import delete_files, save_dataframe_to_csv

distance_calculator = DistanceCalculator()
weather_data_handler = WeatherDataHandler()
open_meteo_fetcher = OpenMeteoFetcher(distance_calculator=distance_calculator)
data_enricher = DataEnricher(distance_calculator=distance_calculator, weather_data_handler=weather_data_handler)


def _get_process_date_range(ref_date: date, period_days: int) -> tuple[date, date]:
    """Returns a tuple of (start_date, end_date) where end_date is one day before ref_date and start_date is period_days before end_date."""
    end_date = ref_date - timedelta(days=1)
    start_date = end_date - timedelta(days=period_days)
    return start_date, end_date


def _prepare_cf_with_airport_data(cf_df: pd.DataFrame) -> pd.DataFrame:
    airport_codes_df = pd.read_csv(data_dir / CsvFiles.airport_codes)

    cf_merged = cf_df.merge(
        airport_codes_df,
        left_on="server_airport_code",
        right_on="iata_code",
        how="left",
    )

    cf_merged["server_city"] = cf_merged["municipality"]
    cf_merged["server_country_code"] = cf_merged["iso_country"]
    cf_merged = cf_merged.drop(columns=["iso_country", "municipality", "iata_code"], errors="ignore")

    return cf_merged


def _merge_measurements(ndt_df: pd.DataFrame, cf_df: pd.DataFrame) -> pd.DataFrame:
    ndt_df["data_source"] = "NDT7"
    cf_df["data_source"] = "Cloudflare AIM"

    assert set(columns).issubset(set(ndt_df.columns)), "NDT DataFrame is missing required columns"
    assert set(columns).issubset(set(cf_df.columns)), "CF DataFrame is missing required columns"
    return pd.concat([ndt_df[columns], cf_df[columns]], ignore_index=True)


def _get_file_names(start_date: date, end_date: date) -> tuple[str, str]:
    latency_file_name = f"download_latency_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.csv"
    throughput_file_name = f"download_throughput_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.csv"
    return latency_file_name, throughput_file_name


def _maybe_delete_old_measurements(max_files: int = 52) -> None:
    files = list(measurements_dir.iterdir())
    if len(files) <= max_files:
        return
    files.sort(
        key=lambda f: datetime.strptime(f.name.split("_")[2], "%Y-%m-%d"),
        reverse=True,
    )
    for f in files[max_files:]:
        f.unlink()


def clean_up() -> None:
    distance_calculator.update_unresolved_cities()
    _maybe_delete_old_measurements()
    delete_files(
        [
            CsvFiles.ndt_best_starlink_servers,
            CsvFiles.cf_best_starlink_servers,
        ]
    )


def _update_city_country_set(
    df: pd.DataFrame,
    city_country_set: set[tuple[str, str]],
) -> None:
    city_country_set.update(
        (city, country)
        for city, country in zip(df["client_city"], df["client_country_code"])
        if pd.notna(city) and pd.notna(country)
    )


def _update_servers_df(df: pd.DataFrame) -> None:
    servers_df = pd.read_csv(data_dir / CsvFiles.server_locations)
    combined = pd.concat(
        [
            servers_df[["server_city", "server_country_code"]],
            df[["server_city", "server_country_code"]],
        ],
        ignore_index=True,
    ).dropna()
    combined = combined.drop_duplicates().reset_index(drop=True)
    combined.to_csv(data_dir / CsvFiles.server_locations, index=False)
    logger.info(f"Updated server locations with {len(combined) - len(servers_df)} unique entries.")


def _fetch_weather_data(merged_df: pd.DataFrame, start_date: date, today_date: date) -> None:
    city_country_set: set[tuple[str, str]] = set()
    _update_city_country_set(merged_df, city_country_set)
    prev_latency_file_name, prev_throughput_file_name = _get_file_names(*_get_process_date_range(start_date, 6))
    prev_latency_path = measurements_dir / prev_latency_file_name
    prev_throughput_path = measurements_dir / prev_throughput_file_name
    prev_latency_df = None
    prev_throughput_df = None
    if prev_latency_path.exists():
        prev_latency_df = pd.read_csv(str(prev_latency_path))
        _update_city_country_set(prev_latency_df, city_country_set)
    if prev_throughput_path.exists():
        prev_throughput_df = pd.read_csv(str(prev_throughput_path))
        _update_city_country_set(prev_throughput_df, city_country_set)
    if prev_latency_df is not None:
        prev_latency_df = data_enricher.enrich_df_with_weather(prev_latency_df, 'client_city', 'client_country_code')
        prev_latency_df.to_csv(index=False)
    if prev_throughput_df is not None:
        prev_throughput_df = data_enricher.enrich_df_with_weather(
            prev_throughput_df, 'client_city', 'client_country_code'
        )
        prev_throughput_df.to_csv(index=False)
    open_meteo_fetcher.fetch_weather_for_cities(
        city_country_set, ref_date=today_date, historical_days=15, forecast_days=0
    )


def _prepare_prediction_data(today_date: date, input_csv: str, output_csv: str) -> None:
    df = pd.read_csv(data_dir / input_csv)
    open_meteo_fetcher.fetch_weather_for_locations(
        locations=df[["lat", "lon"]].values.tolist(),
        ref_date=today_date,
        historical_days=None,
        forecast_days=15,
    )
    df = data_enricher.generate_df_for_prediction(df, start_date=today_date, days=14)
    df.to_csv(predictions_dir / output_csv, index=False)


@LogUtils.log_function
def main() -> None:
    try:
        DataUpdater.maybe_update_data()
        today_date = datetime.now(tz=timezone.utc).date()

        big_query_data_manager = BigQueryDataManager()
        big_query_data_manager.get_best_servers(*_get_process_date_range(today_date, 30))

        start_date, end_date = _get_process_date_range(today_date, 6)
        logger.info(f"Processing measurements from {start_date} to {end_date}...")
        ndt_df, cf_df = big_query_data_manager.get_measurements(start_date, end_date)

        data_processer = DataProcesser()
        ndt_df, cf_df = data_processer.process_data(ndt_df, cf_df)

        cf_df = _prepare_cf_with_airport_data(cf_df)
        merged_df = _merge_measurements(ndt_df, cf_df)

        _update_servers_df(merged_df)
        _fetch_weather_data(merged_df, start_date, today_date)
        enriched_df = data_enricher.enrich_dataframe_for_training(merged_df)

        filtered_latency_df, filtered_throughput_df = filter_df(enriched_df)

        latency_file_name, throughput_file_name = _get_file_names(start_date, end_date)
        save_dataframe_to_csv(filtered_latency_df, latency_file_name, measurements_dir)
        save_dataframe_to_csv(filtered_throughput_df, throughput_file_name, measurements_dir)

        clean_up()
        logger.info("Data processing complete.")

        _prepare_prediction_data(today_date, CsvFiles.prediction_points, CsvFiles.prediction_points_features)
        logger.info("City data preparation complete.")
        _prepare_prediction_data(today_date, CsvFiles.hexagon_centers, CsvFiles.hexagon_centers_features)
        logger.info("Hexagon data preparation complete.")
    except Exception:
        logger.exception("Application failed")
        exit(1)

    logger.info("Application exited successfully.")


if __name__ == "__main__":
    main()
