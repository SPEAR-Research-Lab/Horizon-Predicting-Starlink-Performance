from typing import Callable, Dict, Optional, TypedDict

from pandas import DataFrame
from psycopg2.sql import SQL

from .enums import CsvFiles, Tables
from .sql.create_queries import (
    airports_create_query,
    cf_best_starlink_servers_create_query,
    cities_create_query,
    get_cf_create_query,
    ndt_best_starlink_servers_create_query,
    ndt_temp_create_query,
    processed_dates_create_query,
    unified_telemetry_create_query,
)
from .sql.delete_queries import airport_codes_standardize_cities_query
from .sql.insert_queries import (
    airport_insert_query,
    cf_best_starlink_servers_insert_query,
    cities_insert_query,
    get_cf_insert_query,
    ndt_best_starlink_servers_insert_query,
    ndt_temp_insert_query,
    processed_dates_insert_query,
    unified_telemetry_insert_query,
)
from .utils import clean_airport_codes, clean_cf_servers

type CleanDataframeFn = Callable[[DataFrame], None]


class TableInfo(TypedDict):
    create_query: SQL
    insert_query: SQL
    post_insert_query: Optional[SQL]
    csv_name: Optional[str]
    cleaning_fn: Optional[CleanDataframeFn]


table_data: Dict[Tables, TableInfo] = {
    Tables.PROCESSED_DATES: {
        "create_query": processed_dates_create_query,
        "insert_query": processed_dates_insert_query,
        "post_insert_query": None,
        "csv_name": None,
        "cleaning_fn": None,
    },
    Tables.CITIES: {
        "create_query": cities_create_query,
        "insert_query": cities_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.CITIES.value,
        "cleaning_fn": None,
    },
    Tables.AIRPORT_CODES: {
        "create_query": airports_create_query,
        "insert_query": airport_insert_query,
        "post_insert_query": airport_codes_standardize_cities_query,
        "csv_name": CsvFiles.AIRPORT_CODES.value,
        "cleaning_fn": clean_airport_codes,
    },
    Tables.NDT_BEST_STARLINK_SERVERS: {
        "create_query": ndt_best_starlink_servers_create_query,
        "insert_query": ndt_best_starlink_servers_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.NDT_BEST_STARLINK_SERVERS.value,
        "cleaning_fn": None,
    },
    Tables.CF_BEST_STARLINK_SERVERS: {
        "create_query": cf_best_starlink_servers_create_query,
        "insert_query": cf_best_starlink_servers_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.CF_BEST_STARLINK_SERVERS.value,
        "cleaning_fn": clean_cf_servers,
    },
    Tables.CF_TEMP: {
        "create_query": get_cf_create_query(Tables.CF_TEMP.value),
        "insert_query": get_cf_insert_query(Tables.CF_TEMP.value),
        "post_insert_query": None,
        "csv_name": None,
        "cleaning_fn": None,
    },
    Tables.CF_MEAN: {
        "create_query": get_cf_create_query(Tables.CF_MEAN.value),
        "insert_query": get_cf_insert_query(Tables.CF_MEAN.value),
        "post_insert_query": None,
        "csv_name": None,
        "cleaning_fn": None,
    },
    Tables.CF_90TH_PERCENTILE: {
        "create_query": get_cf_create_query(Tables.CF_90TH_PERCENTILE.value),
        "insert_query": get_cf_insert_query(Tables.CF_90TH_PERCENTILE.value),
        "post_insert_query": None,
        "csv_name": None,
        "cleaning_fn": None,
    },
    Tables.NDT7_TEMP: {
        "create_query": ndt_temp_create_query,
        "insert_query": ndt_temp_insert_query,
        "post_insert_query": None,
        "csv_name": None,
        "cleaning_fn": None,
    },
    Tables.UNIFIED_TELEMETRY: {
        "create_query": unified_telemetry_create_query,
        "insert_query": unified_telemetry_insert_query,
        "post_insert_query": None,
        "csv_name": None,
        "cleaning_fn": None,
    },
}
