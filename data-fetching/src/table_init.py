import gc
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from psycopg2 import sql
from psycopg2.extensions import connection, cursor
from psycopg2.extras import execute_values

from .caida_api_queries import fetch_asn_data
from .config import data_dir, logger
from .enums import CsvFiles, ExecutionDecision, Tables
from .logger import LogUtils
from .sql.delete_queries import delete_all_from_table_query
from .sql.drop_queries import drop_tables_query
from .sql.select_queries import get_check_table_exists_query
from .table_data import CleanDataframeFn, table_data
from .utils import delete_files, download_file, generate_cities_csv


class TableInitializer:
    def __init__(self, conn: connection) -> None:
        self._conn = conn

    @LogUtils.log_function
    def initialize_tables(self) -> None:
        with self._conn.cursor() as cur:
            for table, data in table_data.items():
                if self._table_exists(cur, table):
                    logger.info(f"Table {table.value} already exists. Skipping creation.")
                    continue
                cur.execute(data['create_query'])
                logger.info(f"Created table {table.value}.")
                if csv_name := data['csv_name']:
                    self._process_and_insert_data(
                        cur,
                        data['insert_query'],
                        data['post_insert_query'],
                        csv_name,
                        data['cleaning_fn'],
                    )
            self._conn.commit()

    def _table_exists(self, cur: cursor, table_name: Tables) -> bool:
        cur.execute(get_check_table_exists_query(table_name.value))
        result = cur.fetchone()
        return result is not None and result[0] is not None and bool(result[0])

    @LogUtils.log_function
    def update_asns(self) -> None:
        fetch_asn_data(CsvFiles.ASNS.value)
        with self._conn.cursor() as cur:
            self._clean_and_insert_data(cur, Tables.AS_STATISTICS)

    @LogUtils.log_function
    def update_airport_codes(self) -> None:
        download_file('https://datahub.io/core/airport-codes/_r/-/data/airport-codes.csv', CsvFiles.AIRPORT_CODES.value)
        with self._conn.cursor() as cur:
            self._clean_and_insert_data(cur, Tables.AIRPORT_CODES)

    @LogUtils.log_function
    def update_cities(self) -> None:
        download_file('https://download.geonames.org/export/dump/cities15000.zip', 'cities.txt', unzip=True)
        download_file('https://download.geonames.org/export/dump/admin1CodesASCII.txt', 'regions.txt')
        generate_cities_csv('cities.txt', 'regions.txt', CsvFiles.CITIES.value)
        delete_files(['cities.txt', 'regions.txt'])
        with self._conn.cursor() as cur:
            self._clean_and_insert_data(cur, Tables.CITIES)

    def _clean_and_insert_data(self, cur: cursor, table: Tables) -> None:
        delete_query = delete_all_from_table_query(table.value)
        cur.execute(delete_query)
        logger.info(f"Deleted all rows from {table.value} table.")
        assert (
            csv_name := table_data[table]["csv_name"]
        ) is not None, f"CSV name for table {table.value} is not defined."
        self._process_and_insert_data(
            cur,
            table_data[table]["insert_query"],
            table_data[table]["post_insert_query"],
            csv_name,
            table_data[table]["cleaning_fn"],
        )

    def _process_and_insert_data(
        self,
        cur: cursor,
        insert_query: sql.SQL,
        post_insert_query: Optional[sql.SQL],
        csv_file_name: str,
        clean_dataframe: Optional[CleanDataframeFn],
    ) -> None:
        csv_file_path = data_dir / csv_file_name
        insert_result = self._insert_data_from_csv(cur, csv_file_path, insert_query, clean_dataframe)
        if insert_result == ExecutionDecision.OK and post_insert_query:
            cur.execute(post_insert_query)
            logger.info(f"Executed post-insert query for {csv_file_name}")

    @LogUtils.log_function
    def drop_tables(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(drop_tables_query)
            self._conn.commit()

    def _insert_data_from_csv(
        self,
        cur: cursor,
        csv_file_path: Path,
        insert_query: sql.SQL,
        clean_dataframe: Callable[[pd.DataFrame], None] | None = None,
    ) -> ExecutionDecision:
        df = None
        try:
            if not csv_file_path.exists():
                logger.warning(f"CSV file {csv_file_path} does not exist. Skipping data insertion.")
                return ExecutionDecision.SKIP
            df = pd.read_csv(csv_file_path, dtype=str, na_values=[""], keep_default_na=False)
            df = df.where(pd.notnull(df), None)
            if clean_dataframe:
                clean_dataframe(df)
            data_tuples = [tuple(x) for x in df.to_records(index=False)]
            execute_values(cur, insert_query, data_tuples)
            logger.info(f"Inserted {len(data_tuples)} rows into the database from {csv_file_path}.")
            return ExecutionDecision.OK

        except Exception as e:
            logger.error(f"Exception inserting data from {csv_file_path}: {e}")
            raise e
        finally:
            if df is not None:
                del df
            gc.collect()
