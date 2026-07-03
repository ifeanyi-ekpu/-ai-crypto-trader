from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from trader.journal import TradingJournal


def generate_daily_report(journal: TradingJournal, output_dir: str | Path = "logs", day: str | None = None) -> Path:
    journal.initialize()
    report_day = day or date.today().isoformat()
    summary = journal.summary()
    trades = int(summary["trades"])
    wins = int(summary["wins"])
    losses = int(summary["losses"])
    win_rate = (wins / trades * 100) if trades else 0.0
    output_path = Path(output_dir) / f"daily_report_{report_day}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Daily Trading Report — {report_day}

**Mode:** Paper mode only  
**Safety:** No leverage, no live orders, deterministic risk engine.

## Performance

| Metric | Value |
|---|---:|
| Closed trades | {trades} |
| Wins | {wins} |
| Losses | {losses} |
| Win rate | {win_rate:.2f}% |
| Realized P&L | ${summary['pnl']:.2f} |
| Rejected/blocked signals | {summary['rejected']} |

## AI/Risk Note

Paper mode is active. This report is for monitoring only. Do not move to live trading until the 30-day validation gate is met.
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
