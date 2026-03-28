from datetime import date

from google.cloud import bigquery
from pandas import DataFrame
from psycopg2 import sql
from psycopg2.extensions import connection, cursor
from psycopg2.extras import execute_values

from .config import logger, output_dir
from .custom_exceptions import InvalidDateError
from .enums import CsvFiles, ExecutionDecision, Tables
from .logger import LogUtils
from .sql.bigquery_queries import (
    get_cf_best_servers_query,
    get_cf_formatted_query,
    get_ndt_best_servers_query,
    get_ndt_formatted_query,
)
from .sql.select_queries import (
    get_select_monthly_data_query,
    processed_date_select_query,
)
from .table_data import table_data
from .utils import export_data, save_dataframe_to_csv


class DataLoader:
    def __init__(self, conn: connection) -> None:
        self._conn = conn
        self._client = bigquery.Client(project="measurement-lab")

    @LogUtils.log_function
    def load_data(self, date: date, skip_inserted_dates: bool = True) -> ExecutionDecision:
        with self._conn.cursor() as cur:
            if (
                result := self._check_date(cur, date, skip_inserted_dates=skip_inserted_dates)
            ) == ExecutionDecision.SKIP:
                logger.info(f"Skipping data loading for {date.strftime('%Y-%m-%d')} as it has already been processed.")
                return result
            ndt7_query = get_ndt_formatted_query(date.strftime("%Y-%m-%d"))
            cf_query = get_cf_formatted_query(date.strftime("%Y-%m-%d"))
            self._download_data(cur, ndt7_query, table_data[Tables.NDT7_TEMP]["insert_query"], "NDT7")
            self._download_data(cur, cf_query, table_data[Tables.CF_TEMP]["insert_query"], "Cloudflare")
            self._insert_processed_date(cur, date)
            self._conn.commit()
        return ExecutionDecision.OK

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
    def export_monthly(self, month: int, year: int) -> None:
        with self._conn.cursor() as cur:
            query = get_select_monthly_data_query(month, year)
            file_name = f"download_{year}_{month}.csv"
            export_data(cur, query, output_dir, file_name)

    def _check_date(self, cur: cursor, date_to_process: date, skip_inserted_dates: bool) -> ExecutionDecision:
        cur.execute(processed_date_select_query, (date_to_process.strftime("%Y-%m-%d"),))
        if cur.fetchone():
            if not skip_inserted_dates:
                raise InvalidDateError(
                    f"Data for {date_to_process} has already been processed. Please choose a different date."
                )
            logger.warning(f"Data for {date_to_process} has already been processed. Continuing without inserting.")
            return ExecutionDecision.SKIP
        logger.info(f"Date {date_to_process.strftime('%Y-%m-%d')} is valid for processing.")
        return ExecutionDecision.OK

    def _insert_processed_date(self, cur: cursor, date_to_process: date) -> None:
        data_tuples = [(date_to_process.strftime("%Y-%m-%d"),)]
        execute_values(cur, table_data[Tables.PROCESSED_DATES]["insert_query"], data_tuples)
        logger.info(f"Inserted processed date: {date_to_process.strftime('%Y-%m-%d')} into the database.")

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
