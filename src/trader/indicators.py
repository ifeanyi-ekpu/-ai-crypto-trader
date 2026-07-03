from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    high = candles["high"]
    low = candles["low"]
    close = candles["close"]
    previous_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def breakout_high(highs: pd.Series, window: int) -> pd.Series:
    # Shift first so the current candle cannot influence its own breakout level.
    return highs.shift(1).rolling(window=window, min_periods=window).max()


def breakout_low(lows: pd.Series, window: int) -> pd.Series:
    return lows.shift(1).rolling(window=window, min_periods=window).min()
