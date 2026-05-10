import csv

import fastkml
import requests

from .__init__ import data_dir, logger


def query_ground_stations() -> list[tuple[str, str, int]]:
    # get kml-file of Unofficial Starlink Global Gateways & PoPs map
    q = "https://www.google.com/maps/d/u/0/kml?forcekml=1&mid=1805q6rlePY4WZd8QMOaNe2BqAgFkYBY"
    kml = fastkml.KML.from_string(requests.get(q).text)

    stations = []
    for folder in getattr(kml.features[0], 'features', []):
        if hasattr(folder, 'features') and folder.name != "PoPs & Backbone":
            for gs in getattr(folder, 'features', []):
                try:
                    status = next(data for data in gs.extended_data.elements if data.name == "Status").value
                except StopIteration:
                    logger.warning(f"{gs.name} was not well formated; skipped")
                    continue

                if "Live" in status or "live" in status:
                    stations.append((gs.name, *gs.geometry.coords[0][:2]))

    logger.info(f"Amount of ground stations: {len(stations)}")
    return stations


if __name__ == "__main__":
    stations = query_ground_stations()

    with open(data_dir / "ground_stations.csv", "w", newline="", encoding="utf-8") as f:
        csvwriter = csv.writer(f, delimiter=";")
        csvwriter.writerow(("name", "lat", "long"))
        csvwriter.writerows(stations)
