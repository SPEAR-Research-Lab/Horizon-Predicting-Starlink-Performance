from psycopg2 import sql

drop_tables_query = sql.SQL("""
    DROP TABLE IF EXISTS cities, airport_country, ndt7_starlink_servers, cf_starlink_servers, cf_temp, cf_mean,
    cf_90th_percentile, ndt7_temp, unified_telemetry CASCADE;
    """)
