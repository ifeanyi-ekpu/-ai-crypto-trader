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
python -m trader.reporting --db data/kraken_paper_journal.db --output-dir logs --weekly
```

The paper portfolio persists in the SQLite database between runs (equity, open
positions, loss streaks). Delete the `--db` file to start a fresh portfolio.

Position sizing is risk-based (`max_risk_per_trade_pct` of equity per trade) and
capped so total open notional never exceeds equity — no implicit leverage. The
quantity calculation uses the expected **net** stop-loss loss after entry
slippage, stop slippage, and round-trip fees, not just the raw entry-to-stop
price distance.

The risk engine also rejects trades whose expected net take-profit after
simulated fees/slippage is not at least `min_net_reward_risk_ratio` times the
expected net stop-loss loss. This keeps small gross targets from becoming net
losers after realistic trading costs.
