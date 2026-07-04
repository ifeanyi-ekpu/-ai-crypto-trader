import pandas as pd
import pytest

from trader.config import BotConfig
from trader.market_data import CcxtMarketData, build_market_data

OHLCV_ROWS = [
    [1_700_000_000_000, 100, 105, 99, 104, 10],
    [1_700_000_300_000, 104, 108, 103, 107, 12],
    [1_700_000_600_000, 107, 109, 106, 108, 7],  # still-forming candle, must be dropped
]


class FakeExchange:
    def __init__(self):
        self.calls = []

    def fetch_ohlcv(self, symbol, timeframe="1m", limit=100):
        self.calls.append((symbol, timeframe, limit))
        return OHLCV_ROWS


class FlakyExchange:
    def __init__(self, failures: int):
        self.failures = failures
        self.attempts = 0

    def fetch_ohlcv(self, symbol, timeframe="1m", limit=100):
        self.attempts += 1
        if self.attempts <= self.failures:
            raise ConnectionError("temporary network failure")
        return OHLCV_ROWS


def test_ccxt_market_data_normalizes_ohlcv_and_drops_forming_candle():
    exchange = FakeExchange()
    data = CcxtMarketData(exchange=exchange, entry_timeframe="5m", trend_timeframe="1h", limit=2)

    entry = data.get_entry_candles("BTC/USD")
    trend = data.get_trend_candles("BTC/USD")

    assert list(entry.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert isinstance(entry, pd.DataFrame)
    assert isinstance(trend, pd.DataFrame)
    # The newest (still-forming) candle is dropped: the last closed candle is exposed.
    assert len(entry) == 2
    assert entry.iloc[-1]["close"] == 107
    # One extra candle is requested to compensate for the dropped forming candle.
    assert exchange.calls == [("BTC/USD", "5m", 3), ("BTC/USD", "1h", 3)]


def test_fetch_retries_transient_network_errors(monkeypatch):
    monkeypatch.setattr("trader.market_data._retryable_errors", lambda: (ConnectionError,))
    monkeypatch.setattr("trader.market_data.time.sleep", lambda _: None)
    exchange = FlakyExchange(failures=2)
    data = CcxtMarketData(exchange=exchange, limit=2)

    entry = data.get_entry_candles("BTC/USD")

    assert exchange.attempts == 3
    assert len(entry) == 2


def test_fetch_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr("trader.market_data._retryable_errors", lambda: (ConnectionError,))
    monkeypatch.setattr("trader.market_data.time.sleep", lambda _: None)
    exchange = FlakyExchange(failures=10)
    data = CcxtMarketData(exchange=exchange, limit=2)

    with pytest.raises(ConnectionError):
        data.get_entry_candles("BTC/USD")
    assert exchange.attempts == 3


def test_build_market_data_returns_ccxt_adapter_for_exchange_name():
    cfg = BotConfig(exchange="kraken")
    data = build_market_data(cfg)
    assert isinstance(data, CcxtMarketData)
    assert data.entry_timeframe == "5m"
    assert data.trend_timeframe == "1h"
