import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
import xarray as xr
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY") or ""
DATASET = "hourly-in-situ-meteorological-observations-validated"
VERSION = "1.0"

from .constants import data_dir


class OpenDataAPI:
    def __init__(self, api_token: str):
        self.base_url = "https://api.dataplatform.knmi.nl/open-data/v1"
        self.headers = {"Authorization": api_token}

    def __get_data(self, url, params=None):
        return requests.get(url, headers=self.headers, params=params).json()

    def list_files(self, dataset_name: str, dataset_version: str, params: dict):
        return self.__get_data(
            f"{self.base_url}/datasets/{dataset_name}/versions/{dataset_version}/files",
            params=params,
        )

    def get_file_url(self, dataset_name: str, dataset_version: str, file_name: str):
        return self.__get_data(
            f"{self.base_url}/datasets/{dataset_name}/versions/{dataset_version}/files/{file_name}/url"
        )


def download_file_from_temporary_download_url(download_url: str, out_path: Path):
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception:
        raise RuntimeError("Unable to download file using download URL")

    print(f"Successfully downloaded dataset file to {out_path}")


def get_filename(d: date, hour: int) -> str:
    return f"hourly-observations-validated-{d.strftime('%Y%m%d')}-{hour:02d}.nc"


def convert_nc_to_csv(nc_path: Path) -> Path:
    vars_of_interest = {
        "N": "cloud_cover_octa",
        "FF": "wind_speed",
        "SQ": "precipitation_total",
        "T": "temperature",
    }
    station_vars = ["station", "stationname", "lat", "lon"]

    ds = xr.open_dataset(nc_path)

    # select only variables that exist in dataset
    present_vars = [v for v in vars_of_interest.keys() if v in ds.variables]
    if not present_vars:
        raise RuntimeError(f"No expected variables found in {nc_path}, skipping")

    df_data = ds[present_vars].to_dataframe().reset_index()
    df_data = df_data.rename(columns={k: vars_of_interest[k] for k in present_vars})

    # station info may or may not be available as variables; try to build a stations df
    station_present = [v for v in station_vars if v in ds.variables]
    if station_present:
        df_stations = ds[station_present].to_dataframe().reset_index()[station_present]
        if "station" in df_stations.columns:
            df = pd.merge(df_data, df_stations, on="station", how="left")
        else:
            df = df_data
    else:
        df = df_data

    columns_keep = [
        c for c in ["time", "station", "stationname", "lat", "lon"] if c in df.columns
    ]
    columns_keep += [vars_of_interest[k] for k in present_vars]
    df = df[[c for c in columns_keep if c in df.columns]]

    cloud_cover_col = vars_of_interest.get("N")
    if cloud_cover_col in df.columns:
        df[cloud_cover_col] = df[cloud_cover_col] * 12.5

    csv_path = nc_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    print(f"Converted {nc_path} to {csv_path}")
    return csv_path


def merge_csvs_and_cleanup(
    data_folder: Path, merged_name: str = "netherlands.csv"
) -> Path:
    csv_files = sorted(
        [
            p
            for p in data_folder.iterdir()
            if p.suffix == ".csv" and p.name != merged_name
        ]
    )
    nc_files = sorted([p for p in data_folder.iterdir() if p.suffix == ".nc"])
    if not csv_files:
        raise RuntimeError("No CSV files found to merge")

    dfs = []
    for p in csv_files:
        dfs.append(pd.read_csv(p))

    if not dfs:
        raise RuntimeError("No readable CSVs to merge")

    merged = pd.concat(dfs, ignore_index=True)
    merged_path = data_folder / merged_name
    merged.to_csv(merged_path, index=False)
    print(f"Wrote merged CSV to {merged_path}")

    # remove intermediate CSVs and NCs
    for p in csv_files:
        p.unlink()
    for p in nc_files:
        p.unlink()

    return merged_path


def main():
    api = OpenDataAPI(api_token=API_KEY)
    start_date = date(2025, 9, 6)
    end_date = start_date + timedelta(days=2)
    start = get_filename(start_date, 0)
    end = get_filename(end_date, 0)

    params = {"orderBy": "filename", "begin": start, "end": end, "maxKeys": 1000}
    response = api.list_files(DATASET, VERSION, params)
    if "error" in response:
        raise RuntimeError(f"Unable to retrieve list of files: {response['error']}")

    print(f"Found {response.get('resultCount', 0)} files")

    # Download all files listed
    data_dir.mkdir(parents=True, exist_ok=True)
    for f in response.get("files", []):
        file_name = f.get("filename")
        if not file_name:
            continue
        url_resp = api.get_file_url(DATASET, VERSION, file_name)
        temp_url = url_resp.get("temporaryDownloadUrl")
        if not temp_url:
            print(f"No temporary URL for {file_name}, skipping")
            continue
        out_path = data_dir / file_name
        download_file_from_temporary_download_url(temp_url, out_path)

    # Convert all .nc files in data_dir to csv
    nc_files = sorted([p for p in data_dir.iterdir() if p.suffix == ".nc"])
    csv_paths = []
    for nc in nc_files:
        csvp = convert_nc_to_csv(nc)
        if csvp:
            csv_paths.append(csvp)

    # Merge CSVs into a single file and remove intermediates
    merged = merge_csvs_and_cleanup(data_dir)
    if merged:
        print(merged)
    else:
        raise RuntimeError("Failed to produce merged CSV")


if __name__ == "__main__":
    main()
