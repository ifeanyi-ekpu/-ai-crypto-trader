from __future__ import annotations

import time
from dataclasses import dataclass

from trader.config import BotConfig
from trader.journal import TradingJournal
from trader.market_data import build_market_data
from trader.portfolio import PaperPortfolio
from trader.risk import RiskEngine
from trader.strategy import TrendBreakoutStrategy


@dataclass
class BotRunner:
    config: BotConfig
    journal: TradingJournal
    portfolio: PaperPortfolio

    def run_once(self) -> None:
        self.journal.initialize()
        data = build_market_data(self.config)
        strategy = TrendBreakoutStrategy()
        risk_engine = RiskEngine(self.config)

        for symbol in self.config.symbols:
            entry = data.get_entry_candles(symbol)
            trend = data.get_trend_candles(symbol)

            # Close existing positions first, walking every candle since entry so
            # stops/targets hit between scheduled runs are not missed. Doing this
            # before opening anything new also means a fresh position can never be
            # exited on its own entry candle (which would be look-ahead).
            self._process_exits(symbol, entry)

            signal = strategy.generate(symbol, entry, trend)
            self.journal.log_signal(signal)
            decision = risk_engine.evaluate(signal, self.portfolio.state())
            self.journal.log_risk_decision(decision, symbol)
            order = self.portfolio.execute(signal, decision, entry_candle_ts=self._candle_ts(entry.iloc[-1]))
            self.journal.log_order(order)

    def _process_exits(self, symbol: str, candles) -> None:
        if not any(position.symbol == symbol for position in self.portfolio.open_positions):
            return
        for _, row in candles.iterrows():
            trades = self.portfolio.update_market(
                symbol,
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                candle_ts=self._candle_ts(row),
            )
            for trade in trades:
                self.journal.log_trade(trade)

    @staticmethod
    def _candle_ts(row):
        ts = row.get("timestamp")
        return ts.to_pydatetime() if ts is not None and hasattr(ts, "to_pydatetime") else ts


def run_loop(runner: BotRunner, interval_seconds: int = 300) -> None:
    while True:
        try:
            runner.run_once()
        finally:
            runner.journal.save_portfolio(runner.portfolio)
        time.sleep(interval_seconds)
