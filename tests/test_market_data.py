import pandas as pd

from trader.config import BotConfig
from trader.market_data import CcxtMarketData, build_market_data


class FakeExchange:
    def __init__(self):
        self.calls = []

    def fetch_ohlcv(self, symbol, timeframe="1m", limit=100):
        self.calls.append((symbol, timeframe, limit))
        return [
            [1_700_000_000_000, 100, 105, 99, 104, 10],
            [1_700_000_300_000, 104, 108, 103, 107, 12],
        ]


def test_ccxt_market_data_normalizes_ohlcv_to_dataframe():
    exchange = FakeExchange()
    data = CcxtMarketData(exchange=exchange, entry_timeframe="5m", trend_timeframe="1h", limit=2)

    entry = data.get_entry_candles("BTC/USD")
    trend = data.get_trend_candles("BTC/USD")

    assert list(entry.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert isinstance(entry, pd.DataFrame)
    assert isinstance(trend, pd.DataFrame)
    assert entry.iloc[-1]["close"] == 107
    assert exchange.calls == [("BTC/USD", "5m", 2), ("BTC/USD", "1h", 2)]


def test_build_market_data_returns_ccxt_adapter_for_exchange_name():
    cfg = BotConfig(exchange="kraken")
    data = build_market_data(cfg)
    assert isinstance(data, CcxtMarketData)
    assert data.entry_timeframe == "5m"
    assert data.trend_timeframe == "1h"
