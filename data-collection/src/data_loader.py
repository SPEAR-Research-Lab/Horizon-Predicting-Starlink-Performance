from datetime import date
from typing import List, Optional

from google.cloud import bigquery
from pandas import DataFrame
from psycopg2 import sql
from psycopg2.extensions import connection, cursor
from psycopg2.extras import execute_values

from .config import logger, output_dir
from .data_classes import LoadDataConfig
from .enums import CsvFiles, Tables
from .logger import LogUtils
from .sql.bigquery_queries import (
    get_cf_best_servers_query,
    get_ndt_best_servers_query,
)
from .sql.select_queries import get_select_monthly_data_query
from .table_data import table_data
from .utils import export_data, save_dataframe_to_csv


class DataLoader:
    def __init__(self, conn: connection) -> None:
        self._conn = conn
        self._client = bigquery.Client(project="measurement-lab")

    @LogUtils.log_function
    def load_data(self, start_date: date, end_date: date, config: List[LoadDataConfig]) -> None:
        with self._conn.cursor() as cur:
            for load_config in config:
                query = load_config.get_query(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                self._download_data(cur, query, table_data[load_config.table]["insert_query"], load_config.dataset_name)
            self._conn.commit()

    @LogUtils.log_function
    def update_best_servers(self, date_from: date, date_to: date) -> None:
        """
        Update best servers for the given date range.

        @param date_from: is the first day of a month
        @param date_to: is the last day of the month.
        """
        with self._conn.cursor() as cur:
            ndt_starlink_query = get_ndt_best_servers_query(
                date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")
            )
            ndt_starlink_df = self._download_data(
                cur,
                ndt_starlink_query,
                table_data[Tables.NDT_BEST_STARLINK_SERVERS]["insert_query"],
                "NDT7 Best Starlink Servers",
            )
            save_dataframe_to_csv(ndt_starlink_df, CsvFiles.NDT_BEST_STARLINK_SERVERS.value, append=True)

            cf_starlink_query = get_cf_best_servers_query(date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))
            cf_starlink_df = self._download_data(
                cur,
                cf_starlink_query,
                table_data[Tables.CF_BEST_STARLINK_SERVERS]["insert_query"],
                "Cloudflare Best Starlink Servers",
            )
            save_dataframe_to_csv(cf_starlink_df, CsvFiles.CF_BEST_STARLINK_SERVERS.value, append=True)

            self._conn.commit()

    @LogUtils.log_function
    def export_monthly(self, month: int, year: int, only_download: bool, file: Optional[str] = None) -> None:
        with self._conn.cursor() as cur:
            query = get_select_monthly_data_query(month, year, only_download)
            file_name = file if file else f"download_{year}_{month}.csv"
            export_data(cur, query, output_dir, file_name)

    def _download_data(
        self,
        cur: cursor,
        download_query: str,
        insert_query: sql.SQL,
        dataset_name: str,
    ) -> DataFrame:
        df: DataFrame = self._client.query(download_query).to_dataframe()
        logger.info(f"Downloaded {len(df)} rows from BigQuery from {dataset_name}.")
        df.replace("", None, inplace=True)
        df = df.astype(object).where(df.notnull(), None)
        data_tuples = [tuple(x) for x in df.to_records(index=False)]
        execute_values(cur, insert_query, data_tuples)
        logger.info(f"Inserted {len(data_tuples)} rows into the database from {dataset_name}.")
        return df
