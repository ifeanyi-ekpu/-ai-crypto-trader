from trader.config import BotConfig
from trader.models import PortfolioState, Signal
from trader.risk import RiskEngine


def valid_signal():
    return Signal(symbol="BTC/USD", side="buy", confidence=0.8, entry_price=100, stop_loss=95, take_profit=110, reason="breakout")


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
    assert decision.adjusted_quantity == 5
    assert decision.max_loss_usd == 25


def test_risk_rejects_after_max_consecutive_losses():
    cfg = BotConfig()
    state = PortfolioState(equity=10000, consecutive_losses=3)
    decision = RiskEngine(cfg).evaluate(valid_signal(), state)
    assert decision.approved is False
    assert "consecutive" in decision.reason.lower()
