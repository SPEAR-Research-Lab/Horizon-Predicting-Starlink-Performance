from psycopg2 import sql

processed_dates_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS processed_dates (
        processed_date DATE NOT NULL,
        CONSTRAINT processed_dates_pkey PRIMARY KEY (processed_date)
    );

    CREATE INDEX IF NOT EXISTS processed_date_hash_idx
        ON processed_dates USING HASH (processed_date);
"""
)


caida_asn_create_table_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS public.as_statistics
    (
        asn bigint NOT NULL,
        asn_name character varying(512) COLLATE pg_catalog."default",
        rank bigint,
        country_code character varying(512) COLLATE pg_catalog."default",
        country_name character varying(512) COLLATE pg_catalog."default",
        CONSTRAINT as_statistics_pkey PRIMARY KEY (asn)
    );
"""
)


countries_with_starlink_measurements_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS public.countries_with_starlink_measurements
    (
        country_code CHAR(2) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT countries_with_starlink_measurements_pkey PRIMARY KEY (country_code)
    )
"""
)


cities_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS public.cities
    (
        name character varying(200) COLLATE pg_catalog."default" NOT NULL,
        asciiname character varying(200) COLLATE pg_catalog."default" NOT NULL,
        name1 character varying(200) COLLATE pg_catalog."default",
        name2 character varying(200) COLLATE pg_catalog."default",
        name3 character varying(200) COLLATE pg_catalog."default",
        name4 character varying(200) COLLATE pg_catalog."default",
        region character varying(200) COLLATE pg_catalog."default",
        country_code character(2) COLLATE pg_catalog."default" NOT NULL
    )
"""
)


airports_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS airport_country (
        airport_code CHAR(3) NOT NULL,
        country_code CHAR(2) NOT NULL,
        airport_city VARCHAR(255),
        CONSTRAINT airport_country_pkey PRIMARY KEY (airport_code)
    );
"""
)

ndt_best_terrestrial_servers_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS ndt7_terrestrial_servers (
        client_city VARCHAR(255) NOT NULL,
        client_country_code CHAR(2) NOT NULL,
        server_city VARCHAR(255) NOT NULL,
        server_country_code CHAR(2) NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        CONSTRAINT ndt7_terrestrial_servers_pkey PRIMARY KEY (client_city, client_country_code, server_city, server_country_code, month, year)
    );
"""
)

ndt_best_starlink_servers_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS ndt7_starlink_servers (
        client_city VARCHAR(255) NOT NULL,
        client_country_code CHAR(2) NOT NULL,
        server_city VARCHAR(255) NOT NULL,
        server_country_code CHAR(2) NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        CONSTRAINT ndt7_starlink_servers_pkey PRIMARY KEY (client_city, client_country_code, server_city, server_country_code, month, year)
    );
"""
)

cf_best_terrestrial_servers_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS cf_terrestrial_servers (
        client_city VARCHAR(255) NOT NULL,
        client_country_code CHAR(2) NOT NULL,
        server_airport_code CHAR(3) NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        CONSTRAINT cf_terrestrial_servers_pkey PRIMARY KEY (client_city, client_country_code, server_airport_code, month, year)
    );
"""
)

cf_best_starlink_servers_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS cf_starlink_servers (
        client_city VARCHAR(255) NOT NULL,
        client_country_code CHAR(2) NOT NULL,
        server_airport_code CHAR(3) NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        CONSTRAINT cf_starlink_servers_pkey PRIMARY KEY (client_city, client_country_code, server_airport_code, month, year)
    );
"""
)

cf_temp_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS public.cf_temp (
        uuid VARCHAR(255) COLLATE pg_catalog."default" NOT NULL,
        test_time TIMESTAMP WITH TIME ZONE NOT NULL,
        client_city VARCHAR(255) COLLATE pg_catalog."default",
        client_region VARCHAR(255) COLLATE pg_catalog."default",
        client_country_code CHAR(2) COLLATE pg_catalog."default" NOT NULL,
        server_airport_code CHAR(3) COLLATE pg_catalog."default" NOT NULL,
        asn INTEGER NOT NULL,
        packet_loss_rate NUMERIC(10, 5),
        download_throughput_mbps NUMERIC(10, 5),
        download_latency_ms INTEGER,
        download_jitter_ms NUMERIC(10, 5),
        upload_throughput_mbps NUMERIC(10, 5),
        upload_latency_ms INTEGER,
        upload_jitter_ms NUMERIC(10, 5),
        CONSTRAINT cf_temp_pkey PRIMARY KEY (uuid)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS pk_cf_temp
        ON public.cf_temp USING btree
        (uuid ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS time_btree_cf_temp
        ON public.cf_temp USING btree
        (test_time ASC NULLS LAST)
        TABLESPACE pg_default;

    ALTER TABLE IF EXISTS public_cf_temp
        CLUSTER ON time_btree_cf_temp;

    CREATE INDEX IF NOT EXISTS asn_btree_cf_temp
        ON public.cf_temp USING btree
        (asn ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS city_hash_cf_temp
        ON public.cf_temp USING hash
        (client_city COLLATE pg_catalog."default")
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS country_hash_cf_temp
        ON public.cf_temp USING hash
        (client_country_code COLLATE pg_catalog."default")
        TABLESPACE pg_default;
"""
)

