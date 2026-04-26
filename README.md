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

### 1. Set up the Data Collection Module

Navigate to the data-collection directory:

```bash
cd data-collection
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

### Data Collection (`data-collection/`)

The data processing system merges NDT7 and Cloudflare AIM datasets from BigQuery, standardizes city names, validates servers, and stores results in PostgreSQL. It implements steps 1 and 2 of our Pipeline.

**Key Features:**
- Downloads telemetry data from BigQuery
- Standardizes location names and server information
- Identifies optimal servers per location (monthly median latency)
- Automated updates and comprehensive logging

**Database Requirements:** PostgreSQL must exist before running the application.

**Automated Scripts:**
- `scripts/collect_data.py` - Produces the complete dataset used in the paper (January 1 - November 30, 2025) with all preprocessing and aggregation steps (steps 1 and 2 of the pipeline)
- `scripts/data_for_plots.py` - Generates processed data files needed for the plots project to reproduce paper visualizations

For detailed instructions, see [data-collection/README.md](data-collection/README.md)

### Analysis & Visualization (`plots/`)

Comprehensive Jupyter notebook-based analysis covering:
- Anomaly detection impact assessment
- Geographic and client-server filtering
- Statistical distribution comparisons
- Weather correlation validation

**Note:** Large data files are not committed. Place your CSV data files in the respective `data/` directories within each notebook folder.

For detailed instructions, see [plots/README.md](plots/README.md)

### Model Pipeline (`model-pipeline/`)

End-to-end data enrichment and model training for predicting Starlink performance. Implements pipeline stages 3-5:

- **Feature Enrichment:** Weather index (PLS-derived), satellite density, geographic and temporal features
- **Anomaly Detection:** Percentile, directional MAD, and isolation forest strategies
- **Model Training:** Ensemble of Random Forest + Gradient Boosting with weight optimization

```bash
# Enrich data
python model-pipeline/src/main_enrich.py --src data/raw --dst data/enriched

# Train models
python model-pipeline/src/train_model.py
```

For detailed instructions, see [model-pipeline/README.md](model-pipeline/README.md)

## License

See [LICENSE](LICENSE) for details.

## Citation

If you use this project, please cite the paper, dataset, and source code:

**Paper:**  
Cristian Benghe, Vlad Graure, Tanya Shreedhar, and Nitinder Mohan. 2026. *Horizon: Understanding and Predicting Global Starlink Performance*. Proc. ACM Meas. Anal. Comput. Syst. 10, 2, Article 41 (June 2026). [DOI link](https://doi.org/10.1145/xxxxxxx)

**Dataset:**  
Cristian Benghe, Vlad Graure, Tanya Shreedhar, and Nitinder Mohan. 2026. *Horizon: Understanding and Predicting Global Starlink Performance – Dataset*. [https://doi.org/10.4121/0bf59468-e5cb-433f-aeb2-e04cf694b65c](https://doi.org/10.4121/0bf59468-e5cb-433f-aeb2-e04cf694b65c)

**Source Code:**  
Cristian Benghe, Vlad Graure, Tanya Shreedhar, and Nitinder Mohan. 2026. *Horizon: Understanding and Predicting Global Starlink Performance – Source Code*. [https://github.com/spear-lab/Horizon-Predicting-Starlink-Performance](https://github.com/spear-lab/Horizon-Predicting-Starlink-Performance)

