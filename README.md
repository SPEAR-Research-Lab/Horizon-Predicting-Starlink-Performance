# Horizon: Predicting Starlink Performance

This is the artifacts repository for the ACM SIGMETRICS 2026 paper: **Horizon: Understanding and Predicting Global Starlink Performance**.

This project analyzes and predicts Starlink network performance metrics globally using measurements from Cloudflare AIM and M-Lab NDT7 datasets.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Components](#project-components)
- [License](#license)
- [Citation](#citation)

## Prerequisites

- **Python:** 3.13 or later
- **PostgreSQL:** A running PostgreSQL database instance
- **Google Cloud:** BigQuery access (for M-Lab datasets)
- **Git:** For cloning the repository

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd Horizon-Predicting-Starlink-Performance
```

### 2. Create a virtual environment

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Set up the Data Fetching Module

Navigate to the data-fetching directory:

```bash
cd data-fetching
```

Create a `.env` file with your database and Google Cloud credentials:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=<your_postgres_user>
DB_PASSWORD=<your_postgres_password>
DB_NAME=<your_database_name>
```

Initialize the database:

```bash
python -m src.main --init
```

Process data for a specific date:

```bash
python -m src.main --date 2024-01-15
```

### 2. Run Analysis and Visualization

Navigate to the plots directory:

```bash
cd ../plots
```

Install additional dependencies:

```bash
pip install -r requirements.txt
```

Open and run the Jupyter notebooks:

```bash
jupyter notebook
```

Available analysis notebooks:
- **anomaly-filtration-plots/** - Anomaly detection and filtration analysis
- **map-plots/** - Geographic performance visualization
- **statistical-analysis-plots/** - Statistical comparisons
- **weather-validation-plots/** - Weather correlation analysis

> **Note:** Interactive Plotly visualizations in the notebooks don't render on GitHub. Clone the repository and run locally with Jupyter to view all plots.

## Project Components

### Data Fetching (`data-fetching/`)

The data processing system merges NDT7 and Cloudflare AIM datasets from BigQuery, standardizes city names, validates servers, and stores results in PostgreSQL.

**Key Features:**
- Downloads telemetry data from BigQuery
- Standardizes location names and server information
- Identifies optimal servers per location (monthly median latency)
- Automated updates and comprehensive logging

**Database Requirements:** PostgreSQL must exist before running the application.

For detailed instructions, see [data-fetching/README.md](data-fetching/README.md)

### Analysis & Visualization (`plots/`)

Comprehensive Jupyter notebook-based analysis covering:
- Anomaly detection impact assessment
- Geographic and client-server filtering
- Statistical distribution comparisons
- Weather correlation validation

**Note:** Large data files are not committed. Place your CSV data files in the respective `data/` directories within each notebook folder.

For detailed instructions, see [plots/README.md](plots/README.md)

## License

See [LICENSE](LICENSE) for details.
