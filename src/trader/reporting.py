from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from trader.journal import TradingJournal


def _format_summary_rows(summary: dict[str, float | int]) -> str:
    trades = int(summary["trades"])
    wins = int(summary["wins"])
    losses = int(summary["losses"])
    win_rate = (wins / trades * 100) if trades else 0.0
    return f"""| Closed trades | {trades} |
| Wins | {wins} |
| Losses | {losses} |
| Win rate | {win_rate:.2f}% |
| Realized P&L | ${summary['pnl']:.2f} |
| Rejected/blocked signals | {summary['rejected']} |"""


def generate_daily_report(journal: TradingJournal, output_dir: str | Path = "logs", day: str | None = None) -> Path:
    journal.initialize()
    report_day = day or datetime.now(timezone.utc).date().isoformat()
    daily = journal.summary(day=report_day)
    all_time = journal.summary()
    portfolio = journal.load_portfolio(starting_equity=0.0)

    if portfolio.starting_equity > 0:
        total_return_pct = (portfolio.equity - portfolio.starting_equity) / portfolio.starting_equity * 100
        equity_line = f"| Equity | ${portfolio.equity:,.2f} |\n| Total return | {total_return_pct:+.2f}% |"
    else:
        equity_line = "| Equity | no portfolio state yet |"

    if portfolio.open_positions:
        position_rows = "\n".join(
            f"| {p.symbol} | {p.side} | {p.quantity:.8f} | {p.entry_price:,.2f} | {p.stop_loss:,.2f} | {p.take_profit:,.2f} |"
            for p in portfolio.open_positions
        )
        positions_section = f"""| Symbol | Side | Quantity | Entry | Stop | Target |
|---|---|---:|---:|---:|---:|
{position_rows}"""
    else:
        positions_section = "No open positions."

    output_path = Path(output_dir) / f"daily_report_{report_day}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Daily Trading Report — {report_day} (UTC)

**Mode:** Paper mode only
**Safety:** No leverage, no live orders, deterministic risk engine.

## Portfolio

| Metric | Value |
|---|---:|
{equity_line}

## Open positions

{positions_section}

## Today ({report_day} UTC)

| Metric | Value |
|---|---:|
{_format_summary_rows(daily)}

## All time

| Metric | Value |
|---|---:|
{_format_summary_rows(all_time)}

## AI/Risk Note

Paper mode is active. P&L includes simulated exchange fees and slippage.
This report is for monitoring only. Do not move to live trading until the
30-day validation gate is met.
"""
    output_path.write_text(text, encoding="utf-8")
    with journal.connect() as conn:
        conn.execute("INSERT INTO daily_reports (day, path) VALUES (?, ?)", (report_day, str(output_path)))
    return output_path


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/trading_journal.db")
    parser.add_argument("--output-dir", default="logs")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    path = generate_daily_report(TradingJournal(args.db), args.output_dir, args.date)
    print(path)


if __name__ == "__main__":
    cli()
