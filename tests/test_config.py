import pytest

from trader.config import BotConfig, load_config


def test_default_config_is_paper_and_no_leverage():
    cfg = BotConfig()
    assert cfg.mode == "paper"
    assert cfg.kill_switch is False
    assert cfg.risk.allow_leverage is False
    assert cfg.risk.max_risk_per_trade_pct == 0.25


def test_load_config_rejects_live_mode_without_explicit_gate(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text("mode: live\n")
    with pytest.raises(ValueError, match="Live trading is disabled"):
        load_config(path)


def test_kill_switch_blocks_trading():
    cfg = BotConfig(kill_switch=True)
    assert cfg.trading_enabled is False
