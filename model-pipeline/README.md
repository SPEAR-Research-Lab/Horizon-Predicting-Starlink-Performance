# Model Pipeline

The Horizon model-data-pipeline provides end-to-end data enrichment and model training for predicting Starlink performance.

## Overview

### Data Enrichment (`main_enrich.py`)

Transforms raw measurement data into feature-rich datasets by adding:

- **Temporal Features:** Hour, day-of-week, month, year extracted from test timestamps
- **Geographic Features:** Client latitude/longitude (geocoded from city names), client-server distance (great-circle)
- **Weather Features:** Temperature, precipitation, cloud cover, wind speed (interpolated from OpenMeteo)
- **Satellite Density:** Number of Starlink satellites in view (from TLE data)

Input CSV must contain: `client_city`, `client_country_code`, `server_city`, `server_country_code`, `test_time`

Output CSV includes all input columns plus enriched features, with rows containing missing values dropped.

### Model Training (`train_model.py`)

Trains ensemble models (Random Forest + Gradient Boosting) to predict latency or throughput.

## Quick Start

### Enrich Data

**Via command-line flags:**
```bash
python model-pipeline/src/main_enrich.py --src data/raw --dst data/enriched
```

**Via interactive prompts:**
```bash
python model-pipeline/src/main_enrich.py
```
Then enter paths when prompted.

**Short flags:**
```bash
python model-pipeline/src/main_enrich.py -s data/raw -d data/enriched
```

Supports both directory (batch process all CSVs) and single file paths.

### Train Model

```bash
python model-pipeline/src/train_model.py
```

## Folder Structure

```
model-pipeline/
├── src/
│   ├── main_enrich.py              # Data enrichment entry point
│   ├── train_model.py              # Model training entry point
│   ├── filter_anomalies.py         # 3-strategy anomaly detection
│   ├── satellite_enricher.py       # Satellite density computation
│   ├── inter_city_distance_calculator.py  # Distance caching
│   ├── meteo_data_handler.py       # Weather data loading
│   ├── open_meteo_fetcher.py       # OpenMeteo API client
│   ├── constants.py                # Feature specs & paths
│   ├── custom_types.py             # Type definitions
│   ├── utils.py                    # Helper functions
│   ├── logger.py                   # Logging setup
│   └── __init__.py
├── data/
│   ├── raw/                        # Raw measurement data
│   ├── enriched/                   # After feature enrichment
│   ├── filtered/                   # After anomaly removal
│   └── processed/                  # Training-ready data
├── models/                         # Trained model artifacts
├── tests/                          # Unit tests
└── README.md                       # This file
```

## Dependencies

- pandas, numpy, scikit-learn
- geopy (distance calculation)
- requests (API calls)
- python-dateutil (time parsing)
- PyYAML (config)
- joblib (model persistence)
- pytest (testing)

Install: `pip install -r requirements.txt` (from the repository root)

## Pipeline Architecture

1. **Data Collection:** M-Lab NDT7, Cloudflare AIM, OpenMeteo weather, TLE satellite data
2. **Feature Enrichment:** Geographic, temporal, weather, and satellite features
3. **Anomaly Detection:** Removes outliers using percentile, directional MAD, or isolation forest
4. **Model Training:** Ensemble of Random Forest + Gradient Boosting with weight optimization

## References

See `SATELLITE_ENRICHER.md` for satellite density computation details.
