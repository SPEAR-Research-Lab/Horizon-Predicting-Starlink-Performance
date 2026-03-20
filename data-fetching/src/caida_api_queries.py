import csv
import json
from typing import Any

from graphqlclient import GraphQLClient

from .config import data_dir

URL = "https://api.asrank.caida.org/v2/graphql"
PAGE_SIZE = 10000

column_names = ["asn", "asnName", "rank", "country_code", "country_name"]
decoder = json.JSONDecoder()


def _asn_query(first: int, offset: int) -> list[str]:
    return [
        "asns",
        """{
            asns(first:%s, offset:%s) {
                totalCount
                pageInfo {
                    first
                    hasNextPage
                }
                edges {
                    node {
                        asn
                        asnName
                        rank
                        country {
                            iso
                            name
                        }
                    }
                }
            }
        }"""
        % (first, offset),
    ]


def _download_data(url: str, query: Any) -> Any:
    client = GraphQLClient(url)
    return decoder.decode(client.execute(query))


def fetch_asn_data(fname: str) -> None:
    hasNextPage = True
    first = PAGE_SIZE
    offset = 0

    path = data_dir / fname
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=column_names)
        writer.writeheader()

        while hasNextPage:
            type, query = _asn_query(first, offset)
            data = _download_data(URL, query)

            if not ("data" in data and type in data["data"]):
                raise ValueError(f"Failed to parse data for type {type} from {URL}")

            data = data["data"][type]
            for node in data["edges"]:
                n = node["node"]
                row = {
                    "asn": n.get("asn"),
                    "asnName": n.get("asnName"),
                    "rank": n.get("rank"),
                    "country_code": n.get("country", {}).get("iso"),
                    "country_name": n.get("country", {}).get("name"),
                }
                writer.writerow(row)

            hasNextPage = data["pageInfo"]["hasNextPage"]
            offset += data["pageInfo"]["first"]
