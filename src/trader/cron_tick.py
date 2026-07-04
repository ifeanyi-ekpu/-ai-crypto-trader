from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from dotenv import load_dotenv

from trader.config import load_config
from trader.journal import TradingJournal
from trader.notifications import telegram_notifier_from_env
from trader.reporting import generate_daily_report
from trader.scheduler import BotRunner


def journal_event_counts(journal: TradingJournal) -> dict[str, int]:
    journal.initialize()
    with journal.connect() as conn:
        filled_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'filled'").fetchone()[0]
        trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM risk_decisions WHERE approved = 0").fetchone()[0]
    return {"filled_orders": int(filled_orders), "trades": int(trades), "rejected": int(rejected)}


def build_event_message(before: dict[str, int], after: dict[str, int]) -> str | None:
    new_filled = after.get("filled_orders", 0) - before.get("filled_orders", 0)
    new_trades = after.get("trades", 0) - before.get("trades", 0)
    if new_filled <= 0 and new_trades <= 0:
        return None

    lines = ["🤖 Paper trading event"]
    if new_filled > 0:
        lines.append(f"New filled paper orders: {new_filled}")
    if new_trades > 0:
        lines.append(f"New closed paper trades: {new_trades}")
    lines.append("Mode: paper only. No live exchange orders.")
    return "\n".join(lines)


def run_tick(config_path: str, db_path: str, report_daily: bool = False, report_dir: str = "logs") -> str | None:
    cfg = load_config(config_path)
    journal = TradingJournal(db_path)
    before = journal_event_counts(journal)
    portfolio = journal.load_portfolio(
        starting_equity=cfg.paper_equity_usd,
        fee_pct=cfg.execution.fee_pct,
        slippage_bps=cfg.execution.slippage_bps,
    )
    # Trades are journaled as they close during the run, so the portfolio must
    # be saved even if a later symbol fails (e.g. a network error) — otherwise
    # the next tick reloads already-closed positions and double-counts them.
    try:
        BotRunner(config=cfg, journal=journal, portfolio=portfolio).run_once()
    finally:
        journal.save_portfolio(portfolio)
    after = journal_event_counts(journal)
    message = build_event_message(before, after)
    if report_daily:
        report_path = generate_daily_report(journal, output_dir=report_dir)
        report_message = f"📊 Daily paper trading report generated: {report_path}"
        message = f"{message}\n\n{report_message}" if message else report_message
    return message


def cli() -> None:
    parser = argparse.ArgumentParser(description="Cron-safe paper trading tick with optional Telegram notification")
    parser.add_argument("--config", default="config/settings.kraken-paper.yaml")
    parser.add_argument("--db", default="data/kraken_paper_journal.db")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--report-daily", action="store_true")
    parser.add_argument("--report-dir", default="logs")
    args = parser.parse_args()

    if Path(args.env).exists():
        load_dotenv(args.env)

    notifier = telegram_notifier_from_env()
    try:
        message = run_tick(args.config, args.db, args.report_daily, args.report_dir)
    except Exception as exc:  # pragma: no cover - exercised by real cron failures
        error_message = f"🚨 Paper trading bot error: {exc}\n\n{traceback.format_exc(limit=3)}"
        if notifier:
            notifier.send(error_message)
        raise

    if message:
        if notifier:
            notifier.send(message)
        print(message)


if __name__ == "__main__":
    cli()
