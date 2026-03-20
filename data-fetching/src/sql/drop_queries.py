from psycopg2 import sql

drop_tables_query = sql.SQL(
    """
    DROP TABLE IF EXISTS as_statistics, countries_with_starlink_measurements,
    cities, airport_country, ndt7_terrestrial_servers, ndt7_starlink_servers,
    cf_terrestrial_servers, cf_starlink_servers, cf_temp, ndt7_temp,
    unified_telemetry, processed_dates CASCADE;
    """
)
