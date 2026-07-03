from __future__ import annotations

import sqlite3
from pathlib import Path

from trader.models import OrderResult, RiskDecision, Signal, TradeLog


class TradingJournal:
    def __init__(self, db_path: str | Path = "data/trading_journal.db"):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS signals (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts TEXT NOT NULL,
                  symbol TEXT NOT NULL,
                  side TEXT NOT NULL,
                  confidence REAL NOT NULL,
                  entry_price REAL,
                  stop_loss REAL,
                  take_profit REAL,
                  reason TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS risk_decisions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts TEXT DEFAULT CURRENT_TIMESTAMP,
                  symbol TEXT NOT NULL,
                  approved INTEGER NOT NULL,
                  reason TEXT NOT NULL,
                  adjusted_quantity REAL NOT NULL,
                  max_loss_usd REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts TEXT NOT NULL,
                  symbol TEXT NOT NULL,
                  side TEXT NOT NULL,
                  quantity REAL NOT NULL,
                  price REAL,
                  status TEXT NOT NULL,
                  reason TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trades (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  opened_at TEXT NOT NULL,
                  closed_at TEXT NOT NULL,
                  symbol TEXT NOT NULL,
                  side TEXT NOT NULL,
                  quantity REAL NOT NULL,
                  entry_price REAL NOT NULL,
                  exit_price REAL NOT NULL,
                  pnl REAL NOT NULL,
                  reason TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS daily_reports (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  day TEXT NOT NULL,
                  path TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def log_signal(self, signal: Signal) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO signals (ts, symbol, side, confidence, entry_price, stop_loss, take_profit, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (signal.timestamp.isoformat(), signal.symbol, signal.side, signal.confidence, signal.entry_price, signal.stop_loss, signal.take_profit, signal.reason),
            )

    def log_risk_decision(self, decision: RiskDecision, symbol: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO risk_decisions (symbol, approved, reason, adjusted_quantity, max_loss_usd) VALUES (?, ?, ?, ?, ?)",
                (symbol, int(decision.approved), decision.reason, decision.adjusted_quantity, decision.max_loss_usd),
            )

    def log_order(self, order: OrderResult) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO orders (ts, symbol, side, quantity, price, status, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (order.timestamp.isoformat(), order.symbol, order.side, order.quantity, order.price, order.status, order.reason),
            )

    def log_trade(self, trade: TradeLog) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO trades (opened_at, closed_at, symbol, side, quantity, entry_price, exit_price, pnl, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (trade.opened_at.isoformat(), trade.closed_at.isoformat(), trade.symbol, trade.side, trade.quantity, trade.entry_price, trade.exit_price, trade.pnl, trade.reason),
            )

    def count(self, table: str) -> int:
        if table not in {"signals", "risk_decisions", "orders", "trades", "daily_reports"}:
            raise ValueError("Unsupported table")
        with self.connect() as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def summary(self) -> dict[str, float | int]:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS trades, COALESCE(SUM(pnl), 0) AS pnl FROM trades").fetchone()
            wins = conn.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0").fetchone()[0]
            losses = conn.execute("SELECT COUNT(*) FROM trades WHERE pnl < 0").fetchone()[0]
            rejected = conn.execute("SELECT COUNT(*) FROM risk_decisions WHERE approved = 0").fetchone()[0]
        return {"trades": int(row["trades"]), "pnl": float(row["pnl"]), "wins": int(wins), "losses": int(losses), "rejected": int(rejected)}
