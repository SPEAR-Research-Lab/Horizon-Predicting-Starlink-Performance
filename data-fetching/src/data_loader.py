from datetime import date

from google.cloud import bigquery
from pandas import DataFrame
from psycopg2 import sql
from psycopg2.extensions import connection, cursor
from psycopg2.extras import execute_values

from .config import logger
from .custom_exceptions import InvalidDateError
from .enums import CsvFiles, ExecutionDecision, Tables
from .logger import LogUtils
from .sql.bigquery_queries import (
    get_cf_best_servers_query,
    get_cf_formatted_query,
    get_countries_with_starlink_query,
    get_ndt_best_servers_query,
    get_ndt_formatted_query,
)
from .sql.delete_queries import delete_all_from_table_query
from .sql.select_queries import (
    get_top_asns_query,
    processed_date_select_query,
)
from .table_data import table_data
from .utils import save_dataframe_to_csv

STARLINK_ASN = "14593"


class DataLoader:
    def __init__(self, conn: connection) -> None:
        self._conn = conn
        self._client = bigquery.Client(project="measurement-lab")

    @LogUtils.log_function
    def load_data(
        self, date: date, skip_inserted_dates: bool = False, starlink_only: bool = False
    ) -> ExecutionDecision:
        with self._conn.cursor() as cur:
            if (
                result := self._check_date(cur, date, skip_inserted_dates=skip_inserted_dates)
            ) == ExecutionDecision.SKIP:
                logger.info(f"Skipping data loading for {date.strftime('%Y-%m-%d')} as it has already been processed.")
                return result
            asns = "14593" if starlink_only else self._get_top_asns(cur, includes_starlink=True)
            ndt7_query = get_ndt_formatted_query(date.strftime("%Y-%m-%d"), asns)
            cf_query = get_cf_formatted_query(date.strftime("%Y-%m-%d"), asns)
            self._download_data(cur, ndt7_query, table_data[Tables.NDT7_TEMP]["insert_query"], 'NDT7')
            self._download_data(cur, cf_query, table_data[Tables.CF_TEMP]["insert_query"], 'Cloudflare')
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
            top_asns = self._get_top_asns(cur, includes_starlink=False)

            ndt_terrestrial_query = get_ndt_best_servers_query(
                date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"), top_asns
            )
            ndt_terrestrial_df = self._download_data(
                cur,
                ndt_terrestrial_query,
                table_data[Tables.NDT_BEST_TERRESTRIAL_SERVERS]["insert_query"],
                'NDT7 Best Terrestrial Servers',
            )
            save_dataframe_to_csv(ndt_terrestrial_df, CsvFiles.NDT_BEST_TERRESTRIAL_SERVERS.value, append=True)

            ndt_starlink_query = get_ndt_best_servers_query(
                date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"), STARLINK_ASN
            )
            ndt_starlink_df = self._download_data(
                cur,
                ndt_starlink_query,
                table_data[Tables.NDT_BEST_STARLINK_SERVERS]["insert_query"],
                'NDT7 Best Starlink Servers',
            )
            save_dataframe_to_csv(ndt_starlink_df, CsvFiles.NDT_BEST_STARLINK_SERVERS.value, append=True)

            cf_terrestrial_query = get_cf_best_servers_query(
                date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"), top_asns
            )
            cf_terrestrial_df = self._download_data(
                cur,
                cf_terrestrial_query,
                table_data[Tables.CF_BEST_TERRESTRIAL_SERVERS]["insert_query"],
                'Cloudflare Best Terrestrial Servers',
            )
            save_dataframe_to_csv(cf_terrestrial_df, CsvFiles.CF_BEST_TERRESTRIAL_SERVERS.value, append=True)

            cf_starlink_query = get_cf_best_servers_query(
                date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"), STARLINK_ASN
            )
            cf_starlink_df = self._download_data(
                cur,
                cf_starlink_query,
                table_data[Tables.CF_BEST_STARLINK_SERVERS]["insert_query"],
                'Cloudflare Best Starlink Servers',
            )
            save_dataframe_to_csv(cf_starlink_df, CsvFiles.CF_BEST_STARLINK_SERVERS.value, append=True)

            self._conn.commit()

    @LogUtils.log_function
    def update_countries_with_starlink(self, date_from: date, date_to: date) -> None:
        with self._conn.cursor() as cur:
            delete_query = delete_all_from_table_query(Tables.COUNTRIES_WITH_STARLINK_MEASUREMENTS.value)
            cur.execute(delete_query)
            logger.info("Deleted all rows from Countries with Starlink Measurements table.")
            download_query = get_countries_with_starlink_query(
                date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")
            )
            df = self._download_data(
                cur,
                download_query,
                table_data[Tables.COUNTRIES_WITH_STARLINK_MEASUREMENTS]["insert_query"],
                'Countries with Starlink Measurements',
            )
            save_dataframe_to_csv(df, CsvFiles.COUNTRIES_WITH_STARLINK_MEASUREMENTS.value)
            self._conn.commit()

    def _check_date(self, cur: cursor, date_to_process: date, skip_inserted_dates: bool = False) -> ExecutionDecision:
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
        df.replace('', None, inplace=True)
        df = df.astype(object).where(df.notnull(), None)
        data_tuples = [tuple(x) for x in df.to_records(index=False)]
        execute_values(cur, insert_query, data_tuples)
        logger.info(f"Inserted {len(data_tuples)} rows into the database from {dataset_name}.")
        return df

    def _get_top_asns(self, cur: cursor, includes_starlink: bool) -> str:
        query = get_top_asns_query(includes_starlink=includes_starlink)
        cur.execute(query)
        row = cur.fetchone()
        if not row:
            logger.warning("No ISPs found in the database. Using default ISPs.")
            return "14593"
        isps_str: str = row[0]
        return isps_str
