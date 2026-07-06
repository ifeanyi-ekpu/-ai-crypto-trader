from datetime import datetime, timezone

import pandas as pd

from trader.config import BotConfig, RiskConfig
from trader.journal import TradingJournal
from trader.models import Position
from trader.portfolio import PaperPortfolio
from trader.scheduler import BotRunner


def make_candles(rows):
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


def ts(minute):
    return pd.Timestamp(datetime(2026, 7, 3, 12, minute, tzinfo=timezone.utc))


class FakeMarketData:
    """Flat, non-breakout candles so no new signal fires; used to test exits."""

    def __init__(self, entry_candles):
        self.entry_candles = entry_candles

    def get_entry_candles(self, symbol):
        return self.entry_candles

    def get_trend_candles(self, symbol):
        return self.entry_candles


def test_run_once_closes_position_on_intermediate_candle(tmp_path, monkeypatch):
    # Position opened on the 12:00 candle. Since the last run, three candles
    # closed; the stop was hit on the middle one (12:10), not the latest.
    candles = make_candles(
        [
            [ts(0), 100, 101, 99, 100, 10],
            [ts(5), 100, 101, 99, 100, 10],
            [ts(10), 100, 100, 94, 96, 10],  # stop (95) hit here
            [ts(15), 96, 97, 95.5, 96, 10],
        ]
    )
    monkeypatch.setattr("trader.scheduler.build_market_data", lambda cfg: FakeMarketData(candles))

    portfolio = PaperPortfolio(starting_equity=1000)
    portfolio.open_positions.append(
        Position(
            symbol="BTC/USD",
            side="buy",
            quantity=1,
            entry_price=100,
            stop_loss=95,
            take_profit=110,
            entry_candle_ts=ts(0).to_pydatetime(),
        )
    )
    config = BotConfig(exchange="local_sample", symbols=["BTC/USD"])
    journal = TradingJournal(tmp_path / "journal.db")
    BotRunner(config=config, journal=journal, portfolio=portfolio).run_once()

    assert len(portfolio.open_positions) == 0
    assert len(portfolio.closed_trades) == 1
    assert portfolio.closed_trades[0].reason == "stop_loss"
    assert journal.count("trades") == 1


def test_run_once_does_not_exit_new_position_on_its_own_entry_candle(tmp_path, monkeypatch):
    # Strong breakout on the last candle whose range also spans the ATR stop
    # and target. The position must open and stay open: its own candle's
    # high/low happened before the entry existed.
    stamps = pd.date_range("2026-07-03 10:00", periods=25, freq="5min", tz="UTC")
    rows = [[stamp, 100, 101, 99, 100, 10] for stamp in stamps[:-1]]
    rows.append([stamps[-1], 100, 140, 80, 130, 50])
    candles = make_candles(rows)

    trend_stamps = pd.date_range("2026-07-01", periods=60, freq="1h", tz="UTC")
    trend = make_candles([[stamp, 100 + i, 101 + i, 99 + i, 100 + i, 10] for i, stamp in enumerate(trend_stamps)])

    class BreakoutData(FakeMarketData):
        def get_trend_candles(self, symbol):
            return trend

    monkeypatch.setattr("trader.scheduler.build_market_data", lambda cfg: BreakoutData(candles))

    portfolio = PaperPortfolio(starting_equity=1000)
    config = BotConfig(exchange="local_sample", symbols=["BTC/USD"], risk=RiskConfig(min_net_reward_risk_ratio=0.1))
    journal = TradingJournal(tmp_path / "journal.db")
    BotRunner(config=config, journal=journal, portfolio=portfolio).run_once()

    assert len(portfolio.open_positions) == 1
    assert portfolio.closed_trades == []
    assert portfolio.open_positions[0].entry_candle_ts == stamps[-1].to_pydatetime()
