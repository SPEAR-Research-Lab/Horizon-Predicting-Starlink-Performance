def get_cf_formatted_query(date: str, top_asns: str) -> str:
    return f"""
    SELECT
        measurementUUID AS uuid,
        FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S+00', TIMESTAMP(measurementTime), 'UTC') AS test_time,
        clientCity AS client_city,
        clientRegion AS client_region,
        clientCountry AS client_country_code,
        serverPoP AS server_airport_code,
        clientASN AS asn,
        ROUND(packetLoss.lossRatio, 5) AS packet_loss_rate,

        ROUND((SELECT PERCENTILE_DISC(bps, 0.5) OVER () FROM UNNEST(download.bps) AS bps LIMIT 1) / 1000000, 5) AS download_throughput_mbps,
        CAST(ROUND((SELECT PERCENTILE_DISC(ltc, 0.5) OVER () FROM UNNEST(loadedLatencyMs.download) AS ltc LIMIT 1), 0) AS INT) AS download_latency_ms,
        ROUND(loadedJitterMs.download, 5) AS download_jitter_ms,

        ROUND((SELECT PERCENTILE_DISC(bps, 0.5) OVER () FROM UNNEST(upload.bps) AS bps LIMIT 1) / 1000000, 5) AS upload_throughput_mbps,
        CAST(ROUND((SELECT PERCENTILE_DISC(ltc, 0.5) OVER () FROM UNNEST(loadedLatencyMs.upload) AS ltc LIMIT 1), 0) AS INT) AS upload_latency_ms,
        ROUND(loadedJitterMs.upload, 5) AS upload_jitter_ms
    FROM `measurement-lab.cloudflare.speedtest_speed1`
    WHERE
        date = '{date}'
        AND clientCountry IS NOT NULL AND clientCountry <> ''
        AND (download.bps IS NOT NULL AND ARRAY_LENGTH(download.bps) > 0)
        AND (upload.bps IS NOT NULL AND ARRAY_LENGTH(upload.bps) > 0)
        AND (loadedLatencyMs.download IS NOT NULL AND (SELECT PERCENTILE_DISC(ltc, 0.5) OVER () FROM UNNEST(loadedLatencyMs.download) AS ltc LIMIT 1) > 0)
        AND (loadedLatencyMs.upload IS NOT NULL AND (SELECT PERCENTILE_DISC(ltc, 0.5) OVER () FROM UNNEST(loadedLatencyMs.upload) AS ltc LIMIT 1) > 0)
        AND clientASN IN ({top_asns});"""


def get_ndt_formatted_query(date: str, top_asns: str) -> str:
    return f"""
    SELECT
      a.UUID as uuid,
      FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S+00', TIMESTAMP(a.TestTime), 'UTC') AS test_time,
      client.Geo.City AS client_city,
      client.Geo.Region AS client_region,
      client.Geo.CountryCode AS client_country_code,
      server.Geo.City AS server_city,
      server.Geo.CountryCode AS server_country_code,
      client.Network.ASNumber AS asn,
      ROUND(a.LossRate, 5) AS packet_loss_rate,
      CASE
        WHEN raw.Download.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Download.ServerMeasurements) - 1)].TCPInfo.RTT IS NOT NULL
        THEN ROUND(a.MeanThroughputMbps, 5)
        ELSE NULL
      END AS download_throughput_mbps,
      CAST(ROUND(raw.Download.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Download.ServerMeasurements) - 1)].TCPInfo.RTT / 1000, 0) AS INT) AS download_latency_ms,
      ROUND(raw.Download.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Download.ServerMeasurements) - 1)].TCPInfo.RTTVar / 1000, 5) AS download_jitter_ms,
      CASE
        WHEN raw.Upload.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Upload.ServerMeasurements) - 1)].TCPInfo.RTT IS NOT NULL
        THEN ROUND(a.MeanThroughputMbps, 5)
        ELSE NULL
      END AS upload_throughput_mbps,
      CAST(ROUND(raw.Upload.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Upload.ServerMeasurements) - 1)].TCPInfo.RTT / 1000, 0) AS INT) AS upload_latency_ms,
      ROUND(raw.Upload.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Upload.ServerMeasurements) - 1)].TCPInfo.RTTVar / 1000, 5) AS upload_jitter_ms
    FROM `measurement-lab.ndt.ndt7`
    WHERE
      date = '{date}'
      AND client.Geo.CountryCode IS NOT NULL AND client.Geo.CountryCode <> ''
      AND a.MeanThroughputMbps IS NOT NULL AND a.MeanThroughputMbps <> 0.0
      AND (
        raw.Download.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Download.ServerMeasurements) - 1)].TCPInfo.RTT IS NOT NULL
        AND raw.Download.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Download.ServerMeasurements) - 1)].TCPInfo.RTT > 0
          OR
        raw.Upload.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Upload.ServerMeasurements) - 1)].TCPInfo.RTT IS NOT NULL
        AND raw.Upload.ServerMeasurements[SAFE_OFFSET(ARRAY_LENGTH(raw.Upload.ServerMeasurements) - 1)].TCPInfo.RTT > 0
      )
      AND client.Network.ASNumber IN ({top_asns});"""


