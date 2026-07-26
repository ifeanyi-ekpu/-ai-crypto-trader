from pathlib import Path

import pytest

from trader.config import BotConfig, load_config


def test_default_config_is_paper_and_no_leverage():
    cfg = BotConfig()
    assert cfg.mode == "paper"
    assert cfg.kill_switch is False
    assert cfg.risk.allow_leverage is False
    assert cfg.risk.max_risk_per_trade_pct == 0.25
    assert cfg.strategy.breakout_window == 20
    assert cfg.strategy.stop_atr_multiple == 1.5
    assert cfg.strategy.target_atr_multiple == 3.0


def test_load_kraken_paper_strategy_calibration():
    config_path = Path(__file__).parents[1] / "config" / "settings.kraken-paper.yaml"

    cfg = load_config(config_path)

    assert cfg.strategy.entry_timeframe == "15m"
    assert cfg.strategy.trend_timeframe == "1h"
    assert cfg.strategy.breakout_window == 20
    assert cfg.strategy.atr_period == 14
    assert cfg.strategy.stop_atr_multiple == 1.5
    assert cfg.strategy.target_atr_multiple == 12.0


def test_load_config_rejects_live_mode_without_explicit_gate(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text("mode: live\n")
    with pytest.raises(ValueError, match="Live trading is disabled"):
        load_config(path)


def test_kill_switch_blocks_trading():
    cfg = BotConfig(kill_switch=True)
    assert cfg.trading_enabled is False
