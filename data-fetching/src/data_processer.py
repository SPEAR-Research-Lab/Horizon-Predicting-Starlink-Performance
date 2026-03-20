from psycopg2.extensions import connection

from .config import logger
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
from .sql.update_queries import (
    cf_temp_standardize_cities_query,
    ndt_temp_standardize_client_cities_query,
    ndt_temp_standardize_server_cities_query,
)


class DataProcesser:
    def __init__(self, conn: connection) -> None:
        self._conn = conn

    @LogUtils.log_function
    def process_data(self) -> None:
        with self._conn.cursor() as cur:

            ndt7_invalid_terrestrial_servers_query = get_ndt7_temp_delete_invalid_servers_query(
                Tables.NDT_BEST_TERRESTRIAL_SERVERS.value
            )
            cur.execute(ndt7_invalid_terrestrial_servers_query)
            logger.info(f"Deleted {cur.rowcount} invalid NDT7 terrestrial servers.")

            ndt7_invalid_starlink_servers_query = get_ndt7_temp_delete_invalid_servers_query(
                Tables.NDT_BEST_STARLINK_SERVERS.value
            )
            cur.execute(ndt7_invalid_starlink_servers_query)
            logger.info(f"Deleted {cur.rowcount} invalid NDT7 starlink servers.")

            cur.execute(ndt_temp_standardize_client_cities_query)
            logger.info(f"Standardized {cur.rowcount} NDT7 client cities.")
            cur.execute(ndt_temp_standardize_server_cities_query)
            logger.info(f"Standardized {cur.rowcount} NDT7 server cities.")

            cur.execute(global_telemetry_from_ndt_insert_query)
            logger.info(f"Inserted {cur.rowcount} global telemetry records from NDT7 into the database.")

            ndt7_delete_query = delete_all_from_table_query(Tables.NDT7_TEMP.value)
            cur.execute(ndt7_delete_query)
            logger.info(f"Deleted {cur.rowcount} NDT7 temporary records after processing.")

            cf_invalid_terrestrial_servers_query = get_cf_temp_delete_invalid_servers_query(
                Tables.CF_BEST_TERRESTRIAL_SERVERS.value
            )
            cur.execute(cf_invalid_terrestrial_servers_query)
            logger.info(f"Deleted {cur.rowcount} invalid Cloudflare terrestrial servers.")

            cf_invalid_starlink_servers_query = get_cf_temp_delete_invalid_servers_query(
                Tables.CF_BEST_STARLINK_SERVERS.value
            )
            cur.execute(cf_invalid_starlink_servers_query)
            logger.info(f"Deleted {cur.rowcount} invalid Cloudflare starlink servers.")

            cur.execute(cf_temp_standardize_cities_query)
            logger.info(f"Standardized {cur.rowcount} Cloudflare client cities.")

            cur.execute(global_telemetry_from_cf_insert_query)
            logger.info(f"Inserted {cur.rowcount} global telemetry records from Cloudflare into the database.")

            cf_delete_query = delete_all_from_table_query(Tables.CF_TEMP.value)
            cur.execute(cf_delete_query)
            logger.info(f"Deleted {cur.rowcount} Cloudflare temporary records after processing.")

            self._conn.commit()
            logger.info("Data processing completed successfully.")
