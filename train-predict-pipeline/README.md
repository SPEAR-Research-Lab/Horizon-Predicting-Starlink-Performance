# Train & Predict Pipeline

AWS-based pipeline that trains Horizon models on the latest Starlink measurements and generates prediction JSONs for the LEO Viewer. Runs weekly on EC2 spot instances, triggered automatically after the data collection workflow completes.

## How It Works

1. GitHub Actions starts an EC2 spot instance (r5.2xlarge) with the user-data script
2. The instance pulls the latest code, downloads enriched measurements from S3
3. Trains fresh ensemble models (Random Forest + Gradient Boosting) for latency and throughput
4. Runs predictions for all H3 hex centers (resolutions 2, 3, 4) and city-level dot points
5. Pushes prediction JSONs to the `predictions-data` orphan branch
6. Self-terminates

## Structure

```
train-predict-pipeline/
├── src/
│   ├── __init__.py
│   ├── train_model.py          # Model training (ensemble RF + GB)
│   ├── predict_pipeline.py     # Orchestrates prediction generation
│   ├── predict.py              # Runs inference on feature CSVs
│   ├── predicts_json.py        # Exports predictions to JSON format
│   └── s3_download.py          # Downloads measurements from S3
├── aws/
│   └── user-data.sh            # EC2 bootstrap script (full pipeline)
└── requirements.txt
```

## Usage

Normally runs via GitHub Actions (`.github/workflows/weekly-predictions.yml`). To run manually:

```bash
cd train-predict-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Download data from S3
python -m src.s3_download --bucket horizon-starlink-data

# Train models
python -m src.train_model --data-dir /tmp/measurements

# Generate predictions
python -m src.predict_pipeline --output ../leo-viewer/frontend/public
```

## Requirements

- Python 3.13+
- AWS credentials (S3 access for measurement data)
- Trained model artifacts in `models/` (created by `train_model.py`)

## GitHub Actions Trigger

The workflow fires automatically when the weekly measurements collection succeeds, or can be dispatched manually. It uses OIDC for AWS authentication and the instance terminates itself after completion (regardless of success or failure). Logs are uploaded to `s3://horizon-starlink-data/pipeline-logs/latest.log`.
