#!/bin/bash

S3_LOG="s3://horizon-starlink-data/pipeline-logs/latest.log"
LOGFILE="/tmp/pipeline.log"

exec > "$LOGFILE" 2>&1

echo "=== Pipeline started: $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="

trap 'EXIT_CODE=$?
      echo "=== Pipeline finished: $(date -u +"%Y-%m-%d %H:%M:%S UTC") | exit: $EXIT_CODE ==="
      aws s3 cp "$LOGFILE" "$S3_LOG" || echo "WARNING: log upload to S3 failed"
      shutdown -h now' EXIT

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

# Validate outputs
cd /home/ec2-user/horizon
PREDICTION_FILES=(
    "leo-viewer/frontend/public/predicted_hex_res2.json"
    "leo-viewer/frontend/public/predicted_hex_res3.json"
    "leo-viewer/frontend/public/predicted_hex_res4.json"
    "leo-viewer/frontend/public/dot_predictions.json"
)
for f in "${PREDICTION_FILES[@]}"; do
    [ -f "$f" ] || { log "✘ Missing output: $f"; exit 1; }
    log "  ✔ $f ($(wc -c < "$f") bytes)"
    git add -- "$f"
done

# Commit & push — no stash, no rebase
if git diff --staged --quiet; then
    log "No prediction changes — skipping commit"
else
    step "git commit" git commit -m "Update predictions - $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
    step "git push"   git push origin main
fi
EOF