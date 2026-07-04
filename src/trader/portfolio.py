from __future__ import annotations

from datetime import datetime

from trader.models import OrderResult, PortfolioState, Position, RiskDecision, Signal, TradeLog


class PaperPortfolio:
    def __init__(self, starting_equity: float, fee_pct: float = 0.0, slippage_bps: float = 0.0):
        self.starting_equity = starting_equity
        self.equity = starting_equity
        self.fee_pct = fee_pct
        self.slippage_bps = slippage_bps
        self.daily_realized_pnl = 0.0
        self.consecutive_losses = 0
        self.open_positions: list[Position] = []
        self.closed_trades: list[TradeLog] = []

    def _slip(self, price: float, against_side: str) -> float:
        # Slippage always moves the fill against us: buys fill higher, sells fill lower.
        factor = self.slippage_bps / 10_000
        return price * (1 + factor) if against_side == "buy" else price * (1 - factor)

    def state(self) -> PortfolioState:
        return PortfolioState(
            equity=self.equity,
            daily_realized_pnl=self.daily_realized_pnl,
            open_positions=len(self.open_positions),
            consecutive_losses=self.consecutive_losses,
            open_notional=sum(p.entry_price * p.quantity for p in self.open_positions),
        )

    def execute(self, signal: Signal, decision: RiskDecision, entry_candle_ts: datetime | None = None) -> OrderResult:
        if not decision.approved:
            return OrderResult(
                symbol=signal.symbol,
                side=signal.side,
                quantity=0,
                price=signal.entry_price,
                status="rejected",
                reason=decision.reason,
            )
        if signal.side not in {"buy", "sell"}:
            return OrderResult(signal.symbol, signal.side, 0, signal.entry_price, "rejected", "No executable side")
        assert signal.entry_price is not None
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
        fill_price = round(self._slip(signal.entry_price, signal.side), 8)
        position = Position(
            symbol=signal.symbol,
            side=signal.side,
            quantity=decision.adjusted_quantity,
            entry_price=fill_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            entry_candle_ts=entry_candle_ts,
        )
        self.open_positions.append(position)
        return OrderResult(
            symbol=signal.symbol,
            side=signal.side,
            quantity=decision.adjusted_quantity,
            price=fill_price,
            status="filled",
            reason=decision.reason,
        )

    def update_market(
        self,
        symbol: str,
        high: float,
        low: float,
        close: float,
        candle_ts: datetime | None = None,
    ) -> list[TradeLog]:
        closed: list[TradeLog] = []
        remaining: list[Position] = []
        for position in self.open_positions:
            if position.symbol != symbol:
                remaining.append(position)
                continue
            # A candle at or before the entry candle happened before the position
            # existed; using its high/low would let the simulation look ahead.
            opened_on = position.entry_candle_ts or position.opened_at
            if candle_ts is not None and candle_ts <= opened_on:
                remaining.append(position)
                continue
            exit_price: float | None = None
            reason = ""
            if position.side == "buy":
                if low <= position.stop_loss:
                    # Stops fill through the level; targets are limit orders at the level.
                    exit_price = self._slip(position.stop_loss, "sell")
                    reason = "stop_loss"
                elif high >= position.take_profit:
                    exit_price = position.take_profit
                    reason = "take_profit"
                pnl = 0.0 if exit_price is None else (exit_price - position.entry_price) * position.quantity
            else:
                if high >= position.stop_loss:
                    exit_price = self._slip(position.stop_loss, "buy")
                    reason = "stop_loss"
                elif low <= position.take_profit:
                    exit_price = position.take_profit
                    reason = "take_profit"
                pnl = 0.0 if exit_price is None else (position.entry_price - exit_price) * position.quantity

            if exit_price is None:
                remaining.append(position)
                continue

            fees = (position.entry_price + exit_price) * position.quantity * self.fee_pct / 100
            trade = TradeLog(
                symbol=position.symbol,
                side=position.side,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=round(exit_price, 8),
                pnl=round(pnl - fees, 8),
                reason=reason,
                opened_at=position.opened_at,
            )
            self.equity = round(self.equity + trade.pnl, 8)
            self.daily_realized_pnl = round(self.daily_realized_pnl + trade.pnl, 8)
            self.consecutive_losses = self.consecutive_losses + 1 if trade.pnl < 0 else 0
            self.closed_trades.append(trade)
            closed.append(trade)
        self.open_positions = remaining
        return closed
