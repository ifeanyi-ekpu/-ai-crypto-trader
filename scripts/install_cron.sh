#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
CRON_LOG="$PROJECT_DIR/logs/cron.log"
mkdir -p "$PROJECT_DIR/logs" "$PROJECT_DIR/data"

# Runs every 5 minutes. flock prevents overlapping ticks if an exchange call hangs.
TICK_JOB="*/5 * * * * cd $PROJECT_DIR && /usr/bin/flock -n /tmp/ai-crypto-trader.lock $PROJECT_DIR/scripts/cron_tick.sh >> $CRON_LOG 2>&1"

# Sends a daily summary near midnight UTC. It still only uses paper-mode local data.
DAILY_JOB="55 23 * * * cd $PROJECT_DIR && /usr/bin/flock -n /tmp/ai-crypto-trader-daily.lock $PROJECT_DIR/scripts/cron_tick.sh --report-daily >> $CRON_LOG 2>&1"

( crontab -l 2>/dev/null | grep -v 'ai-crypto-trader.lock' | grep -v 'ai-crypto-trader-daily.lock'; echo "$TICK_JOB"; echo "$DAILY_JOB" ) | crontab -

crontab -l | grep 'ai-crypto-trader'
echo "Cron installed. Logs: $CRON_LOG"
