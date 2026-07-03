import pytest

from trader.models import Signal


def test_signal_requires_stop_loss_for_buy():
    with pytest.raises(ValueError, match="stop_loss"):
        Signal(symbol="BTC/USD", side="buy", confidence=0.8, entry_price=100, take_profit=110, reason="test")


def test_hold_signal_does_not_require_prices():
    signal = Signal.hold("BTC/USD", "no setup")
    assert signal.side == "hold"
    assert signal.reason == "no setup"
