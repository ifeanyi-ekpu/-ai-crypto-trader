from trader.journal import TradingJournal
from trader.reporting import generate_daily_report


def test_generate_daily_report_creates_markdown(tmp_path):
    db = tmp_path / "journal.db"
    journal = TradingJournal(db)
    journal.initialize()
    report_path = generate_daily_report(journal, output_dir=tmp_path, day="2026-07-03")
    text = report_path.read_text()
    assert "Daily Trading Report" in text
    assert "Paper mode" in text
