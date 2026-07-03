from __future__ import annotations

from trader.models import RiskDecision, Signal


def explain_decision(signal: Signal, decision: RiskDecision) -> str:
    """Safe placeholder for AI analysis. No trade authority lives here."""
    if signal.side == "hold":
        return f"AI note: no setup for {signal.symbol}. Reason: {signal.reason}."
    status = "accepted" if decision.approved else "rejected"
    return (
        f"AI note: {signal.symbol} {signal.side} signal was {status}. "
        f"Signal reason: {signal.reason}. Risk decision: {decision.reason}. "
        "The deterministic risk engine remains the authority."
    )
