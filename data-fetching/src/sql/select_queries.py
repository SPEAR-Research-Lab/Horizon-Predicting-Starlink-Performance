from psycopg2 import sql


def get_top_asns_query(includes_starlink: bool) -> str:
    return f"""
        WITH rank_within_country_view AS (
        SELECT asn, country_name, RANK() OVER (PARTITION BY country_name ORDER BY rank ASC) AS rank_within_country
        FROM as_statistics
        ),
        filtered_asns AS (
            SELECT a.asn
            FROM as_statistics a
            JOIN rank_within_country_view b ON a.asn = b.asn
            JOIN countries_with_starlink_measurements c ON a.country_code = c.country_code
            WHERE b.rank_within_country <= 5 {"OR a.asn = 14593" if includes_starlink else ""}
        )
        SELECT STRING_AGG(a.asn::TEXT, ',' ORDER BY a.asn) AS asns_csv
        FROM filtered_asns a;
    """


processed_date_select_query = sql.SQL(
    """
    SELECT processed_date
    FROM processed_dates
    WHERE processed_date = %s
"""
)


def get_check_table_exists_query(table_name: str) -> str:
    return f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = '{table_name}'
    );
"""
