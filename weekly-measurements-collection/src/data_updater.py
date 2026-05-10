from datetime import datetime, timezone
import io
import zipfile

import pandas as pd
import requests

from config import CsvFiles, data_dir, logger
from logger import LogUtils
from utils import delete_files

UPDATE_INTERVAL_DAYS = 30


class DataUpdater:

    @LogUtils.log_function
    @staticmethod
    def maybe_update_data() -> None:
        if not DataUpdater._should_update():
            logger.info(f"Data update skipped. Last update was within {UPDATE_INTERVAL_DAYS} days.")
            return

        logger.info("Updating data...")
        DataUpdater._update_cities()
        DataUpdater._update_airport_codes()
        DataUpdater._update_last_run_date()

    @staticmethod
    def _should_update() -> bool:
        last_update_path = data_dir / CsvFiles.last_update_file
        if not last_update_path.exists():
            logger.info("No previous update record found. Proceeding with update.")
            return True

        try:
            df = pd.read_csv(last_update_path, dtype=str, keep_default_na=False)
            if df.empty or "last_update" not in df.columns or df["last_update"].iloc[0] == "":
                return True

            last_update = datetime.fromisoformat(df["last_update"].iloc[0])
            days_elapsed = (datetime.now(tz=timezone.utc) - last_update).days

            if days_elapsed >= UPDATE_INTERVAL_DAYS:
                logger.info(f"{days_elapsed} days have passed since last update. Proceeding with update.")
                return True
            else:
                logger.info(f"Only {days_elapsed} days have passed since last update. Skipping.")
                return False
        except (pd.errors.ParserError, KeyError, ValueError) as e:
            logger.warning(f"Error reading last update date: {e}. Proceeding with update.")
            return True

    @staticmethod
    def _update_last_run_date() -> None:
        last_update_path = data_dir / CsvFiles.last_update_file
        current_time = datetime.now(tz=timezone.utc).isoformat()
        pd.DataFrame({"last_update": [current_time]}).to_csv(last_update_path, index=False)
        logger.info(f"Last update date recorded: {current_time}")

    @staticmethod
    def _update_airport_codes() -> None:
        DataUpdater._download_file(
            "https://datahub.io/core/airport-codes/_r/-/data/airport-codes.csv",
            CsvFiles.airport_codes,
        )
        DataUpdater._process_airport_codes()
        logger.info("Airport codes updated successfully.")

    @staticmethod
    def _update_cities() -> None:
        DataUpdater._download_file(
            "https://download.geonames.org/export/dump/cities15000.zip",
            "cities.txt",
            unzip=True,
        )
        DataUpdater._download_file(
            "https://download.geonames.org/export/dump/admin1CodesASCII.txt",
            "regions.txt",
        )
        DataUpdater._generate_cities_csv("cities.txt", "regions.txt")
        delete_files(["cities.txt", "regions.txt"])
        logger.info("Cities data updated successfully.")

    @staticmethod
    def _download_file(url: str, file_name: str, unzip: bool = False) -> None:
        file_path = data_dir / file_name
        response = requests.get(url)
        response.raise_for_status()
        if unzip:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(data_dir)
                extracted_files = z.namelist()
                logger.info(f"Extracted files: {extracted_files} to {data_dir}")
                if len(extracted_files) == 1:
                    original_path = data_dir / extracted_files[0]
                    original_path.rename(file_path)
                    logger.info(f"Renamed {original_path} to {file_path}")
                else:
                    logger.warning("Multiple files extracted; skipping rename.")
        else:
            with open(file_path, "wb") as f:
                f.write(response.content)
            logger.info(f"File saved to: {file_path}")

    @staticmethod
    def _generate_cities_csv(cities_txt: str, regions_txt: str) -> None:
        column_names = [
            "geonameid",
            "name",
            "asciiname",
            "alternatenames",
            "latitude",
            "longitude",
            "feature_class",
            "feature_code",
            "country_code",
            "cc2",
            "admin1_code",
            "admin2_code",
            "admin3_code",
            "admin4_code",
            "population",
            "elevation",
            "dem",
            "timezone",
            "modification_date",
        ]
        cities_path = data_dir / cities_txt
        cities_df = pd.read_csv(
            cities_path,
            sep="\t",
            header=None,
            names=column_names,
            dtype=str,
            keep_default_na=False,
        )
        cities_df = cities_df[
            [
                "country_code",
                "name",
                "asciiname",
                "alternatenames",
                "admin1_code",
                "admin2_code",
            ]
        ]

        def _extract_alt_names(alt_str: str) -> list[str]:
            if not alt_str:
                return [""] * 4
            parts = alt_str.split(",")
            return parts[:4] + [""] * (4 - len(parts[:4]))

        alt_names = cities_df["alternatenames"].apply(_extract_alt_names).apply(pd.Series)
        alt_names.columns = pd.Index(["name1", "name2", "name3", "name4"])

        regions_path = data_dir / regions_txt
        regions_df = pd.read_csv(
            regions_path,
            sep="\t",
            header=None,
            names=["admin1_full_code", "admin1_name", "admin1_ascii", "geonameid"],
            dtype=str,
            keep_default_na=False,
        )

        regions_df[["admin1_country", "admin1_code"]] = regions_df["admin1_full_code"].str.split(".", expand=True)
        cities_df = cities_df.merge(
            regions_df[["admin1_country", "admin1_code", "admin1_ascii"]],
            left_on=["country_code", "admin1_code"],
            right_on=["admin1_country", "admin1_code"],
            how="left",
        )

        cities_df.rename(columns={"admin1_ascii": "region"}, inplace=True)

        final_df = pd.concat(
            [
                cities_df["name"],
                cities_df["asciiname"],
                alt_names,
                cities_df["region"],
                cities_df["country_code"],
            ],
            axis=1,
        )

        final_df.columns = pd.Index(
            [
                "name",
                "asciiname",
                "name1",
                "name2",
                "name3",
                "name4",
                "region",
                "country_code",
            ]
        )
        final_df = final_df[
            final_df["asciiname"].notna() & final_df["asciiname"].ne("") & final_df["country_code"].notna()
        ]
        final_df = final_df.drop_duplicates(subset=["name", "asciiname", "region", "country_code"])

        final_df.to_csv(data_dir / CsvFiles.cities, index=False)
        logger.info(f"Cities csv successfully created {len(final_df)} records from {cities_txt} and {regions_txt}.")

    @staticmethod
    def _process_airport_codes() -> None:
        airport_path = data_dir / CsvFiles.airport_codes
        cities_path = data_dir / CsvFiles.cities

        airports_df = pd.read_csv(
            airport_path,
            dtype=str,
            keep_default_na=False,
        )

        airports_df["country_code"] = airports_df["iso_country"].str.split("-").str[0]
        airports_df.rename(columns={"municipality": "airport_city"}, inplace=True)

        cities_df = pd.read_csv(
            cities_path,
            dtype=str,
            keep_default_na=False,
        )

        airports_df = airports_df[(airports_df["airport_city"].notna()) & (airports_df["airport_city"] != "")]

        name_columns = ["name", "asciiname", "name1", "name2", "name3", "name4"]
        mapping_dfs = []

        for col in name_columns:
            temp_df = cities_df[[col, "country_code", "asciiname"]].copy()
            temp_df.columns = ["lookup_name", "country_code", "asciiname"]
            temp_df = temp_df[temp_df["lookup_name"].notna() & (temp_df["lookup_name"] != "")]
            mapping_dfs.append(temp_df)

        lookup_df = pd.concat(mapping_dfs, ignore_index=True)
        lookup_df = lookup_df.drop_duplicates(subset=["lookup_name", "country_code"], keep="first")

        lookup_df["lookup_key"] = lookup_df["lookup_name"] + "|" + lookup_df["country_code"]
        airports_df["lookup_key"] = airports_df["airport_city"] + "|" + airports_df["country_code"]

        lookup_df.rename(columns={"asciiname": "matched_asciiname"}, inplace=True)

        merged = airports_df.merge(lookup_df[["lookup_key", "matched_asciiname"]], on="lookup_key", how="left")

        updates_made = merged["matched_asciiname"].notna().sum()
        airports_df["airport_city"] = merged["matched_asciiname"].fillna(merged["airport_city"])

        airports_df.rename(columns={"airport_city": "municipality"}, inplace=True)
        airports_df.drop(columns=["country_code", "lookup_key"], inplace=True)

        airports_df.to_csv(airport_path, index=False)
        logger.info(f"Airport codes processed: {updates_made} municipalities updated to ASCII names.")
