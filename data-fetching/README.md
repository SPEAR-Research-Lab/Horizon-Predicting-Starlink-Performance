# Data Processing System

This project implements a comprehensive data processing system that merges NDT7 and Cloudflare AIM datasets. It processes network measurement data from BigQuery, standardizes it, and stores it in a PostgreSQL database for analysis.

## Features

- **Data Loading**: Downloads and processes telemetry data from BigQuery (NDT7 and Cloudflare datasets)
- **Data Processing**: Standardizes city names, validates servers, and merges datasets
- **Best Server Analysis**: Identifies optimal servers for each client location based on median latency, calculated separately for terrestrial and Starlink networks on a per-month basis
- **Starlink Analysis**: Tracks countries with Starlink measurements
- **Automated Updates**: Updates ASN data, airport codes, and city information
- **Comprehensive Logging**: Detailed logging with UTC timestamps

## Requirements

- **Python version:** 3.13
- **Database:** PostgreSQL (You must have your own PostgreSQL database instance to connect to)
- **PostgreSQL Driver:** For installing the `psycopg2` library.
- **Google Cloud:** BigQuery access for M-Lab datasets
- Recommended: Use a virtual environment (e.g., `venv` or `virtualenv`)

## Setup

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd global-telemetry-data-processing
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python3.13 -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Create a `.env` file in the root directory with the following content:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=<your_user>
   DB_PASSWORD=<your_password>
   DB_NAME=<your_database_name>
   ```

**Note:** The PostgreSQL database specified in the environment variables must already exist before running the application.

5. **Set up Google Cloud credentials** for BigQuery access (follow Google Cloud documentation)

## Usage

The main entry point is `src/main.py` with various command-line options:

### Initialize Database
```sh
python -m src.main --init
```
Creates all required tables and populates them with initial data.

### Process Daily Data
```sh
python -m src.main --date 2024-01-15
```
Downloads and processes telemetry data for a specific date (YYYY-MM-DD format).

### Process Daily Data (Starlink Only)
```sh
python -m src.main --date 2024-01-15 --starlink-only
```
Downloads and processes telemetry data for a specific date, including only Starlink measurements.

### Process Date Range
```sh
python -m src.main --date-range 2024-01-01:2024-01-31
```
Downloads and processes telemetry data for a date range (YYYY-MM-DD:YYYY-MM-DD format).

### Process Date Range (Starlink Only)
```sh
python -m src.main --date-range 2024-01-01:2024-01-31 --starlink-only
```
Downloads and processes telemetry data for a date range, including only Starlink measurements.

### Update Best Servers
```sh
python -m src.main --update-best-servers 2024-01:2024-12
```
Updates best server mappings for the specified month range (YYYY-MM:YYYY-MM format). The system calculates optimal servers separately for:
- **NDT7 terrestrial servers** (non-Starlink ISPs)
- **NDT7 Starlink servers** (ASN 14593)
- **Cloudflare terrestrial servers** (non-Starlink ISPs)
- **Cloudflare Starlink servers** (ASN 14593)

Best servers are determined per month based on median latency for each client location. Results are stored in separate tables and exported to CSV files. End date is optional - if not provided, defaults to the start date (single month).

### Update Countries with Starlink
```sh
python -m src.main --update-countries-with-starlink 2024-01-01:2024-01-31
```
Updates the list of countries with Starlink measurements. End date is optional - if not provided, defaults to yesterday.

### Update Reference Data
```sh
python -m src.main --update asn,airport,cities
```
Updates ASN data, airport codes, and city information.

### Drop All Tables (Use with caution!)
```sh
python -m src.main --drop
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--init` | Initialize database tables and populate with reference data |
| `--date YYYY-MM-DD` | Process telemetry data for specific date |
| `--date-range YYYY-MM-DD:YYYY-MM-DD` | Process telemetry data for date range |
| `--starlink-only` | Filter measurements to include only Starlink data (use with --date or --date-range) |
| `--update-best-servers YYYY-MM:YYYY-MM` | Update best server mappings per month for terrestrial and Starlink separately (end date optional) |
| `--update-countries-with-starlink DATE_RANGE` | Update Starlink country data (end date optional) |
| `--update CHOICES` | Update reference data (asn, airport, cities) |
| `--drop` | Drop all database tables |

## Data Sources

- **NDT7**: Network Diagnostic Tool measurements from M-Lab
- **Cloudflare AIM**: Cloudflare's speed test measurements
- **CAIDA ASRank**: ASN and organization data
- **GeoNames**: City and region information
- **Airport Codes**: IATA airport code mappings

## Project Structure

```
global-telemetry-data-processing/
│
├── src/
│   ├── main.py                    # Main entry point
│   ├── handler.py                 # Command handlers
│   ├── factory.py                 # Factory pattern implementation
│   ├── data_loader.py             # BigQuery data loading
│   ├── data_processer.py          # Data processing and standardization
│   ├── table_init.py              # Database table initialization
│   ├── logger.py                  # Logging utilities
│   ├── utils.py                   # Helper utilities
│   ├── enums.py                   # Enumerations
│   ├── custom_exceptions.py       # Custom exception classes
│   └── sql/                       # SQL queries
│       ├── bigquery_queries.py
│       ├── create_queries.py
│       ├── insert_queries.py
│       ├── delete_queries.py
│       └── ...
├── data/
│   ├── cities.csv                           # City reference data
│   ├── ndt-best-terrestrial-servers.csv    # NDT7 best servers for terrestrial ISPs
│   ├── ndt-best-starlink-servers.csv       # NDT7 best servers for Starlink
│   ├── cf-best-terrestrial-servers.csv     # Cloudflare best servers for terrestrial ISPs
│   ├── cf-best-starlink-servers.csv        # Cloudflare best servers for Starlink
│   └── ...
├── logs/                          # Log files (auto-generated)
├── .env                           # Environment configuration
├── requirements.txt               # Python dependencies
├── setup.cfg                      # Tool configurations
├── pyproject.toml                 # Project configuration
├── build.sh                       # Build/lint script
└── README.md
```

## Logging

- Logging is handled by the `LogUtils` class in `src/logger.py`
- Logs are written to the `logs/` directory with UTC timestamps
- Console output is also provided for real-time monitoring
- Use `@LogUtils.log_function` decorator to automatically log function execution

## Development

### Database Schema
The system creates and manages the following main tables:
- `unified_telemetry`: Merged NDT7 and Cloudflare data
- `ndt7_terrestrial_servers`: Best NDT7 servers for terrestrial ISPs per client location per month
- `ndt7_starlink_servers`: Best NDT7 servers for Starlink per client location per month
- `cf_terrestrial_servers`: Best Cloudflare servers for terrestrial ISPs per client location per month
- `cf_starlink_servers`: Best Cloudflare servers for Starlink per client location per month
- `countries_with_starlink_measurements`: Countries with Starlink data
- `as_statistics`: ASN information
- `cities`: City name standardization data
- `airport_country`: Airport code mappings

## Notes

- Ensure Python 3.13 is installed and available in your PATH
- The script processes past UTC dates only (cannot process current or future dates)
- BigQuery access requires proper Google Cloud authentication
- Large datasets may require significant processing time and storage space
- Monitor logs for detailed execution information and error handling
