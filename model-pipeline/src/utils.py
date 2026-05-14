import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Tuple

import pandas as pd
from dateutil.relativedelta import relativedelta


class ModelType(Enum):
    DOWNLOAD = "download"
    UPLOAD = "upload"


def get_weather_file_name(city: str, country: str, is_historical: bool) -> str:
    return f"{city}_{country}_{'historical' if is_historical else 'forecast'}.csv"


def get_previous_and_next_hours_utc(dt: datetime) -> Tuple[str, str]:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    previous_hour = dt.replace(minute=0, second=0, microsecond=0)
    next_hour = previous_hour + timedelta(hours=1)
    return previous_hour.isoformat().replace("T", " "), next_hour.isoformat().replace(
        "T", " "
    )


def extract_month_and_year_mark_from_filename(filename: str) -> str:
    match = re.search(r"(?:^|_)(\d{2})_(\d{4})[._]", filename)
    if match:
        return f"{match.group(1)}_{match.group(2)}"

    match = re.search(r"(?:^|_)(\d)_(\d{4})[._]", filename)
    if match:
        return f"{match.group(1)}_{match.group(2)}"

    raise ValueError(
        f"Filename '{filename}' does not contain a valid month and year pattern."
    )


def get_file_matchers(
    files: list[str],
    model_type: ModelType,
    number_of_months: int,
    last_month: Optional[str] = None,
) -> list[str]:
    if last_month is None:
        dates: list[datetime] = []
        for file in files:
            if file.endswith(".csv") and model_type.value in file:
                try:
                    date = extract_month_and_year_mark_from_filename(file)
                    dates.append(datetime.strptime(date, "%m_%Y"))
                except ValueError:
                    continue

        end_date = max(dates) if dates else datetime.now()
    else:
        end_date = datetime.strptime(last_month, "%m_%Y")

    file_matchers = []
    for i in range(number_of_months):
        month_date = end_date - relativedelta(months=i)
        file_matchers.append(f"{month_date.month}_{month_date.year}")
    return file_matchers


def add_weather_index(df: pd.DataFrame, target: str) -> pd.DataFrame:
    df["cloud_cover"] = (df["cloud_cover"] - df["cloud_cover"].mean()) / df[
        "cloud_cover"
    ].std()
    df["precipitation"] = (df["precipitation"] - df["precipitation"].mean()) / (
        df["precipitation"].std() if df["precipitation"].std() != 0 else 1
    )
    df["wind_speed_10m"] = (df["wind_speed_10m"] - df["wind_speed_10m"].mean()) / df[
        "wind_speed_10m"
    ].std()
    df["temperature_2m"] = (df["temperature_2m"] - df["temperature_2m"].mean()) / df[
        "temperature_2m"
    ].std()
    if "latency" in target:
        df["weather_index"] = (
            0.462 * df["cloud_cover"]
            + 0.232 * df["precipitation"]
            + 0.229 * df["wind_speed_10m"]
            + 0.077 * df["temperature_2m"]
        )
    elif "throughput" in target:
        df["weather_index"] = (
            0.619 * df["cloud_cover"]
            + 0.289 * df["precipitation"]
            + 0.087 * df["wind_speed_10m"]
            + 0.005 * df["temperature_2m"]
        )
    else:
        raise ValueError(f"Unknown target for weather index calculation: {target}")

    df = df.drop(
        columns=["cloud_cover", "precipitation", "wind_speed_10m", "temperature_2m"]
    )
    return df
