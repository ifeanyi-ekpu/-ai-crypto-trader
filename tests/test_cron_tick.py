from datetime import datetime, timezone

import pytest

from trader.config import BotConfig
from trader.cron_tick import build_event_message, run_tick
from trader.journal import TradingJournal
from trader.models import Position
from trader.portfolio import PaperPortfolio


def test_build_event_message_returns_none_when_no_important_event():
    before = {"filled_orders": 0, "trades": 0, "rejected": 3}
    after = {"filled_orders": 0, "trades": 0, "rejected": 6}

    assert build_event_message(before, after) is None


def test_build_event_message_reports_filled_order():
    before = {"filled_orders": 0, "trades": 0, "rejected": 0}
    after = {"filled_orders": 1, "trades": 0, "rejected": 2}

    message = build_event_message(before, after)

    assert message is not None
    assert "Paper trading event" in message
    assert "New filled paper orders: 1" in message


def test_build_event_message_reports_closed_trade():
    before = {"filled_orders": 1, "trades": 0, "rejected": 0}
    after = {"filled_orders": 1, "trades": 1, "rejected": 0}

    message = build_event_message(before, after)

    assert message is not None
    assert "New closed paper trades: 1" in message


def test_run_tick_reuses_and_saves_persistent_portfolio_state(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("mode: paper\nexchange: local_sample\nsymbols: []\npaper_equity_usd: 1000\n")
    db_path = tmp_path / "journal.db"
    original = PaperPortfolio(starting_equity=1000)
    original.equity = 990
    original.open_positions.append(
        Position(
            symbol="BTC/USD",
            side="buy",
            quantity=0.1,
            entry_price=100,
            stop_loss=95,
            take_profit=110,
            opened_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
        )
    )
    TradingJournal(db_path).save_portfolio(original)

    class FakeRunner:
        def __init__(self, config: BotConfig, journal: TradingJournal, portfolio: PaperPortfolio):
            self.portfolio = portfolio

        def run_once(self):
            assert self.portfolio.equity == 990
            assert len(self.portfolio.open_positions) == 1
            self.portfolio.equity = 995

    monkeypatch.setattr("trader.cron_tick.BotRunner", FakeRunner)

    run_tick(str(config_path), str(db_path))

    restored = TradingJournal(db_path).load_portfolio(starting_equity=1000)
    assert restored.equity == 995
    assert len(restored.open_positions) == 1


def test_run_tick_saves_state_even_when_run_fails(tmp_path, monkeypatch):
    # Trades are journaled as they close during a run. If a later symbol then
    # fails, the portfolio must still be saved; reloading stale state would
    # re-close the same positions and double-count their PnL.
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("mode: paper\nexchange: local_sample\nsymbols: []\npaper_equity_usd: 1000\n")
    db_path = tmp_path / "journal.db"

    class FailingRunner:
        def __init__(self, config: BotConfig, journal: TradingJournal, portfolio: PaperPortfolio):
            self.portfolio = portfolio

        def run_once(self):
            self.portfolio.equity = 970  # a trade closed before the failure
            raise ConnectionError("exchange unreachable on second symbol")

    monkeypatch.setattr("trader.cron_tick.BotRunner", FailingRunner)

    with pytest.raises(ConnectionError):
        run_tick(str(config_path), str(db_path))

    restored = TradingJournal(db_path).load_portfolio(starting_equity=1000)
    assert restored.equity == 970
