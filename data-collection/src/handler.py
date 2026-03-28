from datetime import timedelta
from typing import Optional

from .config import logger
from .enums import ExecutionDecision, UpdateChoices
from .factory import Factory
from .utils import parse_date, parse_date_range, parse_date_range_from_months


class Handler:
    def __init__(self, factory: Factory) -> None:
        self._factory = factory

    def drop(self) -> None:
        confirm = input("Are you sure you want to drop all tables? (y/n): ").strip().lower()
        if confirm == "y":
            logger.info("Drop flag confirmed. Dropping all tables...")
            table_initializer = self._factory.get_table_initializer()
            table_initializer.drop_tables()
        else:
            logger.info("Drop flag detected, but operation cancelled by user.")

    def init(self) -> None:
        logger.info("Initialization flag detected. Performing setup...")
        table_initializer = self._factory.get_table_initializer()
        table_initializer.initialize_tables()

    def update_best_servers(self, date_range_str: str) -> None:
        start_date, end_date = parse_date_range_from_months(date_range_str)
        data_loader = self._factory.get_data_loader()
        while start_date <= end_date:
            end_of_month = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            data_loader.update_best_servers(start_date, end_of_month)
            start_date = (start_date + timedelta(days=32)).replace(day=1)

    def update(self, choices_str: str) -> None:
        choices = [UpdateChoices(choice_str) for choice_str in set(choices_str.split(","))]
        logger.info(f"Update choices detected: {choices}")
        table_initializer = self._factory.get_table_initializer()
        for choice in choices:
            if choice == UpdateChoices.AIRPORT_CODES:
                table_initializer.update_airport_codes()
            elif choice == UpdateChoices.CITIES:
                table_initializer.update_cities()

    def date(self, date_str: str, export_raw: bool, export_raw_csv_name: Optional[str] = None) -> None:
        date = parse_date(date_str)
        logger.info(f"Running with specified date: {date}")
        data_loader = self._factory.get_data_loader()
        if data_loader.load_data(date) == ExecutionDecision.OK:
            data_processer = self._factory.get_data_processer()
            data_processer.process_data(export_raw, export_raw_csv_name=export_raw_csv_name)

    def date_range(self, date_range_str: str, export_raw: bool, export_raw_csv_name: Optional[str]) -> None:
        start_date, end_date = parse_date_range(date_range_str)
        logger.info(f"Running with specified date range: {start_date} to {end_date}")
        date = end_date
        while date >= start_date:
            data_loader = self._factory.get_data_loader()
            if data_loader.load_data(date) == ExecutionDecision.OK:
                data_processer = self._factory.get_data_processer()
                data_processer.process_data(export_raw, export_raw_csv_name=export_raw_csv_name)
            date -= timedelta(days=1)

    def export_monthly(self, months_str: str) -> None:
        months = [
            (int(month.strip().split("-")[1]), int(month.strip().split("-")[0])) for month in months_str.split(",")
        ]
        data_loader = self._factory.get_data_loader()
        for month, year in months:
            data_loader.export_monthly(month, year)
