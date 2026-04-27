from datetime import date, datetime, timedelta, timezone
from enum import Enum

import pandas as pd

from big_query_data_manager import BigQueryDataManager
from config import columns, data_dir, logger
from data_processer import DataProcesser
from data_updater import DataUpdater
from enums import CsvFiles
from logger import LogUtils
from utils import delete_files, save_dataframe_to_csv


class DataSource(Enum):
    NDT7 = "NDT7"
    CF = "Cloudflare AIM"


def _get_process_date_range(period_days: int) -> tuple[date, date]:
    """Returns a tuple of (start_date, end_date) where end_date is yesterday's date and start_date is period_days before end_date."""
    end_date = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
    start_date = end_date - timedelta(days=period_days)
    return start_date, end_date


def _prepare_cf_with_airport_data(cf_df: pd.DataFrame) -> pd.DataFrame:
    airport_codes_df = pd.read_csv(data_dir / CsvFiles.AIRPORT_CODES.value)

    cf_merged = cf_df.merge(airport_codes_df, left_on='server_airport_code', right_on='iata_code', how='left')

    cf_merged['server_city'] = cf_merged['municipality']
    cf_merged['server_country_code'] = cf_merged['iso_country']
    cf_merged = cf_merged.drop(columns=['iso_country', 'municipality', 'iata_code'], errors='ignore')

    return cf_merged


def _merge_measurements(ndt_df: pd.DataFrame, cf_df: pd.DataFrame) -> pd.DataFrame:
    ndt_df['data_source'] = DataSource.NDT7.value
    cf_df['data_source'] = DataSource.CF.value

    assert set(columns).issubset(set(ndt_df.columns)), "NDT DataFrame is missing required columns"
    assert set(columns).issubset(set(cf_df.columns)), "CF DataFrame is missing required columns"
    return pd.concat([ndt_df[columns], cf_df[columns]], ignore_index=True)


@LogUtils.log_function
def main() -> None:
    try:
        DataUpdater.maybe_update_data()

        big_query_data_manager = BigQueryDataManager()
        big_query_data_manager.get_best_servers(*_get_process_date_range(30))

        start_date, end_date = _get_process_date_range(7)
        ndt_df, cf_df = big_query_data_manager.get_measurements(start_date, end_date)

        data_processer = DataProcesser()
        ndt_df, cf_df = data_processer.process_data(ndt_df, cf_df)

        cf_df = _prepare_cf_with_airport_data(cf_df)
        merged_df = _merge_measurements(ndt_df, cf_df)

        merged_file_name = f"measurements_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.csv"
        save_dataframe_to_csv(merged_df, merged_file_name)
        logger.info(f"Saved merged measurements to {merged_file_name}")

        delete_files([CsvFiles.NDT_BEST_STARLINK_SERVERS.value, CsvFiles.CF_BEST_STARLINK_SERVERS.value])
    except Exception as e:
        logger.error(f"Application failed: {e}")
        return

    logger.info("Application exited successfully.")


if __name__ == "__main__":
    main()
