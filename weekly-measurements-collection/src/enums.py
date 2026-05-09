from enum import Enum


class CsvFiles(Enum):
    CITIES = "cities.csv"
    AIRPORT_CODES = "airport-codes.csv"
    NDT_BEST_STARLINK_SERVERS = "ndt-best-starlink-servers.csv"
    CF_BEST_STARLINK_SERVERS = "cf-best-starlink-servers.csv"
    LAST_UPDATE_FILE = "last_update.csv"
    CLIENT_CITIES = "client_cities.csv"
    CLIENT_SERVER_DISTANCE = "client_server_distance.csv"
    WORLD_CITIES_COORDINATES = "world_cities_coordinates.csv"
    UNRESOLVED_CITIES = "unresolved_cities.csv"
