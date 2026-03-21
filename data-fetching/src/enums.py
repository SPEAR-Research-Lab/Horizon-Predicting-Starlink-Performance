from enum import Enum


class CsvFiles(Enum):
    CITIES = "cities.csv"
    AIRPORT_CODES = "airport-codes.csv"
    NDT_BEST_STARLINK_SERVERS = "ndt-best-starlink-servers.csv"
    CF_BEST_STARLINK_SERVERS = "cf-best-starlink-servers.csv"


class Tables(Enum):
    PROCESSED_DATES = 'processed_dates'
    CITIES = 'cities'
    AIRPORT_CODES = 'airport_country'
    NDT_BEST_STARLINK_SERVERS = 'ndt7_starlink_servers'
    CF_BEST_STARLINK_SERVERS = 'cf_starlink_servers'
    NDT7_TEMP = 'ndt7_temp'
    CF_TEMP = 'cf_temp'
    UNIFIED_TELEMETRY = 'unified_telemetry'


class UpdateChoices(Enum):
    AIRPORT_CODES = "airport"
    CITIES = "cities"


class ExecutionDecision(Enum):
    OK = 0
    SKIP = 1


class DataSource(Enum):
    NDT7 = "NDT7"
    CF = "Cloudflare AIM"
