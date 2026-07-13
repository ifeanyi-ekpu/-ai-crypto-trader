from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
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


def _parse_day(day: str) -> date:
    return datetime.strptime(day, "%Y-%m-%d").date()


def _summary_between(journal: TradingJournal, start_day: str, end_day: str) -> dict[str, float | int]:
    end_exclusive = (_parse_day(end_day) + timedelta(days=1)).isoformat()
    with journal.connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS trades, COALESCE(SUM(pnl), 0) AS pnl FROM trades WHERE closed_at >= ? AND closed_at < ?",
            (start_day, end_exclusive),
        ).fetchone()
        wins = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE closed_at >= ? AND closed_at < ? AND pnl > 0",
            (start_day, end_exclusive),
        ).fetchone()[0]
        losses = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE closed_at >= ? AND closed_at < ? AND pnl < 0",
            (start_day, end_exclusive),
        ).fetchone()[0]
        rejected = conn.execute(
            "SELECT COUNT(*) FROM risk_decisions WHERE approved = 0 AND ts >= ? AND ts < ?",
            (start_day, end_exclusive),
        ).fetchone()[0]
    return {"trades": int(row["trades"]), "pnl": float(row["pnl"]), "wins": int(wins), "losses": int(losses), "rejected": int(rejected)}


def _top_rejection_reasons(journal: TradingJournal, start_day: str, end_day: str, limit: int = 5) -> str:
    end_exclusive = (_parse_day(end_day) + timedelta(days=1)).isoformat()
    with journal.connect() as conn:
        rows = conn.execute(
            """
            SELECT reason, COUNT(*) AS count
            FROM risk_decisions
            WHERE approved = 0 AND ts >= ? AND ts < ?
            GROUP BY reason
            ORDER BY count DESC, reason
            LIMIT ?
            """,
            (start_day, end_exclusive, limit),
        ).fetchall()
    if not rows:
        return "No rejected/blocked signals in this period."
    return "\n".join(f"| {row['reason']} | {row['count']} |" for row in rows)


def _portfolio_equity_line(journal: TradingJournal) -> str:
    portfolio = journal.load_portfolio(starting_equity=0.0)
    if portfolio.starting_equity > 0:
        total_return_pct = (portfolio.equity - portfolio.starting_equity) / portfolio.starting_equity * 100
        return f"| Equity | ${portfolio.equity:,.2f} |\n| Total return | {total_return_pct:+.2f}% |"
    return "| Equity | no portfolio state yet |"


def generate_daily_report(journal: TradingJournal, output_dir: str | Path = "logs", day: str | None = None) -> Path:
    journal.initialize()
    report_day = day or datetime.now(timezone.utc).date().isoformat()
    daily = journal.summary(day=report_day)
    all_time = journal.summary()
    portfolio = journal.load_portfolio(starting_equity=0.0)
    equity_line = _portfolio_equity_line(journal)

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


def generate_weekly_report(journal: TradingJournal, output_dir: str | Path = "logs", end_day: str | None = None) -> Path:
    journal.initialize()
    period_end = _parse_day(end_day) if end_day else datetime.now(timezone.utc).date()
    period_start = period_end - timedelta(days=6)
    start_text = period_start.isoformat()
    end_text = period_end.isoformat()
    weekly = _summary_between(journal, start_text, end_text)
    all_time = journal.summary()
    rejection_rows = _top_rejection_reasons(journal, start_text, end_text)
    rejection_table = (
        "No rejected/blocked signals in this period."
        if rejection_rows.startswith("No rejected")
        else f"| Reason | Count |\n|---|---:|\n{rejection_rows}"
    )

    output_path = Path(output_dir) / f"weekly_report_{start_text}_to_{end_text}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Weekly Trading Report — {start_text} to {end_text} (UTC)

**Mode:** Paper mode only
**Safety:** No leverage, no live orders, deterministic risk engine.

## Portfolio

| Metric | Value |
|---|---:|
{_portfolio_equity_line(journal)}

## This week ({start_text} to {end_text})

| Metric | Value |
|---|---:|
{_format_summary_rows(weekly)}

## Top blocked/rejected reasons this week

{rejection_table}

## All time

| Metric | Value |
|---|---:|
{_format_summary_rows(all_time)}

## AI/Risk Note

Paper mode is active. Weekly results are for validation only. Do not move to
live trading until the 30-day validation gate is met.
"""
    output_path.write_text(text, encoding="utf-8")
    return output_path


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/trading_journal.db")
    parser.add_argument("--output-dir", default="logs")
    parser.add_argument("--date", default=None)
    parser.add_argument("--weekly", action="store_true")
    args = parser.parse_args()
    if args.weekly:
        path = generate_weekly_report(TradingJournal(args.db), args.output_dir, args.date)
    else:
        path = generate_daily_report(TradingJournal(args.db), args.output_dir, args.date)
    print(path)


if __name__ == "__main__":
    cli()
