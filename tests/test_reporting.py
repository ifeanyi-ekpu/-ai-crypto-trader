from datetime import datetime, timezone

from trader.journal import TradingJournal
from trader.models import Position, TradeLog
from trader.portfolio import PaperPortfolio
from trader.reporting import generate_daily_report


def test_generate_daily_report_creates_markdown(tmp_path):
    db = tmp_path / "journal.db"
    journal = TradingJournal(db)
    journal.initialize()
    report_path = generate_daily_report(journal, output_dir=tmp_path, day="2026-07-03")
    text = report_path.read_text()
    assert "Daily Trading Report" in text
    assert "Paper mode" in text


def test_report_shows_equity_positions_and_day_filtered_stats(tmp_path):
    journal = TradingJournal(tmp_path / "journal.db")
    journal.initialize()

    portfolio = PaperPortfolio(starting_equity=10_000)
    portfolio.equity = 10_250
    portfolio.open_positions.append(
        Position(symbol="ETH/USD", side="buy", quantity=0.5, entry_price=2000, stop_loss=1900, take_profit=2200)
    )
    journal.save_portfolio(portfolio)

    journal.log_trade(
        TradeLog(
            symbol="BTC/USD",
            side="buy",
            quantity=1,
            entry_price=100,
            exit_price=90,
            pnl=-10,
            reason="stop_loss",
            opened_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
            closed_at=datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc),
        )
    )

    text = generate_daily_report(journal, output_dir=tmp_path, day="2026-07-03").read_text()
    assert "$10,250.00" in text
    assert "+2.50%" in text
    assert "ETH/USD" in text
    assert "## Today (2026-07-03 UTC)" in text
    assert "## All time" in text
    # The July 2 trade is in the all-time section but not in today's section.
    today_section = text.split("## Today")[1].split("## All time")[0]
    assert "| Closed trades | 0 |" in today_section
