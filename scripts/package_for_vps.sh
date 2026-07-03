#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p dist
TARBALL="dist/ai-crypto-trader-vps.tar.gz"

tar \
  --exclude='./.venv' \
  --exclude='./data/*.db' \
  --exclude='./logs/*.log' \
  --exclude='./logs/daily_report_*.md' \
  --exclude='./dist' \
  --exclude='./.env' \
  --exclude='./__pycache__' \
  --exclude='./tests/__pycache__' \
  --exclude='./src/trader/__pycache__' \
  -czf "$TARBALL" .

echo "$TARBALL"
