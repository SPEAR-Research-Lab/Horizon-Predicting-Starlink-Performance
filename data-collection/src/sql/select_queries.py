from psycopg2 import sql

from ..enums import DataSource


def get_check_table_exists_query(table_name: str) -> str:
    return f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = '{table_name}'
    );
"""


def get_select_monthly_data_query(month: int, year: int) -> str:
    return f"""
    SELECT
        uuid,
        TO_CHAR(test_time AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS.USOF') AS test_time,
        data_source,
        client_city,
        client_country_code,
        server_city,
        server_country_code,
        packet_loss_rate,
        download_throughput_mbps,
        download_latency_ms,
        download_jitter_ms
    FROM unified_telemetry
    WHERE EXTRACT(MONTH FROM test_time AT TIME ZONE 'UTC') = {month}
      AND EXTRACT(YEAR  FROM test_time AT TIME ZONE 'UTC') = {year}
      AND download_latency_ms IS NOT NULL
      AND download_latency_ms <> 0
      AND download_throughput_mbps IS NOT NULL
      AND download_throughput_mbps <> 0
      AND client_city IS NOT NULL
      AND server_city IS NOT NULL
"""


select_unfiltered_data_query = sql.SQL(f"""
    (SELECT
        uuid,
        TO_CHAR(test_time AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS.USOF') AS test_time,
        '{DataSource.CF.value}' AS data_source,
        client_city,
        client_country_code,
        ac.airport_city AS server_city,
        ac.country_code AS server_country_code,
        packet_loss_rate,
        download_throughput_mbps,
        download_latency_ms,
        download_jitter_ms
    FROM cf_temp JOIN airport_country ac ON cf_temp.server_airport_code = ac.airport_code)

    UNION

    (SELECT
        uuid,
        TO_CHAR(test_time AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS.USOF') AS test_time,
        '{DataSource.NDT7.value}' AS data_source,
        client_city,
        client_country_code,
        server_city,
        server_country_code,
        packet_loss_rate,
        download_throughput_mbps,
        download_latency_ms,
        download_jitter_ms
    FROM ndt7_temp)
""")

def get_select_cf_data_query(experiment_table: str) -> sql.SQL:
    return sql.SQL(f"""
    (SELECT
        uuid,
        TO_CHAR(test_time AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS.USOF') AS test_time,
        '{DataSource.CF.value}' AS data_source,
        client_city,
        client_country_code,
        ac.airport_city AS server_city,
        ac.country_code AS server_country_code,
        packet_loss_rate,
        download_throughput_mbps,
        download_latency_ms,
        download_jitter_ms
    FROM {experiment_table} JOIN airport_country ac ON {experiment_table}.server_airport_code = ac.airport_code)""")