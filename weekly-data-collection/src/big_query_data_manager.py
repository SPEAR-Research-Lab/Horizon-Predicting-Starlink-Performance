from datetime import date

from google.cloud import bigquery
from pandas import DataFrame

from bigquery_queries import (
    get_cf_best_servers_query,
    get_cf_formatted_query,
    get_ndt_best_servers_query,
    get_ndt_formatted_query,
)
from config import logger
from enums import CsvFiles
from logger import LogUtils
from utils import save_dataframe_to_csv


class BigQueryDataManager:
    def __init__(self) -> None:
        self._client = bigquery.Client(project="measurement-lab")

    @LogUtils.log_function
    def get_measurements(self, start_date: date, end_date: date) -> tuple[DataFrame, DataFrame]:
        ndt_query = get_ndt_formatted_query(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        ndt_df = self._download_data(ndt_query)

        cf_query = get_cf_formatted_query(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        cf_df = self._download_data(cf_query)
        return ndt_df, cf_df

    @LogUtils.log_function
    def get_best_servers(self, start_date: date, end_date: date) -> None:
        ndt_query = get_ndt_best_servers_query(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        ndt_df = self._download_data(ndt_query)
        save_dataframe_to_csv(ndt_df, CsvFiles.NDT_BEST_STARLINK_SERVERS.value)

        cf_query = get_cf_best_servers_query(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        cf_df = self._download_data(cf_query)
        save_dataframe_to_csv(cf_df, CsvFiles.CF_BEST_STARLINK_SERVERS.value)

    def _download_data(self, download_query: str) -> DataFrame:
        df: DataFrame = self._client.query(download_query).to_dataframe()
        logger.info(f"Downloaded {len(df)} rows from BigQuery.")
        df.replace("", None, inplace=True)
        df = df.astype(object).where(df.notnull(), None)
        return df
