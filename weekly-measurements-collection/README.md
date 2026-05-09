# Weekly Measurements Collection

A lightweight, automated weekly data collection system for Starlink network measurements. This service automatically fetches, processes, and exports network telemetry data from BigQuery on a weekly schedule.

## Key Features

- **Automated Weekly Pipeline**: Processes the last 7 days of network measurements automatically
- **Best Servers Analysis**: Automatically identifies optimal Starlink servers for each client location (based on last 30 days)
- **Dual Data Sources**: Combines NDT7 and Cloudflare AIM network measurements
- **City Standardization**: Automatically standardizes city names and airport codes
- **CSV Export**: Saves processed measurements to CSV files with automatic timestamping
- **Reference Data Updates**: Auto-updates airport codes and city information when needed
- **UTC Logging**: Comprehensive logging with UTC timestamps

## How It's Different from data-collection

| Feature | data-collection | weekly-measurements-collection |
|---------|-----------------|-------------------------------|
| **Purpose** | Comprehensive, flexible data processing system | Lightweight, automated weekly collector |
| **Storage** | PostgreSQL database | CSV file exports only |
| **Scheduling** | On-demand, CLI-driven | Automated weekly execution |
| **CLI Options** | Extensive (init, date, date-range, export, JSD experiments, etc.) | None - single automated workflow |
| **Date Range** | Any custom date range | Fixed: last 7 days automatically |
| **Use Case** | Research, data analysis, experimentation | Production weekly data collection |
| **Complexity** | Higher (database setup, migrations, multiple modes) | Minimal (just run it) |
| **Dependencies** | Requires PostgreSQL instance + setup | Only requires BigQuery credentials |

## Requirements

- **Python version:** 3.13+
- **Google Cloud:** BigQuery access for M-Lab datasets
- **Environment:** UTC timezone recommended for consistent logging

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   Note: installing the root directory dependencies is enough. This is a minimal set of dependencies for GitHub Actions.

2. **Set up Google Cloud credentials**

    For BigQuery access (follow Google Cloud and MLab documentation)

3. **Optional - Configure data directory:**
   The system will automatically create necessary directories for data, logs, and measurements.

## Usage

Simply run the main script:

```bash
python -m src.main
```

The script will:
1. Check if reference data (cities, airports) needs updating
2. Fetch best performing Starlink servers from the last 30 days
3. Download measurements from the last 7 days (NDT7 and Cloudflare)
4. Process and standardize the data
5. Merge both datasets and export to `measurements/` directory
6. Generate a CSV file with timestamp: `measurements_YYYY-MM-DD_YYYY-MM-DD.csv`

## Output Files

- **measurements/**: Processed and merged measurement data in CSV format
- **logs/**: Timestamped log files with UTC timestamps
- **data/**: Reference data (cities, airport codes)

## Logging

All operations are logged to timestamped files in the `logs/` directory with UTC timestamps. Check logs for detailed execution information, data counts, and any errors.
