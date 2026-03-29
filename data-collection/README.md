# Data Processing System

This project implements a comprehensive data processing system that merges NDT7 and Cloudflare AIM datasets. It processes network measurement data from BigQuery, standardizes it, and stores it in a PostgreSQL database for analysis.

## Features

- **Data Loading**: Downloads and processes telemetry data from BigQuery (NDT7 and Cloudflare datasets)
- **Data Processing**: Standardizes city names, validates servers, and merges datasets
- **Best Server Analysis**: Identifies optimal servers for each client location based on median latency on a per-month basis
- **CF Aggregation Method Experiments Export**: Generates Cloudflare mean and 90th percentile data by city for JSD (Jensen-Shannon Divergence) experiments
- **Automated Updates**: Updates airport codes, and city information
- **Comprehensive Logging**: Detailed logging with UTC timestamps

## Requirements

- **Python version:** 3.13
- **Database:** PostgreSQL (You must have your own PostgreSQL database instance to connect to)
- **PostgreSQL Driver:** For installing the `psycopg2` library.
- **Google Cloud:** BigQuery access for M-Lab datasets

## Setup

1. **Configure environment variables:**

   Create a `.env` file in the root directory with the following content:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=<your_user>
   DB_PASSWORD=<your_password>
   DB_NAME=<your_database_name>
   ```

**Note:** The PostgreSQL database specified in the environment variables must already exist before running the application.

2. **Set up Google Cloud credentials** for BigQuery access (follow Google Cloud documentation)

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

### Process Date Range
```sh
python -m src.main --date-range 2024-01-01:2024-01-31
```
Downloads and processes telemetry data for a date range (YYYY-MM-DD:YYYY-MM-DD format).

### Update Best Servers
```sh
python -m src.main --update-best-servers 2024-01:2024-12
```
Updates best server mappings for the specified month range (YYYY-MM:YYYY-MM format). The system calculates optimal servers separately for:
- **NDT7 Starlink servers** (ASN 14593)
- **Cloudflare Starlink servers** (ASN 14593)

Best servers are determined per month based on median latency for each client location. Results are stored in separate tables and exported to CSV files. End date is optional - if not provided, defaults to the start date (single month).

### Export Raw Data
```sh
python -m src.main --date 2024-01-15 --export-raw unfiltered_data.csv
```
Exports unfiltered raw data to CSV before client-server filtering is applied. Works with both `--date` and `--date-range`. Data includes measurements from both NDT7 and Cloudflare with standardized city names.

### Export Monthly Data
```sh
python -m src.main --export-monthly 2024-01,2024-02,2024-03
```
Exports filtered data to CSV by month. Provide comma-separated months (format: YYYY-MM). Creates one CSV file per month from the database.

### Export CF Aggregation Method Data for Experiments
```sh
python -m src.main --process-cloudflare-mean-and-p90-for-experiment 2024-01,2024-02,2024-03
```
Calculates and exports Cloudflare mean and 90th percentile statistics by city for specified months. Used for generating data needed in JSD (Jensen-Shannon Divergence) experiments. Use format `yyyy-mm` or `yyyy-mm:yyyy-mm`, where the first date is the start and the second date is the end (optional). Automatically exports the processed data to CSV.

### Update Reference Data
```sh
python -m src.main --update airport,cities
```
Updates airport codes and city information.

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
| `--export-raw FILENAME.csv` | Export unfiltered raw data to CSV before filtering (use with `--date` or `--date-range`) |
| `--export-monthly YYYY-MM[,...]` | Export filtered data to CSV by month (comma-separated months) |
| `--process-cloudflare-mean-and-p90-for-experiment YYYY-MM[:YYYY-MM]` | Calculate and export Cloudflare mean and 90th percentile statistics by city (used for JSD experiments) |
| `--update-best-servers YYYY-MM:YYYY-MM` | Update best server mappings per month for Starlink (end date optional) |
| `--update airport,cities` | Update reference data (airport codes and/or city information) |
| `--drop` | Drop all database tables |

## Data Sources

- **NDT7**: Network Diagnostic Tool measurements from M-Lab
- **Cloudflare AIM**: Cloudflare's speed test measurements
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
│   ├── ndt-best-starlink-servers.csv       # NDT7 best servers for Starlink
│   ├── cf-best-starlink-servers.csv        # Cloudflare best servers for Starlink
│   └── ...
├── logs/                          # Log files (auto-generated)
├── .env                           # Environment configuration
├── requirements.txt               # Python dependencies
├── setup.cfg                      # Tool configurations
├── pyproject.toml                 # Project configuration
├── build.sh                       # Build/lint script
├── scripts/
│   ├── collect_data.py            # Produces the full dataset used in the paper (Jan 1 - Nov 30, 2025)
│   └── data_for_plots.py          # Generates processed data files for the plots project
└── README.md
```

## Scripts

### collect_data.py
Produces the complete dataset used in the paper "Horizon: Understanding and Predicting Global Starlink Performance". This script runs the following operations:
- Initializes the database
- Updates best server mappings for all months in 2025 (January to November)
- Collects and processes network measurements for the entire date range (2025-01-01 to 2025-11-30)
- Exports monthly filtered data to CSV files
- Exports unfiltered raw data for analysis

Run with:
```bash
python scripts/collect_data.py
```

### data_for_plots.py
Generates processed data files needed for the plots project to reproduce the paper's visualizations and statistical analyses. This script exports curated datasets used for:
- Statistical analysis plots
- Map visualizations

Run with:
```bash
python scripts/data_for_plots.py
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
- `ndt7_starlink_servers`: Best NDT7 servers for Starlink per client location per month
- `cf_starlink_servers`: Best Cloudflare servers for Starlink per client location per month
- `cities`: City name standardization data
- `airport_country`: Airport code mappings

## Notes

- Ensure Python 3.13 is installed and available in your PATH
- The script processes past UTC dates only (cannot process current or future dates)
- BigQuery access requires proper Google Cloud authentication
- Large datasets may require significant processing time and storage space
- Monitor logs for detailed execution information and error handling
