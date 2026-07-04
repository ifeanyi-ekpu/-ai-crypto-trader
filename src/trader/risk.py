from __future__ import annotations

from trader.config import BotConfig
from trader.models import PortfolioState, RiskDecision, Signal


class RiskEngine:
    def __init__(self, config: BotConfig):
        self.config = config

    def evaluate(self, signal: Signal, state: PortfolioState) -> RiskDecision:
        cfg = self.config
        if cfg.kill_switch:
            return RiskDecision(approved=False, reason="Kill switch is enabled")
        if cfg.mode != "paper":
            return RiskDecision(approved=False, reason="Only paper mode is allowed in v1")
        if signal.side == "hold":
            return RiskDecision(approved=False, reason=f"No trade: {signal.reason}")
        if cfg.risk.require_stop_loss and signal.stop_loss is None:
            return RiskDecision(approved=False, reason="Trade rejected: missing stop loss")
        if cfg.risk.require_take_profit and signal.take_profit is None:
            return RiskDecision(approved=False, reason="Trade rejected: missing take profit")
        if state.open_positions >= cfg.risk.max_open_positions:
            return RiskDecision(approved=False, reason="Max open positions reached")
        if state.consecutive_losses >= cfg.risk.max_consecutive_losses:
            return RiskDecision(approved=False, reason="Max consecutive losses reached")

        daily_loss_limit = state.equity * cfg.risk.max_daily_loss_pct / 100
        if state.daily_realized_pnl <= -daily_loss_limit:
            return RiskDecision(approved=False, reason="Daily loss limit reached")

        assert signal.entry_price is not None
        assert signal.stop_loss is not None
        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        if risk_per_unit <= 0:
            return RiskDecision(approved=False, reason="Invalid stop distance")

        max_loss_usd = state.equity * cfg.risk.max_risk_per_trade_pct / 100
        quantity = max_loss_usd / risk_per_unit
        if quantity <= 0:
            return RiskDecision(approved=False, reason="Calculated quantity is zero")

        # Risk-based sizing with a tight stop can ask for more notional than the
        # account holds. A spot exchange would reject that, so cap the position
        # to the equity not already committed to open positions (no leverage).
        available_notional = state.equity - state.open_notional
        if available_notional <= 0:
            return RiskDecision(approved=False, reason="No free equity for a new position")
        if quantity * signal.entry_price > available_notional:
            quantity = available_notional / signal.entry_price
            max_loss_usd = quantity * risk_per_unit

        return RiskDecision(
            approved=True,
            reason="Approved by deterministic risk engine",
            adjusted_quantity=round(quantity, 10),
            max_loss_usd=round(max_loss_usd, 2),
        )
