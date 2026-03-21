from psycopg2 import sql

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
