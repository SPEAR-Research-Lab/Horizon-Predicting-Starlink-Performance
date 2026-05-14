import argparse
import os

from dotenv import load_dotenv
import psycopg2

from .config import logger
from .enums import UpdateChoices
from .factory import Factory
from .handler import Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Global Telemetry System")

    parser.add_argument(
        "-i",
        "--init",
        action="store_true",
        help="Initialize the database by creating and populating the required tables.",
    )

    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables in the database. Use with caution!",
    )

    parser.add_argument(
        "-ubs",
        "--update-best-servers",
        type=str,
        help="Update best servers for a specific date range. Best servers will be calculated and updated for every month in the range. Use format yyyy-mm or yyyy-mm:yyyy-mm, where the first date is the start (left of :) and the second date is the end (right of :). The end date is optional.",
    )

    parser.add_argument(
        "-u",
        "--update",
        type=str,
        help=f"Choices: {[update_choice.value for update_choice in UpdateChoices]}. Choose the update(s) to perform. Use 'airport' for updating airport codes, and 'cities' for updating city names. You can specify multiple updates by separating them with commas (e.g., 'asn,airport').",
    )

    parser.add_argument(
        "-d",
        "--date",
        type=str,
        help="Collect network measurements for a specific UTC date (format: yyyy-mm-dd).",
    )

    parser.add_argument(
        "-dr",
        "--date-range",
        type=str,
        help="Collect network measurements for a specific date range (format: yyyy-mm-dd:yyyy-mm-dd). The first date is the start (left of :) and the second date is the end (right of :). The end date is required.",
    )

    parser.add_argument(
        "-er",
        "--export-raw",
        type=str,
        help="Export unfiltered raw data to CSV when used with --date or --date-range. Provide CSV name as an argument (including the .csv extension). Data is exported before client-server filtering is applied.",
    )

    parser.add_argument(
        "-em",
        "--export-monthly",
        type=str,
        help="Export filtered data to CSV by month. Provide comma-separated months (format: yyyy-mm, e.g., '2024-01,2024-02'). Creates one CSV file per month.",
    )

    parser.add_argument(
        "--process-data-for-jsd-experiment",
        type=str,
        help="Calculate and export telemetry data for JSD analysis experiment for a specific date range. Use format yyyy-mm or yyyy-mm:yyyy-mm, where the first date is the start (left of :) and the second date is the end (right of :). The end date is optional. Automatically exports the processed data to CSV.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv()
    logger.info("Starting the application...")

    try:
        with psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
        ) as conn:
            logger.info("Connected to the database successfully.")
            handler = Handler(Factory(conn))
            if args.drop:
                handler.drop()
            if args.init:
                handler.init()
            if args.update_best_servers:
                handler.update_best_servers(args.update_best_servers)
            if args.update:
                handler.update(args.update)
            if args.date:
                handler.date(
                    args.date,
                    args.export_raw is not None,
                    args.export_raw,
                    True if args.process_data_for_jsd_experiment else False,
                )
            if args.date_range:
                handler.date_range(
                    args.date_range,
                    args.export_raw is not None,
                    args.export_raw,
                    True if args.process_data_for_jsd_experiment else False,
                )
            if args.process_data_for_jsd_experiment:
                handler.process_data_for_jsd_experiment(args.process_data_for_jsd_experiment)
            if args.export_monthly:
                handler.export_monthly(args.export_monthly)
    except psycopg2.OperationalError as e:
        logger.exception("OperationalError: Failed to connect to the database")
    except psycopg2.InterfaceError as e:
        logger.exception("InterfaceError: Problem with the connection interface")
    except psycopg2.DatabaseError as e:
        logger.exception("DatabaseError: General database error occurred")
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return

    logger.info("Application exited successfully.")


if __name__ == "__main__":
    main()
