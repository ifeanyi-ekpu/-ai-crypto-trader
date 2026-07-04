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


def test_portfolio_state_reports_open_notional():
    p = PaperPortfolio(starting_equity=1000)
    assert p.state().open_notional == 0
    p.execute(signal(), decision())  # 2 units at entry 100
    assert p.state().open_notional == 200


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


def test_fees_and_slippage_reduce_pnl():
    # 0.1% fee per side, 10 bps slippage.
    p = PaperPortfolio(starting_equity=1000, fee_pct=0.1, slippage_bps=10)
    order = p.execute(signal(), decision())
    assert order.price == 100.1  # buy entry slips upward against us

    trades = p.update_market("BTC/USD", high=111, low=101, close=110)
    assert len(trades) == 1
    trade = trades[0]
    assert trade.exit_price == 110  # take profit fills at the limit price
    gross = (110 - 100.1) * 2
    fees = (100.1 + 110) * 2 * 0.001
    assert trade.pnl == round(gross - fees, 8)
    assert p.equity == round(1000 + trade.pnl, 8)


def test_stop_loss_exit_slips_against_us():
    p = PaperPortfolio(starting_equity=1000, fee_pct=0, slippage_bps=10)
    p.execute(signal(), decision())
    trades = p.update_market("BTC/USD", high=100, low=94, close=95)
    assert trades[0].reason == "stop_loss"
    assert trades[0].exit_price == 95 * (1 - 0.001)  # stop fills through the level


def test_candle_at_or_before_entry_cannot_close_position():
    p = PaperPortfolio(starting_equity=1000)
    entry_ts = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    p.execute(signal(), decision(), entry_candle_ts=entry_ts)

    # The entry candle itself (and anything older) must not trigger an exit,
    # even though its range spans both the stop and the target.
    same_candle = p.update_market("BTC/USD", high=115, low=90, close=100, candle_ts=entry_ts)
    older_candle = p.update_market("BTC/USD", high=115, low=90, close=100, candle_ts=datetime(2026, 7, 3, 11, 55, tzinfo=timezone.utc))
    assert same_candle == []
    assert older_candle == []
    assert len(p.open_positions) == 1

    later = p.update_market("BTC/USD", high=111, low=100, close=110, candle_ts=datetime(2026, 7, 3, 12, 5, tzinfo=timezone.utc))
    assert len(later) == 1
    assert later[0].reason == "take_profit"


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
            entry_candle_ts=opened_at,
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


def test_daily_pnl_resets_on_new_utc_day(tmp_path):
    portfolio = PaperPortfolio(starting_equity=1000)
    portfolio.equity = 950
    portfolio.daily_realized_pnl = -50
    portfolio.consecutive_losses = 2
    journal = TradingJournal(tmp_path / "state.db")
    journal.save_portfolio(portfolio)

    # Simulate the saved state being from yesterday.
    with journal.connect() as conn:
        conn.execute("UPDATE portfolio_state SET pnl_date = '2020-01-01' WHERE id = 1")

    restored = journal.load_portfolio(starting_equity=1000)
    assert restored.daily_realized_pnl == 0  # daily limit is per UTC day
    assert restored.equity == 950  # equity carries over
    assert restored.consecutive_losses == 2  # loss streak guards the strategy, not the day


def test_journal_migrates_v1_database(tmp_path):
    import sqlite3

    # Build a database with the original v1 schema (no pnl_date / entry_candle_ts).
    db_path = tmp_path / "v1.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE portfolio_state (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          starting_equity REAL NOT NULL,
          equity REAL NOT NULL,
          daily_realized_pnl REAL NOT NULL,
          consecutive_losses INTEGER NOT NULL,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE open_positions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          symbol TEXT NOT NULL,
          side TEXT NOT NULL,
          quantity REAL NOT NULL,
          entry_price REAL NOT NULL,
          stop_loss REAL NOT NULL,
          take_profit REAL NOT NULL,
          opened_at TEXT NOT NULL
        );
        INSERT INTO portfolio_state (id, starting_equity, equity, daily_realized_pnl, consecutive_losses)
        VALUES (1, 1000, 980, -20, 1);
        INSERT INTO open_positions (symbol, side, quantity, entry_price, stop_loss, take_profit, opened_at)
        VALUES ('BTC/USD', 'buy', 0.1, 100, 95, 110, '2026-07-03T10:00:00+00:00');
        """
    )
    conn.commit()
    conn.close()

    journal = TradingJournal(db_path)
    restored = journal.load_portfolio(starting_equity=1000)

    assert restored.equity == 980
    assert restored.daily_realized_pnl == 0  # v1 rows have no pnl_date, so reset
    assert len(restored.open_positions) == 1
    assert restored.open_positions[0].entry_candle_ts is None
    journal.save_portfolio(restored)  # round-trip with the new columns works
