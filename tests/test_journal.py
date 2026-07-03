from trader.journal import TradingJournal
from trader.models import RiskDecision, Signal


def test_journal_initializes_and_logs_signal_and_trade(tmp_path):
    db = tmp_path / "journal.db"
    journal = TradingJournal(db)
    journal.initialize()
    signal = Signal(symbol="BTC/USD", side="hold", confidence=0, reason="no setup")
    journal.log_signal(signal)
    journal.log_risk_decision(RiskDecision(approved=False, reason="hold"), symbol="BTC/USD")
    assert journal.count("signals") == 1
    assert journal.count("risk_decisions") == 1