ndt_temp_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS public.ndt7_temp
    (
        uuid character varying(255) COLLATE pg_catalog."default" NOT NULL,
        test_time TIMESTAMP WITH TIME ZONE NOT NULL,
        client_region character varying(255) COLLATE pg_catalog."default",
        client_city character varying(255) COLLATE pg_catalog."default",
        client_country_code character(2) COLLATE pg_catalog."default" NOT NULL,
        server_city character varying(255) COLLATE pg_catalog."default",
        server_country_code character(2) COLLATE pg_catalog."default" NOT NULL,
        asn integer NOT NULL,
        packet_loss_rate numeric(10,5) NOT NULL,
        download_throughput_mbps numeric(10,5),
        download_latency_ms integer,
        download_jitter_ms numeric(10,5),
        upload_throughput_mbps numeric(10,5),
        upload_latency_ms integer,
        upload_jitter_ms numeric(10,5),
        CONSTRAINT ndt7_temp_pkey PRIMARY KEY (uuid)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS pk_ndt
        ON public.ndt7_temp USING btree
        (uuid ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS time_btree_ndt7_temp
        ON public.ndt7_temp USING btree
        (test_time ASC NULLS LAST)
        TABLESPACE pg_default;

    ALTER TABLE IF EXISTS public.ndt7_temp
        CLUSTER ON time_btree_ndt7_temp;

    CREATE INDEX IF NOT EXISTS asn_btree_ndt
        ON public.ndt7_temp USING btree
        (asn ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS country_btree_ndt
        ON public.ndt7_temp USING btree
        (client_country_code COLLATE pg_catalog."default" ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS country_hash_ndt
        ON public.ndt7_temp USING hash
        (client_country_code COLLATE pg_catalog."default")
        TABLESPACE pg_default;
"""
)


unified_telemetry_create_query = sql.SQL(
    """
    CREATE TABLE IF NOT EXISTS public.unified_telemetry
    (
        uuid character varying(255) COLLATE pg_catalog."default" NOT NULL,
        test_time TIMESTAMP WITH TIME ZONE NOT NULL,
        client_city character varying(255) COLLATE pg_catalog."default",
        client_region character varying(255) COLLATE pg_catalog."default",
        client_country_code character(2) COLLATE pg_catalog."default" NOT NULL,
        server_city character varying(255) COLLATE pg_catalog."default",
        server_country_code character(2) COLLATE pg_catalog."default" NOT NULL,
        asn integer NOT NULL,
        data_source character varying(255) COLLATE pg_catalog."default" NOT NULL,
        packet_loss_rate numeric(10,5) NOT NULL,
        download_throughput_mbps numeric(10,5),
        download_latency_ms integer,
        download_jitter_ms numeric(10,5),
        upload_throughput_mbps numeric(10,5),
        upload_latency_ms integer,
        upload_jitter_ms numeric(10,5),
        CONSTRAINT unified_telemetry_pkey PRIMARY KEY (uuid)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS pk_unified_telemetry
        ON public.unified_telemetry USING btree
        (uuid ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS time_btree_unified_telemetry
        ON public.unified_telemetry USING btree
        (test_time ASC NULLS LAST)
        TABLESPACE pg_default;

    ALTER TABLE IF EXISTS public.unified_telemetry
        CLUSTER ON time_btree_unified_telemetry;

    CREATE INDEX IF NOT EXISTS asn_btree_unified_telemetry
        ON public.unified_telemetry USING btree
        (asn ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS country_btree_unified_telemetry
        ON public.unified_telemetry USING btree
        (client_country_code COLLATE pg_catalog."default" ASC NULLS LAST)
        TABLESPACE pg_default;

    CREATE INDEX IF NOT EXISTS country_hash_unified_telemetry
        ON public.unified_telemetry USING hash
        (client_country_code COLLATE pg_catalog."default")
        TABLESPACE pg_default;
"""
)
