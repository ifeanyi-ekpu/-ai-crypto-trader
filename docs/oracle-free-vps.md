# Oracle Free VPS Deployment Notes

Goal: run the paper-trading bot on an always-on Linux VM using cron + Python + Telegram alerts.

## What is automated here

The repo now includes:

- `scripts/vps_bootstrap_ubuntu.sh` — installs Python environment and project deps on Ubuntu.
- `scripts/cron_tick.sh` — runs one paper-trading tick.
- `scripts/install_cron.sh` — installs a 5-minute cron job plus a daily report cron job.
- `src/trader/notifications.py` — Telegram `sendMessage` integration.
- `src/trader/cron_tick.py` — cron-safe runner that only notifies on important events.

## What cannot be fully automated by Hermes

Oracle account creation still requires you because it involves identity/card verification and acceptance of cloud terms.
Telegram bot creation also requires your Telegram account.

## Oracle VM target

Recommended:

- Provider: Oracle Cloud Always Free
- Region: US East / Ashburn if available
- OS: Ubuntu 24.04 if available, Ubuntu 22.04 acceptable
- Shape: Arm Ampere A1 Always Free if available; AMD Micro fallback
- Disk: stay within Always Free block volume limits

## VPS setup after SSH access exists

Because this folder is not currently a git repo, package/copy is the simplest path.

On your Mac:

```bash
cd /Users/ifeanyi/ai-crypto-trader
bash scripts/package_for_vps.sh
scp dist/ai-crypto-trader-vps.tar.gz ubuntu@<VPS_PUBLIC_IP>:~/
```

On the VPS:

```bash
mkdir -p ~/ai-crypto-trader
cd ~/ai-crypto-trader
tar -xzf ~/ai-crypto-trader-vps.tar.gz
bash scripts/vps_bootstrap_ubuntu.sh
nano .env
bash scripts/install_cron.sh
```

`.env` must include:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## Verify

```bash
cd ~/ai-crypto-trader
./scripts/cron_tick.sh --report-daily
crontab -l
sqlite3 data/kraken_paper_journal.db 'select count(*) from signals;'
tail -50 logs/cron.log
```

## Safety

This deployment still uses:

- paper mode only
- public Kraken candle data only
- no live exchange API keys
- no leverage
- no withdrawal permissions
