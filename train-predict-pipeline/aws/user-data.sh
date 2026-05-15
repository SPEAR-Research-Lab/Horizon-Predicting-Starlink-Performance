#!/bin/bash
set -e

sudo -u ec2-user bash <<'EOF'
cd /home/ec2-user/horizon
git pull origin main
git lfs pull

cd train-predict-pipeline
rm -f models 2>/dev/null
mkdir -p models
mkdir -p /tmp/measurements
mkdir -p /tmp/predictions
source .venv/bin/activate

aws s3 sync s3://horizon-starlink-data/measurements/ /tmp/measurements/
aws s3 sync s3://horizon-starlink-data/predictions/ /tmp/predictions/

python -m src.train_model --data-dir /tmp/measurements
python -m src.predict_pipeline --output ../leo-viewer/frontend/public

cd /home/ec2-user/horizon
git add -f leo-viewer/frontend/public/*.json
if git diff --staged --quiet; then
    echo "No changes"
else
    git commit -m "Update predictions - $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    git push
fi
EOF

shutdown -h now
