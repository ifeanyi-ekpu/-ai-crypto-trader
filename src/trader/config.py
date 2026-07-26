from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class RiskConfig(BaseModel):
    max_risk_per_trade_pct: float = Field(default=0.25, gt=0)
    max_daily_loss_pct: float = Field(default=1.5, gt=0)
    max_open_positions: int = Field(default=1, ge=1)
    max_consecutive_losses: int = Field(default=3, ge=1)
    min_net_reward_risk_ratio: float = Field(default=2.0, gt=0)
    require_stop_loss: bool = True
    require_take_profit: bool = True
    allow_leverage: bool = False


class StrategyConfig(BaseModel):
    name: str = "trend_breakout"
    entry_timeframe: str = "5m"
    trend_timeframe: str = "1h"
    fast_ema: int = Field(default=20, ge=1)
    slow_ema: int = Field(default=50, ge=2)
    breakout_window: int = Field(default=20, ge=2)
    atr_period: int = Field(default=14, ge=2)
    stop_atr_multiple: float = Field(default=1.5, gt=0)
    target_atr_multiple: float = Field(default=3.0, gt=0)


class ExecutionConfig(BaseModel):
    """Simulated execution costs so paper results stay close to reality."""

    fee_pct: float = Field(default=0.4, ge=0)  # per-side taker fee, in percent
    slippage_bps: float = Field(default=5, ge=0)  # applied against us on entry and stop exits


class AIConfig(BaseModel):
    enabled: bool = True
    provider: str = "ollama"
    model: str = "qwen3:8b"


class BotConfig(BaseModel):
    mode: Literal["paper", "live"] = "paper"
    kill_switch: bool = False
    exchange: str = "local_sample"
    symbols: list[str] = Field(default_factory=lambda: ["BTC/USD", "ETH/USD", "SOL/USD"])
    paper_equity_usd: float = Field(default=10_000, gt=0)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    ai: AIConfig = Field(default_factory=AIConfig)

    @property
    def trading_enabled(self) -> bool:
        return self.mode == "paper" and not self.kill_switch

    @model_validator(mode="after")
    def live_trading_is_not_allowed_in_v1(self) -> "BotConfig":
        if self.mode == "live":
            raise ValueError("Live trading is disabled in v1. Paper trading must be validated first.")
        if self.risk.allow_leverage:
            raise ValueError("Leverage is disabled in v1.")
        return self


def load_config(path: str | Path) -> BotConfig:
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return BotConfig.model_validate(data)
