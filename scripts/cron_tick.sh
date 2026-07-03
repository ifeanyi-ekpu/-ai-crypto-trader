#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Run scripts/vps_bootstrap_ubuntu.sh first." >&2
  exit 1
fi

.venv/bin/python -m trader.cron_tick \
  --config config/settings.kraken-paper.yaml \
  --db data/kraken_paper_journal.db \
  "$@"
