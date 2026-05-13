from datetime import date, datetime, timedelta, timezone
import io
from pathlib import Path
<<<<<<< leo-viewer
from typing import Tuple
=======
from typing import Optional, Tuple
>>>>>>> main
import zipfile

import pandas as pd
import requests

from config import data_dir, logger


def download_file(url: str, file_name: str, unzip: bool = False) -> None:
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


def save_dataframe_to_csv(df: pd.DataFrame, file_name: str, output_dir: Path = data_dir) -> None:
    file_path = output_dir / file_name
    df.to_csv(file_path, index=False)
    logger.info(f"DataFrame saved to: {file_path}")


def delete_files(file_names: list[str], directory: Path = data_dir) -> None:
    for file_name in file_names:
        file_path = directory / file_name
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
        else:
            logger.warning(f"File not found for deletion: {file_path}")


def _extract_alt_names(alt_str: str) -> list[str]:
    if not alt_str:
        return [""] * 4
    parts = alt_str.split(",")
    return parts[:4] + [""] * (4 - len(parts[:4]))


def generate_cities_csv(cities_txt: str, regions_txt: str, final_file_name: str) -> None:
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
    final_df = final_df[final_df["asciiname"].notna() & final_df["asciiname"].ne("") & final_df["country_code"].notna()]
    final_df = final_df.drop_duplicates(subset=["name", "asciiname", "region", "country_code"])

    final_df.to_csv(data_dir / final_file_name, index=False)
    logger.info(f"Cities csv successfully created {len(final_df)} records from {cities_txt} and {regions_txt}.")


def clean_airport_codes(df: pd.DataFrame) -> None:
    df.dropna(subset=["iata_code"], inplace=True)
    for col in df.columns:
        if col not in ["iso_country", "municipality", "iata_code"]:
            df.drop(columns=col, inplace=True)
    df.rename(
        columns={
            "iso_country": "country_code",
            "municipality": "airport_city",
            "iata_code": "airport_code",
        },
        inplace=True,
    )


def clean_cf_servers(df: pd.DataFrame) -> None:
    df.rename(
        columns={
            "clientCity": "client_city",
            "clientCountry": "client_country",
            "serverPoP": "server_airport_code",
        },
        inplace=True,
    )
    mask = df["client_country"].str.len().ne(2) | df["server_airport_code"].str.len().ne(3)
    df.drop(index=df[mask].index, inplace=True)


def get_tle_file_names(start_date: date, end_date: date) -> list[str]:
    cur = start_date
    result = []
    while cur <= end_date:
        result.append(f"{cur.strftime('%Y-%m-%d')}.tle")
        cur += pd.Timedelta(days=1)
    return result


<<<<<<< leo-viewer
def get_weather_file_name(city: str, country: str, is_historical: bool) -> str:
    return f"{city}_{country}_{'historical' if is_historical else 'forecast'}.csv"
=======
def get_weather_file_names(
    city_country_tuple: Optional[tuple[str, str]], location: Optional[tuple[float, float]]
) -> Tuple[str, str]:
    if city_country_tuple is None and location is None:
        raise ValueError("Either city_country_tuple or location must be provided")
    first, last = city_country_tuple if city_country_tuple is not None else (str(location[0]), str(location[1]))  # type: ignore
    return f"{first}_{last}_historical.csv", f"{first}_{last}_forecast.csv"
>>>>>>> main


def get_previous_and_next_hours_utc(dt: datetime) -> Tuple[str, str]:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    previous_hour = dt.replace(minute=0, second=0, microsecond=0)
    next_hour = previous_hour + timedelta(hours=1)
    return previous_hour.isoformat().replace("T", " "), next_hour.isoformat().replace("T", " ")
