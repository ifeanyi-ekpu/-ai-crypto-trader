import pandas as pd
import pytest

from trader.indicators import atr
from trader.strategy import TrendBreakoutStrategy


def make_df(closes):
    return pd.DataFrame({
        "open": closes,
        "high": [x + 1 for x in closes],
        "low": [x - 1 for x in closes],
        "close": closes,
        "volume": [1000] * len(closes),
    })


def test_trend_breakout_emits_buy_signal_on_valid_breakout():
    strategy = TrendBreakoutStrategy(fast_ema=3, slow_ema=5, breakout_window=3, atr_period=3)
    entry = make_df([10, 11, 12, 13, 17])
    trend = make_df([10, 11, 12, 13, 14, 15])
    signal = strategy.generate("BTC/USD", entry, trend)
    atr_value = float(atr(entry, period=3).iloc[-1])

    assert signal.side == "buy"
    assert signal.entry_price is not None
    assert signal.stop_loss is not None
    assert signal.take_profit is not None
    assert signal.entry_price - signal.stop_loss == pytest.approx(1.5 * atr_value)
    assert signal.take_profit - signal.entry_price == pytest.approx(3.0 * atr_value)


def test_trend_breakout_holds_when_no_breakout():
    strategy = TrendBreakoutStrategy(fast_ema=3, slow_ema=5, breakout_window=3, atr_period=3)
    entry = make_df([10, 11, 12, 12, 12])
    trend = make_df([10, 11, 12, 13, 14, 15])
    signal = strategy.generate("BTC/USD", entry, trend)
    assert signal.side == "hold"


def test_trend_breakout_uses_configurable_atr_stop_and_target_multiples():
    strategy = TrendBreakoutStrategy(
        fast_ema=3,
        slow_ema=5,
        breakout_window=3,
        atr_period=3,
        stop_atr_multiple=2.25,
        target_atr_multiple=12.0,
    )
    entry = make_df([10, 11, 12, 13, 17])
    trend = make_df([10, 11, 12, 13, 14, 15])

    signal = strategy.generate("BTC/USD", entry, trend)

    atr_value = float(atr(entry, period=3).iloc[-1])
    assert signal.entry_price is not None
    assert signal.stop_loss is not None
    assert signal.take_profit is not None
    stop_distance = signal.entry_price - signal.stop_loss
    target_distance = signal.take_profit - signal.entry_price
    assert stop_distance == pytest.approx(2.25 * atr_value)
    assert target_distance == pytest.approx(12.0 * atr_value)
