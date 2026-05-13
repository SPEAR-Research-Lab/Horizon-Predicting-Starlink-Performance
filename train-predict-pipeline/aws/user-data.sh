#!/bin/bash
set -e

REPO_DIR="/home/ubuntu/horizon"

cd $REPO_DIR
git pull origin main

cd train-predict-pipeline
source .venv/bin/activate

python -m src.train_model --data-dir ../weekly-measurements-collection/measurements
python -m src.predict_pipeline --output ../leo-viewer/frontend/public

cd $REPO_DIR
git add leo-viewer/frontend/public/*.json
if git diff --staged --quiet; then
    echo "No changes"
else
    git commit -m "Update predictions - $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    git push
fi

sudo shutdown -h now
