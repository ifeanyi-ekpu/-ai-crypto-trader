from datetime import datetime, timezone

from trader.journal import TradingJournal
from trader.models import Position, RiskDecision, Signal
from trader.portfolio import PaperPortfolio


def signal():
    return Signal(symbol="BTC/USD", side="buy", confidence=0.8, entry_price=100, stop_loss=95, take_profit=110, reason="breakout")


def decision():
    return RiskDecision(approved=True, reason="approved", adjusted_quantity=2, max_loss_usd=10)


def test_portfolio_opens_approved_trade():
    p = PaperPortfolio(starting_equity=1000)
    order = p.execute(signal(), decision())
    assert order.status == "filled"
    assert len(p.open_positions) == 1


def test_portfolio_rejects_unapproved_trade():
    p = PaperPortfolio(starting_equity=1000)
    rejected = RiskDecision(approved=False, reason="blocked")
    order = p.execute(signal(), rejected)
    assert order.status == "rejected"
    assert len(p.open_positions) == 0


def test_portfolio_closes_at_take_profit_and_updates_equity():
    p = PaperPortfolio(starting_equity=1000)
    p.execute(signal(), decision())
    trades = p.update_market("BTC/USD", high=111, low=99, close=110)
    assert len(trades) == 1
    assert trades[0].pnl == 20
    assert p.equity == 1020


def test_portfolio_closes_at_stop_loss_and_counts_loss():
    p = PaperPortfolio(starting_equity=1000)
    p.execute(signal(), decision())
    trades = p.update_market("BTC/USD", high=101, low=94, close=95)
    assert trades[0].pnl == -10
    assert p.consecutive_losses == 1


def test_portfolio_state_round_trips_through_journal(tmp_path):
    opened_at = datetime(2026, 7, 4, tzinfo=timezone.utc)
    portfolio = PaperPortfolio(starting_equity=1000)
    portfolio.equity = 990
    portfolio.daily_realized_pnl = -10
    portfolio.consecutive_losses = 1
    portfolio.open_positions.append(
        Position(
            symbol="ETH/USD",
            side="buy",
            quantity=0.5,
            entry_price=2000,
            stop_loss=1900,
            take_profit=2200,
            opened_at=opened_at,
        )
    )
    journal = TradingJournal(tmp_path / "state.db")

    journal.save_portfolio(portfolio)
    restored = journal.load_portfolio(starting_equity=1000)

    assert restored.equity == 990
    assert restored.daily_realized_pnl == -10
    assert restored.consecutive_losses == 1
    assert len(restored.open_positions) == 1
    assert restored.open_positions[0] == portfolio.open_positions[0]
