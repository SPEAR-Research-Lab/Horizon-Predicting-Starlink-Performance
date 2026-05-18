#!/bin/bash

S3_LOG="s3://horizon-starlink-data/pipeline-logs/latest.log"
LOGFILE="/tmp/pipeline.log"

exec > "$LOGFILE" 2>&1

echo "=== Pipeline started: $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="

trap 'EXIT_CODE=$?
      END_TIME=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

      STATUS="SUCCESS"
      if [ $EXIT_CODE -ne 0 ]; then
          STATUS="FAILED"

          MESSAGE="Pipeline FAILED | exit: $EXIT_CODE | time: $END_TIME | host: $(hostname)"

          echo "=== Pipeline FAILED: $MESSAGE ==="

          aws sns publish \
            --topic-arn failure-email-notification \
            --region eu-west-1 \
            --message "$MESSAGE" \
            --subject "Train and Predict Pipeline FAILED"
      else
          echo "=== Pipeline finished successfully | exit: 0 | time: $END_TIME ==="
      fi

      aws s3 cp "$LOGFILE" "$S3_LOG" || echo "WARNING: log upload to S3 failed"

      shutdown -h now
' EXIT

sudo -u ec2-user bash <<'EOF'
set -euo pipefail

log() { echo "[$(date -u +'%H:%M:%S')] $*"; }

step() {
    local name="$1"; shift
    log "▶ $name"
    if ! "$@"; then
        log "✘ FAILED: $name"
        exit 1
    fi
    log "✔ $name"
}

# Git
cd /home/ec2-user/horizon
step "git lfs install"  git lfs install --skip-smudge --force
step "git fetch"        git fetch origin main
step "git reset"        git reset --hard origin/main
log "HEAD: $(git rev-parse --short HEAD) — $(git log -1 --pretty=%s)"

# Python env — always sync deps, no stale venv risk
cd train-predict-pipeline
[ ! -f .venv/bin/activate ] && python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --quiet
log "Python: $(python --version)"

# Safe model dir reset
[ "$(pwd)" = "/home/ec2-user/horizon/train-predict-pipeline" ] || { log "✘ Wrong directory: $(pwd)"; exit 1; }
rm -rf models && mkdir -p models

# Pipeline
step "s3 download"      python -m src.s3_download --bucket horizon-starlink-data
step "train model"      python -m src.train_model --data-dir /tmp/measurements
step "predict pipeline" python -m src.predict_pipeline --output ../leo-viewer/frontend/public

# Validate and stage outputs
cd /home/ec2-user/horizon
shopt -s nullglob
JSON_FILES=(leo-viewer/frontend/public/predicted_hex_res*.json leo-viewer/frontend/public/dot_predictions.json)
shopt -u nullglob
[ ${#JSON_FILES[@]} -eq 0 ] && { log "✘ No prediction JSONs found"; exit 1; }
for f in "${JSON_FILES[@]}"; do
    log "  ✔ $f ($(wc -c < "$f") bytes)"
done

# Push predictions to orphan branch (force push, no history)
git checkout --orphan predictions-data
git reset
git add -f -- leo-viewer/frontend/public/
git commit -m "Update predictions - $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
git push origin predictions-data --force
EOF