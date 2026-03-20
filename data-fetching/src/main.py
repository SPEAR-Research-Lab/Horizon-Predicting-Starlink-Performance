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
        "-ucws",
        "--update-countries-with-starlink",
        type=str,
        help="Update countries with Starlink for a specific date range. Use format yyyy-mm-dd or yyyy-mm-dd:yyyy-mm-dd, where the first date is the start (left of :) and the second date is the end (right of :). The end date is optional.",
    )

    parser.add_argument(
        "-u",
        "--update",
        type=str,
        help=f"Choices: {[update_choice.value for update_choice in UpdateChoices]}. Choose the update(s) to perform. Use 'asn' for updating ASNs, 'airport' for updating airport codes, and 'cities' for updating city names. You can specify multiple updates by separating them with commas (e.g., 'asn,airport').",
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
        "-so",
        "--starlink-only",
        action="store_true",
        help="When collecting network measurements, only include measurements from Starlink (i.e., for date and date-range commands).",
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
            starlink_only: bool = args.starlink_only
            if args.drop:
                handler.drop()
            if args.init:
                handler.init()
            if args.update_best_servers:
                handler.update_best_servers(args.update_best_servers)
            if args.update_countries_with_starlink:
                handler.update_countries_with_starlink(args.update_countries_with_starlink)
            if args.update:
                handler.update(args.update)
            if args.date:
                handler.date(args.date, starlink_only=starlink_only)
            if args.date_range:
                handler.date_range(args.date_range, starlink_only=starlink_only)
    except psycopg2.OperationalError as e:
        logger.error(f"OperationalError: Failed to connect to the database - {e}")
    except psycopg2.InterfaceError as e:
        logger.error(f"InterfaceError: Problem with the connection interface - {e}")
    except psycopg2.DatabaseError as e:
        logger.error(f"DatabaseError: General database error occurred - {e}")
    except Exception:
        logger.error("Application exited with an error.")
        return

    logger.info("Application exited successfully.")


if __name__ == "__main__":
    main()
