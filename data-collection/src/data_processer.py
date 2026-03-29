from typing import Optional

from psycopg2.extensions import connection, cursor

from .config import logger, output_dir
from .enums import Tables
from .logger import LogUtils
from .sql.delete_queries import (
    delete_all_from_table_query,
    get_cf_temp_delete_invalid_servers_query,
    get_ndt7_temp_delete_invalid_servers_query,
)
from .sql.insert_queries import (
    global_telemetry_from_cf_insert_query,
    global_telemetry_from_ndt_insert_query,
)
from .sql.select_queries import get_select_cf_data_query, select_unfiltered_data_query
from .sql.update_queries import (
    get_cf_standardize_cities_query,
    ndt_temp_standardize_client_cities_query,
    ndt_temp_standardize_server_cities_query,
)
from .utils import export_data


class DataProcesser:
    def __init__(self, conn: connection) -> None:
        self._conn = conn

    def _export_raw(self, cur: cursor, csv_name: Optional[str]) -> None:
        output_file = csv_name or "unfiltered_data.csv"
        export_data(cur, select_unfiltered_data_query, output_dir, output_file)
        logger.info("Exported unfiltered data before client-server filtering.")

    def _standardize_cities(self, cur: cursor) -> None:
        cur.execute(ndt_temp_standardize_client_cities_query)
        logger.info(f"Standardized {cur.rowcount} NDT7 client cities.")
        cur.execute(ndt_temp_standardize_server_cities_query)
        logger.info(f"Standardized {cur.rowcount} NDT7 server cities.")

        cur.execute(get_cf_standardize_cities_query(Tables.CF_TEMP.value))
        logger.info(f"Standardized {cur.rowcount} Cloudflare client cities.")

    def _client_server_filtering(self, cur: cursor) -> None:
        ndt7_invalid_starlink_servers_query = get_ndt7_temp_delete_invalid_servers_query(
            Tables.NDT_BEST_STARLINK_SERVERS.value
        )
        cur.execute(ndt7_invalid_starlink_servers_query)
        logger.info(f"Deleted {cur.rowcount} invalid NDT7 starlink servers.")

        cf_invalid_starlink_servers_query = get_cf_temp_delete_invalid_servers_query(
            Tables.CF_TEMP.value, Tables.CF_BEST_STARLINK_SERVERS.value
        )
        cur.execute(cf_invalid_starlink_servers_query)
        logger.info(f"Deleted {cur.rowcount} invalid Cloudflare starlink servers.")

    def _insert(self, cur: cursor) -> None:
        cur.execute(global_telemetry_from_ndt_insert_query)
        logger.info(f"Inserted {cur.rowcount} global telemetry records from NDT7 into the database.")

        cur.execute(global_telemetry_from_cf_insert_query)
        logger.info(f"Inserted {cur.rowcount} global telemetry records from Cloudflare into the database.")

    def _cleanup(self, cur: cursor) -> None:
        ndt7_delete_query = delete_all_from_table_query(Tables.NDT7_TEMP.value)
        cur.execute(ndt7_delete_query)
        logger.info(f"Deleted {cur.rowcount} NDT7 temporary records after processing.")

        cf_delete_query = delete_all_from_table_query(Tables.CF_TEMP.value)
        cur.execute(cf_delete_query)
        logger.info(f"Deleted {cur.rowcount} Cloudflare temporary records after processing.")

    @LogUtils.log_function
    def process_data(self, export_raw: bool, export_raw_csv_name: Optional[str] = None) -> None:
        with self._conn.cursor() as cur:
            if export_raw:
                self._standardize_cities(cur)
                self._export_raw(cur, export_raw_csv_name)

            self._client_server_filtering(cur)

            if not export_raw:
                self._standardize_cities(cur)

            self._insert(cur)
            self._cleanup(cur)

            self._conn.commit()
            logger.info("Data processing completed successfully.")

    @LogUtils.log_function
    def process_cloudflare_mean_and_p90_for_experiment(self) -> None:
        with self._conn.cursor() as cur:
            for cf_table in [Tables.CF_MEAN.value, Tables.CF_90TH_PERCENTILE.value]:
                logger.info(f"Processing Cloudflare data for table {cf_table}...")

                cur.execute(get_cf_standardize_cities_query(cf_table))
                logger.info(f"Standardized {cur.rowcount} client cities.")

                cf_invalid_starlink_servers_query = get_cf_temp_delete_invalid_servers_query(
                    cf_table, Tables.CF_BEST_STARLINK_SERVERS.value
                )
                cur.execute(cf_invalid_starlink_servers_query)
                logger.info(f"Deleted {cur.rowcount} invalid Cloudflare starlink servers.")

                export_data(cur, get_select_cf_data_query(cf_table), output_dir, f"{cf_table}.csv")
                logger.info("Exported data to CSV.")

                cf_delete_query = delete_all_from_table_query(cf_table)
                cur.execute(cf_delete_query)
                logger.info(f"Deleted {cur.rowcount} Cloudflare temporary records after processing.")

                logger.info(f"Finished processing Cloudflare data for table {cf_table}.")
