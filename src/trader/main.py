from __future__ import annotations

import argparse

from trader.config import load_config
from trader.journal import TradingJournal
from trader.portfolio import PaperPortfolio
from trader.scheduler import BotRunner, run_loop


def cli() -> None:
    parser = argparse.ArgumentParser(description="AI-assisted crypto paper-trading bot")
    parser.add_argument("--config", default="config/settings.example.yaml")
    parser.add_argument("--db", default="data/trading_journal.db")
    parser.add_argument("--once", action="store_true", help="Run one paper-trading cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval-seconds", type=int, default=300)
    args = parser.parse_args()

    cfg = load_config(args.config)
    journal = TradingJournal(args.db)
    portfolio = PaperPortfolio(
        starting_equity=cfg.paper_equity_usd,
        fee_pct=cfg.execution.fee_pct,
        slippage_bps=cfg.execution.slippage_bps,
    )
    runner = BotRunner(config=cfg, journal=journal, portfolio=portfolio)

    if args.loop:
        run_loop(runner, args.interval_seconds)
    else:
        runner.run_once()
        print(f"Paper cycle complete. Equity: ${portfolio.equity:.2f}. Open positions: {len(portfolio.open_positions)}")


if __name__ == "__main__":
    cli()
