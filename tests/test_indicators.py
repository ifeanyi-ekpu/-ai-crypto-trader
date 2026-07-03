import pandas as pd

from trader.indicators import atr, breakout_high, ema, sma


def test_sma_returns_expected_values():
    s = pd.Series([1, 2, 3, 4])
    result = sma(s, 3)
    assert result.iloc[-1] == 3


def test_ema_returns_series_same_length():
    s = pd.Series([1, 2, 3, 4])
    result = ema(s, 3)
    assert len(result) == 4
    assert result.iloc[-1] > result.iloc[0]


def test_atr_is_positive_when_candles_have_range():
    df = pd.DataFrame({"high": [11, 12, 13], "low": [9, 10, 11], "close": [10, 11, 12]})
    result = atr(df, 2)
    assert result.iloc[-1] > 0


def test_breakout_high_excludes_current_candle_to_avoid_lookahead():
    highs = pd.Series([10, 11, 12, 99])
    result = breakout_high(highs, 3)
    assert result.iloc[-1] == 12