def get_cf_best_servers_query(date_from: str, date_to: str, asns: str) -> str:
    month = date_from.split('-')[1]
    year = date_from.split('-')[0]

    return f"""
    WITH city_servers AS (
      SELECT
        clientCity,
        clientCountry,
        serverPoP,
        (SELECT PERCENTILE_DISC(ltc, 0.5) OVER() FROM UNNEST(loadedLatencyMs.download) AS ltc LIMIT 1) AS download_latency_ms,
        (SELECT PERCENTILE_DISC(ltc, 0.5) OVER() FROM UNNEST(loadedLatencyMs.upload) AS ltc LIMIT 1) AS upload_latency_ms,
      FROM `measurement-lab.cloudflare.speedtest_speed1`
      WHERE
        measurementTime >= '{date_from}'
        AND measurementTime <= '{date_to}'
        AND clientCity IS NOT NULL
        AND clientCity <> ''
        AND clientCountry IS NOT NULL
        AND clientCountry <> ''
        AND serverPoP IS NOT NULL
        AND serverPoP <> ''
        AND clientASN IN  ({asns})
    ),

    city_percentiles AS (
      SELECT DISTINCT
        clientCity,
        clientCountry,
        PERCENTILE_CONT(download_latency_ms, 0.01) OVER (PARTITION BY clientCity, clientCountry) AS download_latency_p1,
        PERCENTILE_CONT(upload_latency_ms, 0.01) OVER (PARTITION BY clientCity, clientCountry) AS upload_latency_p1
      FROM city_servers
    )

    SELECT DISTINCT
      cs.clientCity,
      cs.clientCountry,
      cs.serverPoP,
      {month} as month,
      {year} as year
    FROM city_servers cs
    JOIN city_percentiles cp
      ON cs.clientCity = cp.clientCity AND cs.clientCountry = cp.clientCountry
    WHERE
      (cs.download_latency_ms IS NOT NULL
        AND cs.download_latency_ms > 0
        AND cs.download_latency_ms <= cp.download_latency_p1)
      OR
      (cs.upload_latency_ms IS NOT NULL
        AND cs.upload_latency_ms > 0
        AND cs.upload_latency_ms <= cp.upload_latency_p1)
    """


def get_ndt_best_servers_query(date_from: str, date_to: str, asns: str) -> str:
    month = date_from.split('-')[1]
    year = date_from.split('-')[0]

    return f"""
    WITH server_for_client AS (
      SELECT
        client.Geo.City AS client_city,
        client.Geo.CountryCode AS client_country,
        server.Geo.City AS server_city,
        server.Geo.CountryCode AS server_country,
        raw.Download.ServerMeasurements[OFFSET(ARRAY_LENGTH(raw.Download.ServerMeasurements) - 1)].TCPInfo.RTT AS download_latency_ms,
        raw.Upload.ServerMeasurements[OFFSET(ARRAY_LENGTH(raw.Upload.ServerMeasurements) - 1)].TCPInfo.RTT AS upload_latency_ms
      FROM `measurement-lab.ndt.ndt7`
      WHERE date >= '{date_from}'
        AND date <= '{date_to}'
        AND client.Geo.CountryCode IS NOT NULL
        AND client.Geo.CountryCode <> ''
        AND client.Geo.City IS NOT NULL
        AND client.Geo.City <> ''
        AND a.MeanThroughputMbps <> 0.0
        AND client.Network.ASNumber IN ({asns})
    ),

    latency_thresholds AS (
      SELECT DISTINCT
        client_city,
        client_country,
        PERCENTILE_CONT(download_latency_ms, 0.01) OVER (PARTITION BY client_city, client_country) AS download_latency_threshold_ms,
        PERCENTILE_CONT(upload_latency_ms, 0.01) OVER (PARTITION BY client_city, client_country) AS upload_latency_threshold_ms
      FROM server_for_client
      WHERE download_latency_ms IS NOT NULL OR upload_latency_ms IS NOT NULL
    )

    SELECT DISTINCT
      s.client_city,
      s.client_country,
      s.server_city,
      s.server_country,
      {month} as month,
      {year} as year
    FROM server_for_client s
    JOIN latency_thresholds lt
      ON s.client_city = lt.client_city AND s.client_country = lt.client_country
    WHERE
      (s.download_latency_ms IS NOT NULL AND s.download_latency_ms > 0 AND s.download_latency_ms <= lt.download_latency_threshold_ms)
      OR
      (s.upload_latency_ms IS NOT NULL AND s.upload_latency_ms > 0 AND s.upload_latency_ms <= lt.upload_latency_threshold_ms)
    """


def get_countries_with_starlink_query(date_from: str, date_to: str) -> str:
    return f"""
    (SELECT client.Geo.CountryCode AS country_code
    FROM `measurement-lab.ndt.ndt7`
    WHERE
      date >= '{date_from}'
      AND date <= '{date_to}'
      AND client.Network.ASNumber = 14593)
    UNION DISTINCT
    (SELECT clientCountry AS country_code
    FROM `cloudflare.speedtest_speed1`
    WHERE
      measurementTime >= '{date_from}'
      AND measurementTime <= '{date_to}'
      AND clientASN = 14593)
    """
