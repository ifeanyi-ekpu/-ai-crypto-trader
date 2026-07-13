from __future__ import annotations

from trader.config import BotConfig
from trader.models import PortfolioState, RiskDecision, Signal


class RiskEngine:
    def __init__(self, config: BotConfig):
        self.config = config

    def _slipped_price(self, price: float, side: str) -> float:
        slippage = self.config.execution.slippage_bps / 10_000
        return price * (1 + slippage) if side == "buy" else price * (1 - slippage)

    def _net_reward_and_risk_per_unit(self, signal: Signal) -> tuple[float, float]:
        assert signal.entry_price is not None
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
        fee_rate = self.config.execution.fee_pct / 100

        entry_fill = self._slipped_price(signal.entry_price, signal.side)
        if signal.side == "buy":
            target_exit = signal.take_profit
            stop_exit = self._slipped_price(signal.stop_loss, "sell")
            gross_reward = target_exit - entry_fill
            gross_risk = entry_fill - stop_exit
        else:
            target_exit = signal.take_profit
            stop_exit = self._slipped_price(signal.stop_loss, "buy")
            gross_reward = entry_fill - target_exit
            gross_risk = stop_exit - entry_fill

        reward_fees = (entry_fill + target_exit) * fee_rate
        risk_fees = (entry_fill + stop_exit) * fee_rate
        net_reward = gross_reward - reward_fees
        net_risk = gross_risk + risk_fees
        return net_reward, net_risk

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
        assert signal.take_profit is not None
        net_reward_per_unit, net_risk_per_unit = self._net_reward_and_risk_per_unit(signal)
        if net_reward_per_unit <= 0:
            return RiskDecision(approved=False, reason="Trade rejected: expected net reward after fees/slippage is not positive")
        if net_risk_per_unit <= 0:
            return RiskDecision(approved=False, reason="Invalid net risk after fees/slippage")
        reward_risk_ratio = net_reward_per_unit / net_risk_per_unit
        if reward_risk_ratio < cfg.risk.min_net_reward_risk_ratio:
            return RiskDecision(
                approved=False,
                reason=f"Trade rejected: net reward/risk {reward_risk_ratio:.2f} below minimum {cfg.risk.min_net_reward_risk_ratio:.2f}",
            )

        gross_stop_distance = abs(signal.entry_price - signal.stop_loss)
        if gross_stop_distance <= 0:
            return RiskDecision(approved=False, reason="Invalid stop distance")

        max_loss_usd = state.equity * cfg.risk.max_risk_per_trade_pct / 100
        quantity = max_loss_usd / net_risk_per_unit
        if quantity <= 0:
            return RiskDecision(approved=False, reason="Calculated quantity is zero")

        # Risk-based sizing with a tight stop can ask for more notional than the
        # account holds. A spot exchange would reject that, so cap the position
        # to the equity not already committed to open positions (no leverage).
        entry_fill = self._slipped_price(signal.entry_price, signal.side)
        available_notional = state.equity - state.open_notional
        if available_notional <= 0:
            return RiskDecision(approved=False, reason="No free equity for a new position")
        if quantity * entry_fill > available_notional:
            quantity = available_notional / entry_fill
            max_loss_usd = quantity * net_risk_per_unit

        return RiskDecision(
            approved=True,
            reason="Approved by deterministic risk engine",
            adjusted_quantity=round(quantity, 10),
            max_loss_usd=round(max_loss_usd, 2),
        )
