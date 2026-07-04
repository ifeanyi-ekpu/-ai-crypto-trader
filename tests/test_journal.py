from datetime import datetime, timezone

from trader.journal import TradingJournal
from trader.models import RiskDecision, Signal, TradeLog


def test_journal_initializes_and_logs_signal_and_trade(tmp_path):
    db = tmp_path / "journal.db"
    journal = TradingJournal(db)
    journal.initialize()
    signal = Signal(symbol="BTC/USD", side="hold", confidence=0, reason="no setup")
    journal.log_signal(signal)
    journal.log_risk_decision(RiskDecision(approved=False, reason="hold"), symbol="BTC/USD")
    assert journal.count("signals") == 1
    assert journal.count("risk_decisions") == 1


def make_trade(closed_at: datetime, pnl: float) -> TradeLog:
    return TradeLog(
        symbol="BTC/USD",
        side="buy",
        quantity=1,
        entry_price=100,
        exit_price=100 + pnl,
        pnl=pnl,
        reason="take_profit" if pnl > 0 else "stop_loss",
        opened_at=closed_at,
        closed_at=closed_at,
    )


def test_summary_filters_by_day(tmp_path):
    journal = TradingJournal(tmp_path / "journal.db")
    journal.initialize()
    journal.log_trade(make_trade(datetime(2026, 7, 2, 23, 50, tzinfo=timezone.utc), pnl=8))
    journal.log_trade(make_trade(datetime(2026, 7, 3, 0, 10, tzinfo=timezone.utc), pnl=-3))
    journal.log_trade(make_trade(datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc), pnl=5))

    today = journal.summary(day="2026-07-03")
    assert today["trades"] == 2
    assert today["pnl"] == 2
    assert today["wins"] == 1
    assert today["losses"] == 1

    all_time = journal.summary()
    assert all_time["trades"] == 3
    assert all_time["pnl"] == 10
