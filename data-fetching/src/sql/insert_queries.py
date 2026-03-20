from psycopg2 import sql

from ..enums import DataSource

processed_dates_insert_query = sql.SQL(
    """
    INSERT INTO processed_dates (processed_date) VALUES %s
"""
)


cities_insert_query = sql.SQL(
    """
    INSERT INTO cities (name, asciiname, name1, name2, name3, name4, region, country_code)
    VALUES %s
"""
)

ndt_temp_insert_query = sql.SQL(
    """
            INSERT INTO ndt7_temp (
                uuid,
                test_time,
                client_city,
                client_region,
                client_country_code,
                server_city,
                server_country_code,
                asn,
                packet_loss_rate,
                download_throughput_mbps,
                download_latency_ms,
                download_jitter_ms,
                upload_throughput_mbps,
                upload_latency_ms,
                upload_jitter_ms
            ) VALUES %s ON CONFLICT DO NOTHING;
        """
)

cf_temp_insert_query = sql.SQL(
    """
    INSERT INTO cf_temp (
        uuid,
        test_time,
        client_city,
        client_region,
        client_country_code,
        server_airport_code,
        asn,
        packet_loss_rate,
        download_throughput_mbps,
        download_latency_ms,
        download_jitter_ms,
        upload_throughput_mbps,
        upload_latency_ms,
        upload_jitter_ms
    ) VALUES %s
    ON CONFLICT DO NOTHING;
"""
)

unified_telemetry_insert_query = sql.SQL(
    """
    INSERT INTO unified_telemetry (
        uuid,
        test_time,
        client_city,
        client_region,
        client_country_code,
        server_city,
        server_country_code,
        asn,
        data_source,
        packet_loss_rate,
        download_throughput_mbps,
        download_latency_ms,
        download_jitter_ms,
        upload_throughput_mbps,
        upload_latency_ms,
        upload_jitter_ms
    ) VALUES %s
    ON CONFLICT DO NOTHING;
"""
)

airport_insert_query = sql.SQL(
    """
    INSERT INTO airport_country (country_code, airport_city, airport_code)
    VALUES %s
"""
)

ndt_best_terrestrial_servers_insert_query = sql.SQL(
    """
    INSERT INTO ndt7_terrestrial_servers (client_city, client_country_code, server_city, server_country_code, month, year)
    VALUES %s
"""
)

ndt_best_starlink_servers_insert_query = sql.SQL(
    """
    INSERT INTO ndt7_starlink_servers (client_city, client_country_code, server_city, server_country_code, month, year)
    VALUES %s
"""
)

cf_best_terrestrial_servers_insert_query = sql.SQL(
    """
    INSERT INTO cf_terrestrial_servers (client_city, client_country_code, server_airport_code, month, year)
    VALUES %s
"""
)

cf_best_starlink_servers_insert_query = sql.SQL(
    """
    INSERT INTO cf_starlink_servers (client_city, client_country_code, server_airport_code, month, year)
    VALUES %s
"""
)

caida_asn_insert_query = sql.SQL(
    """
    INSERT INTO as_statistics (asn, asn_name, rank, country_code, country_name) VALUES %s
"""
)

countries_with_starlink_measurements_insert_query = sql.SQL(
    """
    INSERT INTO countries_with_starlink_measurements (country_code) VALUES %s
"""
)

global_telemetry_from_cf_insert_query = sql.SQL(
    f"""
    INSERT INTO unified_telemetry (uuid, test_time, client_city, client_region, client_country_code, server_city, server_country_code, asn, data_source, packet_loss_rate, download_throughput_mbps, download_latency_ms, download_jitter_ms, upload_throughput_mbps, upload_latency_ms, upload_jitter_ms)
    SELECT uuid, test_time, client_city, client_region, client_country_code, ac.airport_city AS server_city, ac.country_code AS server_country_code, asn, '{DataSource.CF.value}' AS data_source, packet_loss_rate, download_throughput_mbps, download_latency_ms, download_jitter_ms, upload_throughput_mbps, upload_latency_ms, upload_jitter_ms
    FROM cf_temp JOIN airport_country ac ON cf_temp.server_airport_code = ac.airport_code
    ON CONFLICT DO NOTHING;
"""
)

global_telemetry_from_ndt_insert_query = sql.SQL(
    f"""
    INSERT INTO unified_telemetry (uuid, test_time, client_city, client_region, client_country_code, server_city, server_country_code, asn, data_source, packet_loss_rate, download_throughput_mbps, download_latency_ms, download_jitter_ms, upload_throughput_mbps, upload_latency_ms, upload_jitter_ms)
    SELECT uuid, test_time, client_city, client_region, client_country_code, server_city, server_country_code, asn, '{DataSource.NDT7.value}' AS data_source, packet_loss_rate, download_throughput_mbps, download_latency_ms, download_jitter_ms, upload_throughput_mbps, upload_latency_ms, upload_jitter_ms
    FROM ndt7_temp
    ON CONFLICT DO NOTHING;
"""
)
