# AI Crypto Trader

Autonomous **paper-trading first** crypto bot with hard-coded risk controls and optional AI analysis notes.

## Safety stance

- V1 is paper mode only.
- No leverage.
- AI can explain/analyze, but cannot override risk rules.
- Live trading requires a separate explicit approval gate after paper-trading validation.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python -m trader.main --config config/settings.example.yaml --once
python -m trader.reporting --db data/trading_journal.db

# Public Kraken market data, still paper mode only
python -m trader.main --config config/settings.kraken-paper.yaml --db data/kraken_paper_journal.db --once
python -m trader.reporting --db data/kraken_paper_journal.db --output-dir logs
```
