from psycopg2 import sql


def get_ndt7_temp_delete_invalid_servers_query(table: str) -> str:
    return f"""
    DELETE FROM ndt7_temp n
    WHERE
        n.asn {"=" if 'starlink' in table else "!="} 14593
        AND (
                (
                    EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_city = n.client_city
                        AND sv.client_country_code = n.client_country_code
                        AND sv.month = EXTRACT(MONTH FROM n.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM n.test_time AT TIME ZONE 'UTC')
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_city = n.client_city
                        AND sv.client_country_code = n.client_country_code
                        AND sv.server_city = n.server_city
                        AND sv.server_country_code = n.server_country_code
                        AND sv.month = EXTRACT(MONTH FROM n.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM n.test_time AT TIME ZONE 'UTC')
                    )
                )
                OR
                (
                    NOT EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_city = n.client_city
                        AND sv.client_country_code = n.client_country_code
                        AND sv.month = EXTRACT(MONTH FROM n.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM n.test_time AT TIME ZONE 'UTC')
                    )
                    AND EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_country_code = n.client_country_code
                        AND sv.month = EXTRACT(MONTH FROM n.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM n.test_time AT TIME ZONE 'UTC')
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_country_code = n.client_country_code
                        AND sv.server_city = n.server_city
                        AND sv.server_country_code = n.server_country_code
                        AND sv.month = EXTRACT(MONTH FROM n.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM n.test_time AT TIME ZONE 'UTC')
                    )
                )
            )
"""


def get_cf_temp_delete_invalid_servers_query(table: str) -> str:
    return f"""
        DELETE FROM cf_temp c
        WHERE
            c.asn {"=" if 'starlink' in table else "!="} 14593
            AND
            (
                (
                    EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_city = c.client_city
                        AND sv.client_country_code = c.client_country_code
                        AND sv.month = EXTRACT(MONTH FROM c.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM c.test_time AT TIME ZONE 'UTC')
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_city = c.client_city
                        AND sv.client_country_code = c.client_country_code
                        AND sv.server_airport_code = c.server_airport_code
                        AND sv.month = EXTRACT(MONTH FROM c.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM c.test_time AT TIME ZONE 'UTC')
                    )
                )
                OR
                (
                    NOT EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_city = c.client_city
                        AND sv.client_country_code = c.client_country_code
                        AND sv.month = EXTRACT(MONTH FROM c.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM c.test_time AT TIME ZONE 'UTC')
                    )
                    AND EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_country_code = c.client_country_code
                        AND sv.month = EXTRACT(MONTH FROM c.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM c.test_time AT TIME ZONE 'UTC')
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM {table} sv
                        WHERE sv.client_country_code = c.client_country_code
                        AND sv.server_airport_code = c.server_airport_code
                        AND sv.month = EXTRACT(MONTH FROM c.test_time AT TIME ZONE 'UTC')
                        AND sv.year = EXTRACT(YEAR FROM c.test_time AT TIME ZONE 'UTC')
                    )
                )
            )
"""


def delete_all_from_table_query(table_name: str) -> sql.SQL:
    query = f"DELETE FROM {table_name};"
    return sql.SQL(query)


airport_codes_standardize_cities_query = sql.SQL(
    """
    UPDATE airport_country ac
    SET
        airport_city = c.asciiname
    FROM cities c
    WHERE
        ac.airport_city IS NOT NULL
        AND ac.airport_city <> ''
        AND ac.airport_city IN (c.name, c.asciiname, c.name1, c.name2, c.name3, c.name4)
        AND ac.country_code = c.country_code;
"""
)
