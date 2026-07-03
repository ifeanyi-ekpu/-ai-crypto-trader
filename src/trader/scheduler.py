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
            signal = strategy.generate(symbol, entry, trend)
            self.journal.log_signal(signal)
            decision = risk_engine.evaluate(signal, self.portfolio.state())
            self.journal.log_risk_decision(decision, symbol)
            order = self.portfolio.execute(signal, decision)
            self.journal.log_order(order)
            latest = entry.iloc[-1]
            for trade in self.portfolio.update_market(symbol, high=float(latest["high"]), low=float(latest["low"]), close=float(latest["close"])):
                self.journal.log_trade(trade)


def run_loop(runner: BotRunner, interval_seconds: int = 300) -> None:
    while True:
        runner.run_once()
        time.sleep(interval_seconds)
