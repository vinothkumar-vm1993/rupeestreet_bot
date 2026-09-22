import sqlite3
import os
import datetime

OLD_DB_PATH = os.path.join(os.path.dirname(__file__), "titan_execution.db")
DB_PATH = os.path.join(os.path.dirname(__file__), "rupeestreet_execution.db")

# Seamless migration of existing portfolio database
if os.path.exists(OLD_DB_PATH) and not os.path.exists(DB_PATH):
    try:
        import shutil
        shutil.copy2(OLD_DB_PATH, DB_PATH)
    except Exception:
        pass

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Active trades table matching RupeeStreet specification
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        ticker TEXT NOT NULL,
        tier TEXT NOT NULL,
        entry_price REAL NOT NULL,
        stop_loss REAL NOT NULL,
        breakeven_trigger REAL NOT NULL,
        target_1 REAL NOT NULL,
        target_2 REAL NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Audit log for sentinel events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sentinel_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        ticker TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()

def add_active_trade(chat_id: int, ticker: str, tier: str, entry_price: float, stop_loss: float, breakeven_trigger: float, target_1: float, target_2: float, quantity: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO active_trades (chat_id, ticker, tier, entry_price, stop_loss, breakeven_trigger, target_1, target_2, quantity, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
    """, (chat_id, ticker.upper(), tier, entry_price, stop_loss, breakeven_trigger, target_1, target_2, quantity))
    conn.commit()
    conn.close()

def get_active_trades():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM active_trades WHERE status IN ('ACTIVE', 'BREAKEVEN', 'BREAKEVEN_LOCKED', 'TARGET_HIT') ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_trade_status_and_stop(trade_id: int, new_stop: float, new_status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE active_trades SET stop_loss=?, status=? WHERE id=?", (new_stop, new_status, trade_id))
    conn.commit()
    conn.close()

def close_trade_auto_sell(trade_id: int, reason_status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE active_trades SET status=? WHERE id=?", (reason_status, trade_id))
    conn.commit()
    conn.close()

def remove_active_trade(trade_id: int) -> bool:
    """Permanently removes a trade from active_trades by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_trades WHERE id=?", (trade_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def remove_active_trade_by_ticker(ticker: str, chat_id: int = None) -> bool:
    """Permanently removes all active trades matching ticker (and optional chat_id)."""
    conn = get_connection()
    cursor = conn.cursor()
    if chat_id:
        cursor.execute("DELETE FROM active_trades WHERE ticker=? AND chat_id=?", (ticker.upper(), chat_id))
    else:
        cursor.execute("DELETE FROM active_trades WHERE ticker=?", (ticker.upper(),))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def remove_all_active_trades(chat_id: int = None) -> int:
    """Removes all active trades (optionally for a specific chat)."""
    conn = get_connection()
    cursor = conn.cursor()
    if chat_id:
        cursor.execute("DELETE FROM active_trades WHERE chat_id=?", (chat_id,))
    else:
        cursor.execute("DELETE FROM active_trades")
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected

def is_trade_tracked(ticker: str, chat_id: int = None) -> bool:
    """Checks if a ticker is currently active in tracked trades."""
    conn = get_connection()
    cursor = conn.cursor()
    if chat_id:
        cursor.execute("SELECT id FROM active_trades WHERE ticker=? AND chat_id=? AND status IN ('ACTIVE', 'BREAKEVEN', 'BREAKEVEN_LOCKED', 'TARGET_HIT')", (ticker.upper(), chat_id))
    else:
        cursor.execute("SELECT id FROM active_trades WHERE ticker=? AND status IN ('ACTIVE', 'BREAKEVEN', 'BREAKEVEN_LOCKED', 'TARGET_HIT')", (ticker.upper(),))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def record_sentinel_event(event_type: str, ticker: str, details: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sentinel_events (event_type, ticker, details) VALUES (?, ?, ?)", (event_type, ticker, details))
    conn.commit()
    conn.close()

# Compatibility wrappers
def get_open_trades():
    trades = get_active_trades()
    for t in trades:
        t["symbol"] = t.get("ticker")
        t["current_stop"] = t.get("stop_loss")
        t["shares"] = t.get("quantity")
    return trades

def add_or_update_trade(symbol: str, tier: str, entry_price: float, initial_stop: float, current_stop: float, target1: float, target2: float, target3: float = 0.0, shares: int = 1, atr: float = 0.0, chat_id: int = 0):
    breakeven_trigger = round(entry_price + 1.2 * max(entry_price - initial_stop, 1.0), 2)
    add_active_trade(
        chat_id=chat_id,
        ticker=symbol,
        tier=tier,
        entry_price=entry_price,
        stop_loss=current_stop,
        breakeven_trigger=breakeven_trigger,
        target_1=target1,
        target_2=target2,
        quantity=shares
    )

def update_trade_runtime(trade_id: int, cmp_price: float, new_stop: float, new_status: str, pnl_pct: float = 0.0, breakeven_triggered: int = 0):
    update_trade_status_and_stop(trade_id, new_stop, new_status)

def close_trade_execution(trade_id: int, reason_status: str):
    close_trade_auto_sell(trade_id, reason_status)

# Initialize immediately
init_db()

