#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
PYTHON_BIN=""

for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
    then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python 3.10+ is required. On Ubuntu 24.04, install python3 python3-venv." >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-pip ca-certificates curl git sqlite3
fi

"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
mkdir -p data logs

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID before enabling cron." >&2
fi

echo "Bootstrap complete in $PROJECT_DIR"
