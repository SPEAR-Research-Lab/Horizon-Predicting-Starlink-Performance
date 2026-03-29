import csv
from pathlib import Path

import requests
from pykml import parser

DATA_DIR = Path(__file__).resolve().parent / "data"
GS_URL = "https://www.google.com/maps/d/u/0/kml?forcekml=1&mid=1805q6rlePY4WZd8QMOaNe2BqAgFkYBY"
POP_URL = (
    "https://raw.githubusercontent.com/clarkzjw/starlink-geoip-data/master/map/pop.json"
)
REQUEST_TIMEOUT = 10
CSV_COLS = ("name", "lat", "lon")


def query_ground_stations():
    response = requests.get(GS_URL)
    root = parser.fromstring(response.content)

    stations = []
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.xpath(".//kml:Placemark", namespaces=ns)

    for pm in placemarks:
        try:
            parent_name = (
                pm.getparent().name.text if hasattr(pm.getparent(), "name") else ""
            )
            if parent_name == "PoPs & Backbone":
                continue

            status_element = pm.xpath(
                './/kml:Data[@name="Status"]/kml:value', namespaces=ns
            )
            status = str(status_element[0].text).lower() if status_element else ""

            if "live" in status:
                coords_text = str(pm.Point.coordinates).strip()
                lon, lat, *_ = map(float, coords_text.split(","))
                stations.append((str(pm.name), lat, lon))

        except Exception as e:
            continue

    return stations


def download_pop_data(url: str) -> list[dict]:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to download POP data: {e}")
        return []


def extract_pops(pop_data: list[dict]) -> list[tuple[str, float, float]]:
    return [
        (entry["code"], entry["lat"], entry["lon"])
        for entry in pop_data
        if entry.get("type") == "netfac"
    ]


def write_csv(rows: list[tuple], file_path: Path, headers: tuple[str, ...]):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"CSV saved: {file_path.resolve()}")


def save_pop_and_gs():
    gs_stations = query_ground_stations()
    write_csv(gs_stations, DATA_DIR / "ground_stations.csv", CSV_COLS)

    pop_data = download_pop_data(POP_URL)
    pops = extract_pops(pop_data)
    write_csv(pops, DATA_DIR / "pops.csv", CSV_COLS)


if __name__ == "__main__":
    save_pop_and_gs()
