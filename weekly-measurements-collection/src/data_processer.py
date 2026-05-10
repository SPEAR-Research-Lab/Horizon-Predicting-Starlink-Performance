from enum import Enum
from typing import Tuple

import pandas as pd

from config import CsvFiles, data_dir, logger
from logger import LogUtils


class Prefix(Enum):
    CLIENT = "client"
    SERVER = "server"


class DataProcesser:
    @LogUtils.log_function
    def process_data(self, ndt_df: pd.DataFrame, cf_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        logger.info("Starting data processing...")
        cities_df = pd.read_csv(data_dir / CsvFiles.cities)

        ndt_servers_df = pd.read_csv(data_dir / CsvFiles.ndt_best_starlink_servers)
        ndt_df = self._filter_ndt_servers(ndt_df, ndt_servers_df)
        ndt_df = self._standardize_ndt_cities(ndt_df, cities_df)
        logger.info(f"NDT measurements after processing: {len(ndt_df)}")

        cf_servers_df = pd.read_csv(data_dir / CsvFiles.cf_best_starlink_servers)
        cf_df = self._filter_cf_servers(cf_df, cf_servers_df)
        cf_df = self._standardize_cf_cities(cf_df, cities_df)
        logger.info(f"CF measurements after processing: {len(cf_df)}")
        return ndt_df, cf_df

    def _standardize_ndt_cities(self, ndt_df: pd.DataFrame, cities_df: pd.DataFrame) -> pd.DataFrame:
        client_standardized = self._standardize_cities_by_prefix(ndt_df, cities_df, Prefix.CLIENT, include_region=True)
        return self._standardize_cities_by_prefix(client_standardized, cities_df, Prefix.SERVER, include_region=False)

    def _standardize_cf_cities(self, cf_df: pd.DataFrame, cities_df: pd.DataFrame) -> pd.DataFrame:
        return self._standardize_cities_by_prefix(cf_df, cities_df, Prefix.CLIENT, include_region=False)

    def _standardize_cities_by_prefix(
        self,
        df: pd.DataFrame,
        cities_df: pd.DataFrame,
        prefix: Prefix,
        include_region: bool,
    ) -> pd.DataFrame:
        city_col = f"{prefix.value}_city"
        country_col = f"{prefix.value}_country_code"
        region_col = f"{prefix.value}_region"

        df_with_city = df[df[city_col].notna() & (df[city_col] != "")].copy()
        if df_with_city.empty:
            return df

        city_cols = [
            "country_code",
            "name",
            "name1",
            "name2",
            "name3",
            "name4",
            "asciiname",
        ]
        if include_region:
            city_cols = city_cols + ["region"]
        cities_for_merge = cities_df[city_cols].copy()

        name_fields = ["name", "name1", "name2", "name3", "name4"]
        matches_list = []
        for name_field in name_fields:
            merge_df = df_with_city[["uuid", city_col, country_col]].merge(
                cities_for_merge,
                left_on=[country_col, city_col],
                right_on=["country_code", name_field],
                how="inner",
            )
            if not merge_df.empty:
                logger.info(f"Matched {len(merge_df)} cities with field '{name_field}'")
                matches_list.append(merge_df)

        if not matches_list:
            logger.warning(
                f"No city matches found for prefix {prefix.value}. Total rows with city: {len(df_with_city)}"
            )
            return df

        all_matches = pd.concat(matches_list, ignore_index=True)
        keep_cols = ["uuid", "asciiname"]
        if include_region:
            keep_cols.append("region")
        matched_cities = all_matches.drop_duplicates(subset=["uuid"], keep="first")[keep_cols]

        logger.info(f"Total unique cities matched for {prefix.value}: {len(matched_cities)}")

        result = df.merge(matched_cities, on="uuid", how="left")
        result[city_col] = result["asciiname"].fillna(result[city_col])

        if include_region:
            result[region_col] = result["region"].fillna(result.get(region_col, None))
            result = result.drop(columns=["asciiname", "region"])
        else:
            result = result.drop(columns=["asciiname"])

        return result

    def _filter_cf_servers(self, cf_df: pd.DataFrame, servers_df: pd.DataFrame) -> pd.DataFrame:
        sv_city_country = pd.MultiIndex.from_frame(servers_df[["client_city", "client_country_code"]].drop_duplicates())

        sv_client_city_country_to_server = pd.MultiIndex.from_frame(
            servers_df[["client_city", "client_country_code", "server_airport_code"]].drop_duplicates()
        )

        sv_country_airport = pd.MultiIndex.from_frame(
            servers_df[["client_country_code", "server_airport_code"]].drop_duplicates()
        )
        sv_client_country = set(servers_df["client_country_code"])

        cf_city_country_mi = pd.MultiIndex.from_frame(cf_df[["client_city", "client_country_code"]])
        cf_client_city_country_to_server_mi = pd.MultiIndex.from_frame(
            cf_df[["client_city", "client_country_code", "server_airport_code"]]
        )
        cf_country_airport_mi = pd.MultiIndex.from_frame(cf_df[["client_country_code", "server_airport_code"]])

        city_country_exists = cf_city_country_mi.isin(sv_city_country)
        client_city_country_to_server_exists = cf_client_city_country_to_server_mi.isin(
            sv_client_city_country_to_server
        )
        country_exists = cf_df["client_country_code"].isin(sv_client_country)
        country_airport_exists = cf_country_airport_mi.isin(sv_country_airport)

        condition_a = city_country_exists & ~client_city_country_to_server_exists
        condition_b = ~city_country_exists & country_exists & ~country_airport_exists

        logger.info(f"CF filter - condition_a matches: {condition_a.sum()}, condition_b matches: {condition_b.sum()}")
        logger.info(f"CF filter - removing {(condition_a | condition_b).sum()} rows")

        return cf_df[~(condition_a | condition_b)].reset_index(drop=True)

    def _filter_ndt_servers(self, ndt_df: pd.DataFrame, servers_df: pd.DataFrame) -> pd.DataFrame:
        sv_city_country = pd.MultiIndex.from_frame(servers_df[["client_city", "client_country_code"]].drop_duplicates())
        sv_client_city_country_to_server = pd.MultiIndex.from_frame(
            servers_df[
                [
                    "client_city",
                    "client_country_code",
                    "server_city",
                    "server_country_code",
                ]
            ].drop_duplicates()
        )
        sv_country_server = pd.MultiIndex.from_frame(
            servers_df[["client_country_code", "server_city", "server_country_code"]].drop_duplicates()
        )
        sv_client_country = set(servers_df["client_country_code"])

        ndt_city_country_mi = pd.MultiIndex.from_frame(ndt_df[["client_city", "client_country_code"]])
        ndt_client_city_country_to_server_mi = pd.MultiIndex.from_frame(
            ndt_df[
                [
                    "client_city",
                    "client_country_code",
                    "server_city",
                    "server_country_code",
                ]
            ]
        )
        ndt_country_server_mi = pd.MultiIndex.from_frame(
            ndt_df[["client_country_code", "server_city", "server_country_code"]]
        )

        city_country_exists = ndt_city_country_mi.isin(sv_city_country)
        client_city_country_to_server_exists = ndt_client_city_country_to_server_mi.isin(
            sv_client_city_country_to_server
        )
        country_exists = ndt_df["client_country_code"].isin(sv_client_country)
        country_server_exists = ndt_country_server_mi.isin(sv_country_server)

        condition_a = city_country_exists & ~client_city_country_to_server_exists
        condition_b = ~city_country_exists & country_exists & ~country_server_exists

        logger.info(f"NDT filter - condition_a matches: {condition_a.sum()}, condition_b matches: {condition_b.sum()}")
        logger.info(f"NDT filter - removing {(condition_a | condition_b).sum()} rows")

        return ndt_df[~(condition_a | condition_b)].reset_index(drop=True)
