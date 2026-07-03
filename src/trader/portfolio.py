from __future__ import annotations

from trader.models import OrderResult, PortfolioState, Position, RiskDecision, Signal, TradeLog


class PaperPortfolio:
    def __init__(self, starting_equity: float):
        self.starting_equity = starting_equity
        self.equity = starting_equity
        self.daily_realized_pnl = 0.0
        self.consecutive_losses = 0
        self.open_positions: list[Position] = []
        self.closed_trades: list[TradeLog] = []

    def state(self) -> PortfolioState:
        return PortfolioState(
            equity=self.equity,
            daily_realized_pnl=self.daily_realized_pnl,
            open_positions=len(self.open_positions),
            consecutive_losses=self.consecutive_losses,
        )

    def execute(self, signal: Signal, decision: RiskDecision) -> OrderResult:
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
        position = Position(
            symbol=signal.symbol,
            side=signal.side,
            quantity=decision.adjusted_quantity,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )
        self.open_positions.append(position)
        return OrderResult(
            symbol=signal.symbol,
            side=signal.side,
            quantity=decision.adjusted_quantity,
            price=signal.entry_price,
            status="filled",
            reason=decision.reason,
        )

    def update_market(self, symbol: str, high: float, low: float, close: float) -> list[TradeLog]:
        closed: list[TradeLog] = []
        remaining: list[Position] = []
        for position in self.open_positions:
            if position.symbol != symbol:
                remaining.append(position)
                continue
            exit_price: float | None = None
            reason = ""
            if position.side == "buy":
                if low <= position.stop_loss:
                    exit_price = position.stop_loss
                    reason = "stop_loss"
                elif high >= position.take_profit:
                    exit_price = position.take_profit
                    reason = "take_profit"
                pnl = 0.0 if exit_price is None else (exit_price - position.entry_price) * position.quantity
            else:
                if high >= position.stop_loss:
                    exit_price = position.stop_loss
                    reason = "stop_loss"
                elif low <= position.take_profit:
                    exit_price = position.take_profit
                    reason = "take_profit"
                pnl = 0.0 if exit_price is None else (position.entry_price - exit_price) * position.quantity

            if exit_price is None:
                remaining.append(position)
                continue

            trade = TradeLog(
                symbol=position.symbol,
                side=position.side,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=exit_price,
                pnl=round(pnl, 8),
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
