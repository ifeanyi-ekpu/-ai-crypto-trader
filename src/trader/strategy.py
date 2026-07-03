from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trader.indicators import atr, breakout_high, ema
from trader.models import Signal


@dataclass
class TrendBreakoutStrategy:
    fast_ema: int = 20
    slow_ema: int = 50
    breakout_window: int = 20
    atr_period: int = 14
    minimum_atr: float = 0.000001

    def generate(self, symbol: str, entry_candles: pd.DataFrame, trend_candles: pd.DataFrame) -> Signal:
        required_entry = max(self.breakout_window + 1, self.atr_period)
        required_trend = self.slow_ema
        if len(entry_candles) < required_entry:
            return Signal.hold(symbol, "not enough entry candles")
        if len(trend_candles) < required_trend:
            return Signal.hold(symbol, "not enough trend candles")

        trend_fast = ema(trend_candles["close"], self.fast_ema).iloc[-1]
        trend_slow = ema(trend_candles["close"], self.slow_ema).iloc[-1]
        if pd.isna(trend_fast) or pd.isna(trend_slow) or trend_fast <= trend_slow:
            return Signal.hold(symbol, "1h trend filter is not bullish")

        entry_price = float(entry_candles["close"].iloc[-1])
        prior_high = breakout_high(entry_candles["high"], self.breakout_window).iloc[-1]
        if pd.isna(prior_high) or entry_price <= float(prior_high):
            return Signal.hold(symbol, "no breakout above recent high")

        atr_value = atr(entry_candles, self.atr_period).iloc[-1]
        if pd.isna(atr_value) or float(atr_value) <= self.minimum_atr:
            return Signal.hold(symbol, "ATR unavailable or too low")

        risk_distance = 1.5 * float(atr_value)
        stop_loss = entry_price - risk_distance
        take_profit = entry_price + (2.0 * risk_distance)
        return Signal(
            symbol=symbol,
            side="buy",
            confidence=0.70,
            entry_price=entry_price,
            stop_loss=round(stop_loss, 8),
            take_profit=round(take_profit, 8),
            reason="bullish trend breakout with ATR-based stop and target",
        )
