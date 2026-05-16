#!/bin/bash

exec > /var/log/horizon-pipeline.log 2>&1

sudo -u ec2-user bash <<'EOF'
set -ex

cd /home/ec2-user/horizon
git fetch origin main
git reset --hard origin/main

cd train-predict-pipeline
rm -f models 2>/dev/null
mkdir -p models
source .venv/bin/activate

python -m src.s3_download --bucket horizon-starlink-data
python -m src.train_model --data-dir /tmp/measurements
python -m src.predict_pipeline --output ../leo-viewer/frontend/public

cd /home/ec2-user/horizon
git add -- leo-viewer/frontend/public/predicted_hex_res2.json leo-viewer/frontend/public/predicted_hex_res3.json leo-viewer/frontend/public/predicted_hex_res4.json leo-viewer/frontend/public/dot_predictions.json
if git diff --staged --quiet; then
    echo "No changes to predictions"
else
    git stash --keep-index
    git commit -m "Update predictions - $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    git pull --rebase origin main
    git push
fi
EOF

echo "Script exit code: $?"
shutdown -h now
