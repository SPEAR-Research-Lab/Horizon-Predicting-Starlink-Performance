# Processed Crowdsourced Starlink Performance Data

## Overview
This dataset contains processed and filtered crowdsourced Starlink satellite internet performance measurements collected from MLab NDT7 and Cloudflare AIM between January and November 2025. The data is used to train machine learning models that predict Starlink latency and throughput.

## Structure
The dataset contains two directories, each with 12 monthly CSV files (January-November 2025, plus a November 24-only evaluation file):

- `filtered_percentile_0.75/` — Latency measurements filtered using 75th percentile-based outlier removal
- `filtered_isolation_forest_0.75/` — Throughput measurements filtered using Isolation Forest anomaly detection with 0.75 contamination threshold

## Column Descriptions

| Column | Type | Description |
|--------|------|-------------|
| `uuid` | string | Unique measurement identifier |
| `test_time` | datetime (UTC) | Timestamp of the measurement |
| `data_source` | string | Source platform: "NDT7" (MLab) or "Cloudflare AIM" |
| `client_city` | string | City of the client performing the test |
| `client_country_code` | string | ISO 3166-1 alpha-2 country code of the client |
| `server_city` | string | City of the test server |
| `server_country_code` | string | ISO 3166-1 alpha-2 country code of the server |
| `packet_loss_rate` | float | Fraction of packets lost during the test (0.0-1.0) |
| `download_throughput_mbps` | float | Download throughput in megabits per second |
| `download_latency_ms` | float | Download latency in milliseconds |
| `download_jitter_ms` | float | Download jitter in milliseconds |
| `lat` | float | Client latitude (WGS84) |
| `lon` | float | Client longitude (WGS84) |
| `sat_density` | integer | Number of Starlink satellites visible above 25 degrees elevation at the client location at the time of measurement, computed from TLE orbital data |
| `hour` | integer | Hour of the day (0-23, UTC) |
| `hour_with_minute` | float | Hour with fractional minutes (e.g., 14.5 = 14:30) |
| `day_of_week` | integer | Day of the week (0=Monday, 6=Sunday) |
| `month` | integer | Month of the year (1-12) |
| `year` | integer | Year of the measurement |
| `client_server_distance_km` | float | Great-circle distance between client and server in kilometers |
| `temperature_2m` | float | Air temperature at 2m height in degrees Celsius (Open-Meteo API) |
| `precipitation` | float | Precipitation in millimeters (Open-Meteo API) |
| `cloud_cover` | float | Cloud cover percentage (Open-Meteo API) |
| `wind_speed_10m` | float | Wind speed at 10m height in meters per second (Open-Meteo API) |

## File Naming Convention
Files follow the pattern:
`filtered_<metric>_download_<month>_2025_with_sat_density_enriched.csv`

Where `<metric>` is either `download_latency_ms` or `download_throughput_mbps`, and `<month>` is the numeric month (1-11).

The `*_nov24_only.csv` files contain measurements from 24-30 November 2025 used for model evaluation.

## Data Sources
- **MLab NDT7**: Network Diagnostic Tool speed tests (https://www.measurementlab.net/tests/ndt/)
- **Cloudflare AIM**: Cloudflare Aggregated Internet Measurement (https://aim.cloudflare.com/)
- **Satellite density**: Computed from publicly available Starlink TLE data via CelesTrak
- **Weather data**: Open-Meteo Historical Weather API (https://open-meteo.com/)

## Scale
- Approximately 11.6 million latency measurements
- Approximately 11.9 million throughput measurements
- 131 countries represented
- Temporal coverage: January-November 2025

## Associated Publication
This dataset supports a research paper on predicting Starlink network performance using machine learning. Reference details will be added upon publication.

## License
See the 4TU.ResearchData record for license information.

## Contact
Cristian Benghe — Delft University of Technology, Faculty of Electrical Engineering, Mathematics and Computer Science
