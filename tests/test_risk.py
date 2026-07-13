import pytest

from trader.config import BotConfig, ExecutionConfig
from trader.models import PortfolioState, Signal
from trader.risk import RiskEngine


def valid_signal():
    return Signal(symbol="BTC/USD", side="buy", confidence=0.8, entry_price=100, stop_loss=95, take_profit=115, reason="breakout")


def test_risk_rejects_when_kill_switch_on():
    cfg = BotConfig(kill_switch=True)
    decision = RiskEngine(cfg).evaluate(valid_signal(), PortfolioState(equity=10000))
    assert decision.approved is False
    assert "kill switch" in decision.reason.lower()


def test_risk_rejects_after_daily_loss_limit():
    cfg = BotConfig()
    state = PortfolioState(equity=10000, daily_realized_pnl=-151)
    decision = RiskEngine(cfg).evaluate(valid_signal(), state)
    assert decision.approved is False
    assert "daily loss" in decision.reason.lower()


def test_risk_approves_valid_trade_and_sizes_quantity():
    cfg = BotConfig()
    decision = RiskEngine(cfg).evaluate(valid_signal(), PortfolioState(equity=10000))
    assert decision.approved is True
    assert decision.adjusted_quantity == pytest.approx(4.2535019081)
    assert decision.max_loss_usd == 25


def test_risk_rejects_after_max_consecutive_losses():
    cfg = BotConfig()
    state = PortfolioState(equity=10000, consecutive_losses=3)
    decision = RiskEngine(cfg).evaluate(valid_signal(), state)
    assert decision.approved is False
    assert "consecutive" in decision.reason.lower()


def test_risk_caps_position_notional_at_equity_no_leverage():
    # Tight stop: gross stop sizing alone would ask for 250 units, but net-risk
    # sizing includes fees/slippage so the honest quantity is much smaller.
    cfg = BotConfig()
    tight_stop = Signal(symbol="BTC/USD", side="buy", confidence=0.8, entry_price=100, stop_loss=99.9, take_profit=103, reason="breakout")
    decision = RiskEngine(cfg).evaluate(tight_stop, PortfolioState(equity=10000))
    assert decision.approved is True
    assert decision.adjusted_quantity == pytest.approx(25.0112500603)
    assert decision.adjusted_quantity * 100 <= 10000
    assert decision.max_loss_usd == 25


def test_risk_counts_open_positions_against_available_equity():
    cfg = BotConfig(risk={"max_open_positions": 2})
    state = PortfolioState(equity=10000, open_positions=1, open_notional=9800)
    decision = RiskEngine(cfg).evaluate(valid_signal(), state)
    assert decision.approved is True
    assert decision.adjusted_quantity == pytest.approx(1.9990004998)  # only $200 of equity is still free after entry slippage
    state_fully_invested = PortfolioState(equity=10000, open_positions=1, open_notional=10000)
    decision = RiskEngine(cfg).evaluate(valid_signal(), state_fully_invested)
    assert decision.approved is False
    assert "free equity" in decision.reason.lower()


def test_risk_rejects_trade_where_take_profit_does_not_clear_costs():
    cfg = BotConfig(execution=ExecutionConfig(fee_pct=0.4, slippage_bps=5))
    tiny_target = Signal(symbol="BTC/USD", side="buy", confidence=0.8, entry_price=100, stop_loss=99, take_profit=100.3, reason="breakout")

    decision = RiskEngine(cfg).evaluate(tiny_target, PortfolioState(equity=10000))

    assert decision.approved is False
    assert "net reward" in decision.reason.lower()


def test_risk_requires_net_reward_to_be_at_least_twice_net_risk():
    cfg = BotConfig(execution=ExecutionConfig(fee_pct=0.4, slippage_bps=5))
    weak_reward = Signal(symbol="BTC/USD", side="buy", confidence=0.8, entry_price=100, stop_loss=95, take_profit=110, reason="breakout")

    decision = RiskEngine(cfg).evaluate(weak_reward, PortfolioState(equity=10000))

    assert decision.approved is False
    assert "reward/risk" in decision.reason.lower()


def test_risk_sizes_quantity_using_net_stop_risk_after_costs():
    cfg = BotConfig(execution=ExecutionConfig(fee_pct=0.4, slippage_bps=5))

    decision = RiskEngine(cfg).evaluate(valid_signal(), PortfolioState(equity=10000))

    assert decision.approved is True
    assert decision.adjusted_quantity == pytest.approx(4.2535019081)
    assert decision.max_loss_usd == 25
