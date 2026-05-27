"""SQLite Database Layer for Trade Journal & Position Tracking."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import threading

from config import config
from logger import logger


class TradeDatabase:
    """Thread-safe SQLite database for trades and positions."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self._lock = threading.Lock()
        self._init_tables()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tables(self) -> None:
        """Initialize database schema."""
        with self._lock, self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    side TEXT NOT NULL,
                    exit_time TEXT,
                    exit_price REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    status TEXT DEFAULT 'OPEN',
                    order_type TEXT,
                    product TEXT,
                    risk REAL,
                    target REAL,
                    setup TEXT,
                    notes TEXT,
                    paper INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER,
                    order_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL,
                    order_type TEXT,
                    status TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(trade_id) REFERENCES trades(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("✅ Database tables initialized")
    
    def add_trade(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        side: str,
        order_type: str = "MARKET",
        product: str = "MIS",
        risk: float = 0,
        target: float = 0,
        setup: str = "",
        notes: str = "",
        paper: bool = False
    ) -> int:
        """Add a new trade. Returns trade_id."""
        with self._lock, self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO trades
                   (symbol, entry_time, entry_price, quantity, side, order_type, product, risk, target, setup, notes, paper)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (symbol, datetime.now().isoformat(), entry_price, quantity, side, order_type, product, risk, target, setup, notes, int(paper))
            )
            conn.commit()
            trade_id = cursor.lastrowid
            logger.info(f"✅ Trade added: {symbol} #{trade_id}")
            return trade_id
    
    def close_trade(self, trade_id: int, exit_price: float) -> None:
        """Close a trade and calculate P&L."""
        with self._lock, self._get_conn() as conn:
            trade = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
            if not trade:
                logger.error(f"Trade #{trade_id} not found")
                return
            
            qty = trade['quantity']
            entry_px = trade['entry_price']
            side = trade['side']
            
            # Calculate P&L
            if side == "BUY":
                pnl = (exit_price - entry_px) * qty
            else:
                pnl = (entry_px - exit_price) * qty
            
            pnl_pct = (pnl / (entry_px * qty)) * 100 if entry_px > 0 else 0
            
            conn.execute(
                """UPDATE trades 
                   SET exit_time = ?, exit_price = ?, pnl = ?, pnl_pct = ?, status = 'CLOSED'
                   WHERE id = ?""",
                (datetime.now().isoformat(), exit_price, pnl, pnl_pct, trade_id)
            )
            conn.commit()
            logger.info(f"✅ Trade closed: {trade['symbol']} #{trade_id} | P&L: ₹{pnl:.2f} ({pnl_pct:.2f}%)")
    
    def add_order(self, trade_id: int, order_id: str, symbol: str, side: str, quantity: int, price: float, order_type: str, status: str = "PENDING") -> None:
        """Log an order."""
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """INSERT INTO orders (trade_id, order_id, symbol, side, quantity, price, order_type, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (trade_id, order_id, symbol, side, quantity, price, order_type, status)
            )
            conn.commit()
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open trades."""
        with self._lock, self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY entry_time DESC").fetchall()
            return [dict(row) for row in rows]
    
    def get_closed_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent closed trades."""
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'CLOSED' ORDER BY exit_time DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    def get_trade_stats(self) -> Dict:
        """Get trading statistics."""
        with self._lock, self._get_conn() as conn:
            stats = conn.execute(
                """SELECT 
                     COUNT(*) as total,
                     SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                     SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                     SUM(pnl) as total_pnl
                   FROM trades WHERE status = 'CLOSED'"""
            ).fetchone()
            
            total = stats['total'] or 0
            wins = stats['wins'] or 0
            losses = stats['losses'] or 0
            total_pnl = stats['total_pnl'] or 0
            
            win_rate = (wins / total * 100) if total > 0 else 0
            
            return {
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
            }
    
    def get_daily_loss(self, date: str = None) -> float:
        """Get today's total loss (for daily loss limit check)."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self._lock, self._get_conn() as conn:
            result = conn.execute(
                """SELECT SUM(pnl) as loss FROM trades 
                   WHERE status = 'CLOSED' 
                   AND DATE(exit_time) = ?
                   AND pnl < 0""",
                (date,)
            ).fetchone()
            
            loss = result['loss'] or 0.0
            return abs(loss)


# Singleton instance
_db_instance: Optional[TradeDatabase] = None


def get_database() -> TradeDatabase:
    """Get or create database singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradeDatabase()
    return _db_instance
