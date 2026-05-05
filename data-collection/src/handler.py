from datetime import timedelta
from typing import Optional

from .config import logger
from .data_classes import LoadDataConfig
from .enums import Tables, UpdateChoices
from .factory import Factory
from .sql.bigquery_queries import (
    get_cf_90th_percentile_formatted_query,
    get_cf_formatted_query,
    get_cf_mean_formatted_query,
    get_ndt_formatted_query,
)
from .utils import parse_date, parse_date_range, parse_date_range_from_months

cf_experiment_data_loader_config = [
    LoadDataConfig(
        table=Tables.CF_MEAN,
        get_query=get_cf_mean_formatted_query,
        dataset_name="Cloudflare AIM (mean aggregated)",
    ),
    LoadDataConfig(
        table=Tables.CF_90TH_PERCENTILE,
        get_query=get_cf_90th_percentile_formatted_query,
        dataset_name="Cloudflare AIM (90th percentile aggregated)",
    ),
]

standard_data_loader_config = [
    LoadDataConfig(
        table=Tables.NDT7_TEMP,
        get_query=get_ndt_formatted_query,
        dataset_name="NDT7",
    ),
    LoadDataConfig(
        table=Tables.CF_TEMP,
        get_query=get_cf_formatted_query,
        dataset_name="Cloudflare AIM",
    ),
]


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

    def date(
        self, date_str: str, export_raw: bool, export_raw_csv_name: Optional[str], process_data_for_jsd_experiment: bool
    ) -> None:
        date = parse_date(date_str)
        logger.info(f"Running with specified date: {date}")
        data_loader = self._factory.get_data_loader()
        data_loader.load_data(date, date, standard_data_loader_config)
        data_processer = self._factory.get_data_processer()
        data_processer.process_data(export_raw, export_raw_csv_name, process_data_for_jsd_experiment)

    def date_range(
        self,
        date_range_str: str,
        export_raw: bool,
        export_raw_csv_name: Optional[str],
        process_data_for_jsd_experiment: bool,
    ) -> None:
        start_date, end_date = parse_date_range(date_range_str)
        logger.info(f"Running with specified date range: {start_date} to {end_date}")
        data_loader = self._factory.get_data_loader()
        data_loader.load_data(start_date, end_date, standard_data_loader_config)
        data_processer = self._factory.get_data_processer()
        data_processer.process_data(export_raw, export_raw_csv_name, process_data_for_jsd_experiment)

    def export_monthly(self, months_str: str) -> None:
        months = [
            (int(month.strip().split("-")[1]), int(month.strip().split("-")[0])) for month in months_str.split(",")
        ]
        data_loader = self._factory.get_data_loader()
        for month, year in months:
            data_loader.export_monthly(month, year, only_download=True)

    def process_data_for_jsd_experiment(self, date_range_str: str) -> None:
        start_date, end_date = parse_date_range_from_months(date_range_str)
        logger.info(f"Running with specified date range: {start_date} to {end_date}")
        data_processer = self._factory.get_data_processer()
        data_loader = self._factory.get_data_loader()
        data_loader.load_data(start_date, end_date, cf_experiment_data_loader_config)
        data_processer = self._factory.get_data_processer()
        data_processer.process_data_for_jsd_experiment()
