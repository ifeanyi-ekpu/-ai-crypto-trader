from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from trader.config import BotConfig


class MarketDataProvider(Protocol):
    def get_entry_candles(self, symbol: str) -> pd.DataFrame: ...

    def get_trend_candles(self, symbol: str) -> pd.DataFrame: ...


class LocalSampleMarketData:
    """Deterministic sample candles for safe paper-mode smoke tests."""

    def get_entry_candles(self, symbol: str) -> pd.DataFrame:
        base = 100 if symbol.startswith("BTC") else 50 if symbol.startswith("ETH") else 20
        closes = [base + i for i in range(25)] + [base + 32]
        return pd.DataFrame(
            {
                "open": closes,
                "high": [x + 1 for x in closes],
                "low": [x - 1 for x in closes],
                "close": closes,
                "volume": [1000] * len(closes),
            }
        )

    def get_trend_candles(self, symbol: str) -> pd.DataFrame:
        base = 100 if symbol.startswith("BTC") else 50 if symbol.startswith("ETH") else 20
        closes = [base + i * 0.5 for i in range(80)]
        return pd.DataFrame(
            {
                "open": closes,
                "high": [x + 1 for x in closes],
                "low": [x - 1 for x in closes],
                "close": closes,
                "volume": [1000] * len(closes),
            }
        )


@dataclass
class CcxtMarketData:
    """Public candle data adapter. It does not place orders or use API keys."""

    exchange: object
    entry_timeframe: str = "5m"
    trend_timeframe: str = "1h"
    limit: int = 120

    def _fetch(self, symbol: str, timeframe: str) -> pd.DataFrame:
        rows = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=self.limit)
        candles = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        numeric_columns = ["open", "high", "low", "close", "volume"]
        candles[numeric_columns] = candles[numeric_columns].astype(float)
        candles["timestamp"] = pd.to_datetime(candles["timestamp"], unit="ms", utc=True)
        return candles

    def get_entry_candles(self, symbol: str) -> pd.DataFrame:
        return self._fetch(symbol, self.entry_timeframe)

    def get_trend_candles(self, symbol: str) -> pd.DataFrame:
        return self._fetch(symbol, self.trend_timeframe)


def build_market_data(config: BotConfig) -> MarketDataProvider:
    if config.exchange == "local_sample":
        return LocalSampleMarketData()

    import ccxt  # Imported lazily so local tests/sample mode do not require network setup.

    exchange_class = getattr(ccxt, config.exchange, None)
    if exchange_class is None:
        raise ValueError(f"Unsupported ccxt exchange: {config.exchange}")
    exchange = exchange_class({"enableRateLimit": True})
    return CcxtMarketData(
        exchange=exchange,
        entry_timeframe=config.strategy.entry_timeframe,
        trend_timeframe=config.strategy.trend_timeframe,
    )
