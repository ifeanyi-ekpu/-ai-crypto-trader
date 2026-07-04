from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Side = Literal["buy", "sell", "hold"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Signal(BaseModel):
    symbol: str
    side: Side
    confidence: float = Field(ge=0, le=1)
    entry_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    reason: str
    timestamp: datetime = Field(default_factory=utc_now)

    @classmethod
    def hold(cls, symbol: str, reason: str) -> "Signal":
        return cls(symbol=symbol, side="hold", confidence=0, reason=reason)

    @model_validator(mode="after")
    def prices_required_for_trade(self) -> "Signal":
        if self.side in {"buy", "sell"}:
            missing = [name for name in ("entry_price", "stop_loss", "take_profit") if getattr(self, name) is None]
            if missing:
                raise ValueError(f"Trading signal missing required price field(s): {', '.join(missing)}")
            if self.side == "buy" and not (self.stop_loss < self.entry_price < self.take_profit):
                raise ValueError("Buy signal requires stop_loss < entry_price < take_profit")
            if self.side == "sell" and not (self.take_profit < self.entry_price < self.stop_loss):
                raise ValueError("Sell signal requires take_profit < entry_price < stop_loss")
        return self


class RiskDecision(BaseModel):
    approved: bool
    reason: str
    adjusted_quantity: float = 0
    max_loss_usd: float = 0


@dataclass
class PortfolioState:
    equity: float
    daily_realized_pnl: float = 0
    open_positions: int = 0
    consecutive_losses: int = 0


@dataclass
class OrderResult:
    symbol: str
    side: Side
    quantity: float
    price: float | None
    status: Literal["filled", "rejected"]
    reason: str
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class Position:
    symbol: str
    side: Literal["buy", "sell"]
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    opened_at: datetime = field(default_factory=utc_now)
    # Timestamp of the candle the entry was decided on. Exits must only be
    # evaluated on later candles, otherwise the simulation looks ahead.
    entry_candle_ts: datetime | None = None


@dataclass
class TradeLog:
    symbol: str
    side: Literal["buy", "sell"]
    quantity: float
    entry_price: float
    exit_price: float
    pnl: float
    reason: str
    opened_at: datetime
    closed_at: datetime = field(default_factory=utc_now)
