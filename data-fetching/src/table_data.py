from typing import Callable, Dict, Optional, TypedDict

from pandas import DataFrame
from psycopg2.sql import SQL

from .enums import CsvFiles, Tables
from .sql.create_queries import (
    airports_create_query,
    caida_asn_create_table_query,
    cf_best_starlink_servers_create_query,
    cf_best_terrestrial_servers_create_query,
    cf_temp_create_query,
    cities_create_query,
    countries_with_starlink_measurements_create_query,
    ndt_best_starlink_servers_create_query,
    ndt_best_terrestrial_servers_create_query,
    ndt_temp_create_query,
    processed_dates_create_query,
    unified_telemetry_create_query,
)
from .sql.delete_queries import airport_codes_standardize_cities_query
from .sql.insert_queries import (
    airport_insert_query,
    caida_asn_insert_query,
    cf_best_starlink_servers_insert_query,
    cf_best_terrestrial_servers_insert_query,
    cf_temp_insert_query,
    cities_insert_query,
    countries_with_starlink_measurements_insert_query,
    ndt_best_starlink_servers_insert_query,
    ndt_best_terrestrial_servers_insert_query,
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
    Tables.NDT_BEST_TERRESTRIAL_SERVERS: {
        "create_query": ndt_best_terrestrial_servers_create_query,
        "insert_query": ndt_best_terrestrial_servers_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.NDT_BEST_TERRESTRIAL_SERVERS.value,
        "cleaning_fn": None,
    },
    Tables.NDT_BEST_STARLINK_SERVERS: {
        "create_query": ndt_best_starlink_servers_create_query,
        "insert_query": ndt_best_starlink_servers_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.NDT_BEST_STARLINK_SERVERS.value,
        "cleaning_fn": None,
    },
    Tables.CF_BEST_TERRESTRIAL_SERVERS: {
        "create_query": cf_best_terrestrial_servers_create_query,
        "insert_query": cf_best_terrestrial_servers_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.CF_BEST_TERRESTRIAL_SERVERS.value,
        "cleaning_fn": clean_cf_servers,
    },
    Tables.CF_BEST_STARLINK_SERVERS: {
        "create_query": cf_best_starlink_servers_create_query,
        "insert_query": cf_best_starlink_servers_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.CF_BEST_STARLINK_SERVERS.value,
        "cleaning_fn": clean_cf_servers,
    },
    Tables.AS_STATISTICS: {
        "create_query": caida_asn_create_table_query,
        "insert_query": caida_asn_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.ASNS.value,
        "cleaning_fn": None,
    },
    Tables.COUNTRIES_WITH_STARLINK_MEASUREMENTS: {
        "create_query": countries_with_starlink_measurements_create_query,
        "insert_query": countries_with_starlink_measurements_insert_query,
        "post_insert_query": None,
        "csv_name": CsvFiles.COUNTRIES_WITH_STARLINK_MEASUREMENTS.value,
        "cleaning_fn": None,
    },
    Tables.CF_TEMP: {
        "create_query": cf_temp_create_query,
        "insert_query": cf_temp_insert_query,
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
