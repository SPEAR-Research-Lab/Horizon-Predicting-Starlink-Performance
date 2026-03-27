from pathlib import Path

ROOT = Path(__file__).parent

data_dir = ROOT / "data"
weather_data_dir = ROOT / "weather_data"
output_dir = ROOT / "output"

data_dir.mkdir(exist_ok=True)
weather_data_dir.mkdir(exist_ok=True)
output_dir.mkdir(exist_ok=True)

BANEASA_RO = (44.51040354106759, 26.078179433868698)  # Bucharest - Baneasa metheorological station, Romania
PITESTI_RO = (44.848914440484144, 24.865873475672295)  # Pitesti - metheorological station, Romania

feature_to_y_label = {
    "temperature_2m": "Temperature (°C)",
    "precipitation": "Precipitation (mm)",
    "wind_speed_10m": "Wind Speed (m/s)",
    "cloud_cover": "Cloud Cover (\\%)"
}