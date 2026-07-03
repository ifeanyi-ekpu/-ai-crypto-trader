import pandas as pd

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
    assert signal.side == "buy"
    assert signal.stop_loss < signal.entry_price
    assert signal.take_profit > signal.entry_price


def test_trend_breakout_holds_when_no_breakout():
    strategy = TrendBreakoutStrategy(fast_ema=3, slow_ema=5, breakout_window=3, atr_period=3)
    entry = make_df([10, 11, 12, 12, 12])
    trend = make_df([10, 11, 12, 13, 14, 15])
    signal = strategy.generate("BTC/USD", entry, trend)
    assert signal.side == "hold"
