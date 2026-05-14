#!/bin/bash
set -e

sudo -u ec2-user bash <<'EOF'
cd /home/ec2-user/horizon
git pull origin main

cd train-predict-pipeline
source .venv/bin/activate

python -m src.train_model --data-dir ../weekly-measurements-collection/measurements
python -m src.predict_pipeline --output ../leo-viewer/frontend/public

cd /home/ec2-user/horizon
git add leo-viewer/frontend/public/*.json
if git diff --staged --quiet; then
    echo "No changes"
else
    git commit -m "Update predictions - $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    git push
fi
EOF

shutdown -h now
