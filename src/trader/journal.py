from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from trader.models import OrderResult, Position, RiskDecision, Signal, TradeLog
from trader.portfolio import PaperPortfolio


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
                CREATE TABLE IF NOT EXISTS portfolio_state (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  starting_equity REAL NOT NULL,
                  equity REAL NOT NULL,
                  daily_realized_pnl REAL NOT NULL,
                  consecutive_losses INTEGER NOT NULL,
                  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS open_positions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  symbol TEXT NOT NULL,
                  side TEXT NOT NULL,
                  quantity REAL NOT NULL,
                  entry_price REAL NOT NULL,
                  stop_loss REAL NOT NULL,
                  take_profit REAL NOT NULL,
                  opened_at TEXT NOT NULL
                );
                """
            )
            self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Add columns introduced after v1; the SQLite file persists across deploys."""
        migrations = {
            "portfolio_state": ("pnl_date", "TEXT"),
            "open_positions": ("entry_candle_ts", "TEXT"),
        }
        for table, (column, column_type) in migrations.items():
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

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

    def summary(self, day: str | None = None) -> dict[str, float | int]:
        trade_filter, trade_args = ("WHERE closed_at LIKE ?", (f"{day}%",)) if day else ("", ())
        decision_filter, decision_args = ("AND ts LIKE ?", (f"{day}%",)) if day else ("", ())
        with self.connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS trades, COALESCE(SUM(pnl), 0) AS pnl FROM trades {trade_filter}", trade_args).fetchone()
            wins = conn.execute(f"SELECT COUNT(*) FROM trades {trade_filter} {'AND' if day else 'WHERE'} pnl > 0", trade_args).fetchone()[0]
            losses = conn.execute(f"SELECT COUNT(*) FROM trades {trade_filter} {'AND' if day else 'WHERE'} pnl < 0", trade_args).fetchone()[0]
            rejected = conn.execute(f"SELECT COUNT(*) FROM risk_decisions WHERE approved = 0 {decision_filter}", decision_args).fetchone()[0]
        return {"trades": int(row["trades"]), "pnl": float(row["pnl"]), "wins": int(wins), "losses": int(losses), "rejected": int(rejected)}

    @staticmethod
    def _today_utc() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def save_portfolio(self, portfolio: PaperPortfolio) -> None:
        self.initialize()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO portfolio_state (id, starting_equity, equity, daily_realized_pnl, consecutive_losses, pnl_date, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                  starting_equity = excluded.starting_equity,
                  equity = excluded.equity,
                  daily_realized_pnl = excluded.daily_realized_pnl,
                  consecutive_losses = excluded.consecutive_losses,
                  pnl_date = excluded.pnl_date,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (portfolio.starting_equity, portfolio.equity, portfolio.daily_realized_pnl, portfolio.consecutive_losses, self._today_utc()),
            )
            conn.execute("DELETE FROM open_positions")
            conn.executemany(
                """
                INSERT INTO open_positions (symbol, side, quantity, entry_price, stop_loss, take_profit, opened_at, entry_candle_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        position.symbol,
                        position.side,
                        position.quantity,
                        position.entry_price,
                        position.stop_loss,
                        position.take_profit,
                        position.opened_at.isoformat(),
                        position.entry_candle_ts.isoformat() if position.entry_candle_ts else None,
                    )
                    for position in portfolio.open_positions
                ],
            )

    def load_portfolio(self, starting_equity: float, fee_pct: float = 0.0, slippage_bps: float = 0.0) -> PaperPortfolio:
        self.initialize()
        portfolio = PaperPortfolio(starting_equity=starting_equity, fee_pct=fee_pct, slippage_bps=slippage_bps)
        with self.connect() as conn:
            state = conn.execute("SELECT * FROM portfolio_state WHERE id = 1").fetchone()
            if state is not None:
                portfolio.starting_equity = float(state["starting_equity"])
                portfolio.equity = float(state["equity"])
                portfolio.consecutive_losses = int(state["consecutive_losses"])
                # The daily loss limit is per UTC day; carry PnL over only within the same day.
                if state["pnl_date"] == self._today_utc():
                    portfolio.daily_realized_pnl = float(state["daily_realized_pnl"])
            rows = conn.execute(
                """
                SELECT symbol, side, quantity, entry_price, stop_loss, take_profit, opened_at, entry_candle_ts
                FROM open_positions
                ORDER BY id
                """
            ).fetchall()
        portfolio.open_positions = [
            Position(
                symbol=row["symbol"],
                side=row["side"],
                quantity=float(row["quantity"]),
                entry_price=float(row["entry_price"]),
                stop_loss=float(row["stop_loss"]),
                take_profit=float(row["take_profit"]),
                opened_at=datetime.fromisoformat(row["opened_at"]),
                entry_candle_ts=datetime.fromisoformat(row["entry_candle_ts"]) if row["entry_candle_ts"] else None,
            )
            for row in rows
        ]
        return portfolio
