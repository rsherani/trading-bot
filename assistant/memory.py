# ==================== MEMORY (Layer 5) ====================
# काम: SQLite database — सब कुछ save और recall

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from config import DB_PATH

log = logging.getLogger(__name__)

# ==================== INIT ====================
def init_db():
    """सारी tables बनाओ"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Conversations
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, user_msg TEXT, bot_reply TEXT,
        intent TEXT, symbols TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 2. User preferences
    c.execute('''CREATE TABLE IF NOT EXISTS preferences (
        key TEXT PRIMARY KEY, value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 3. Pending setups
    c.execute('''CREATE TABLE IF NOT EXISTS pending_setups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, setup_type TEXT, direction TEXT,
        trigger_level REAL, entry REAL, stop_loss REAL,
        target1 REAL, target2 REAL,
        confidence REAL, leverage_suggested INTEGER,
        state TEXT, reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME,
        trigger_time DATETIME,
        status TEXT DEFAULT 'active'
    )''')
    
    # 4. Trade journal
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, direction TEXT,
        entry REAL, sl REAL, tp1 REAL, tp2 REAL,
        leverage INTEGER, size REAL,
        status TEXT DEFAULT 'open',
        setup_id INTEGER,
        opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        closed_at DATETIME,
        exit_price REAL,
        pnl_pct REAL,
        pnl_abs REAL,
        notes TEXT
    )''')
    
    # 5. Alerts log
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, alert_type TEXT,
        message TEXT,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 6. Learning/feedback
    c.execute('''CREATE TABLE IF NOT EXISTS learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, concept TEXT,
        explanation TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 7. Performance tracking
    c.execute('''CREATE TABLE IF NOT EXISTS performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE,
        total_signals INTEGER,
        wins INTEGER,
        losses INTEGER,
        expired INTEGER,
        total_pnl REAL,
        notes TEXT
    )''')
    
    conn.commit()
    conn.close()
    log.info("✅ Database initialized")

# ==================== CONVERSATIONS ====================
def save_conversation(user_id, user_msg, bot_reply, intent='', symbols=''):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO conversations 
        (user_id, user_msg, bot_reply, intent, symbols)
        VALUES (?, ?, ?, ?, ?)""",
        (user_id, user_msg, bot_reply[:1000], intent, symbols))
    conn.commit()
    conn.close()

def get_recent_conversations(user_id, limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT user_msg, bot_reply, intent, symbols 
        FROM conversations WHERE user_id=? 
        ORDER BY id DESC LIMIT ?""", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_last_symbol(user_id):
    """पिछली बातचीत का last symbol निकालो"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT symbols FROM conversations 
        WHERE user_id=? AND symbols != '' 
        ORDER BY id DESC LIMIT 1""", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ==================== PREFERENCES ====================
def set_preference(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO preferences 
        (key, value, updated_at) VALUES (?, ?, ?)""",
        (key, str(value), datetime.now()))
    conn.commit()
    conn.close()

def get_preference(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM preferences WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except:
            return row[0]
    return default

# ==================== PENDING SETUPS ====================
def save_setup(symbol, setup_type, direction, trigger_level, entry, sl, tp1, tp2,
               confidence, leverage, state, reason, expiry_sec=3600):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    expires = datetime.now() + timedelta(seconds=expiry_sec)
    c.execute("""INSERT INTO pending_setups 
        (symbol, setup_type, direction, trigger_level, entry, stop_loss, target1, target2,
         confidence, leverage_suggested, state, reason, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (symbol, setup_type, direction, trigger_level, entry, sl, tp1, tp2,
         confidence, leverage, state, reason, expires))
    setup_id = c.lastrowid
    conn.commit()
    conn.close()
    return setup_id

def get_active_setups():
    """सारे active setups जो expire नहीं हुए"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT * FROM pending_setups 
        WHERE status='active' AND expires_at > ? 
        ORDER BY created_at DESC""", (datetime.now(),))
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return rows

def update_setup_state(setup_id, state):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE pending_setups SET state=? WHERE id=?", (state, setup_id))
    conn.commit()
    conn.close()

def close_setup(setup_id, status='cancelled'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE pending_setups SET status=? WHERE id=?", (status, setup_id))
    conn.commit()
    conn.close()

# ==================== TRADES ====================
def open_trade(symbol, direction, entry, sl, tp1, tp2, leverage, size, setup_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO trades 
        (symbol, direction, entry, sl, tp1, tp2, leverage, size, setup_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (symbol, direction, entry, sl, tp1, tp2, leverage, size, setup_id))
    trade_id = c.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def close_trade(trade_id, exit_price, notes=''):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT entry, direction, leverage FROM trades WHERE id=?", (trade_id,))
    row = c.fetchone()
    if row:
        entry, direction, lev = row
        if direction == 'BUY':
            pnl_pct = (exit_price - entry) / entry * 100 * lev
        else:
            pnl_pct = (entry - exit_price) / entry * 100 * lev
        c.execute("""UPDATE trades SET status='closed', closed_at=?, 
            exit_price=?, pnl_pct=?, notes=? WHERE id=?""",
            (datetime.now(), exit_price, pnl_pct, notes, trade_id))
    conn.commit()
    conn.close()

def get_open_trades():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE status='open' ORDER BY opened_at DESC")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return rows

def get_trade_history(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT * FROM trades WHERE status='closed' 
        ORDER BY closed_at DESC LIMIT ?""", (limit,))
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return rows

# ==================== ALERTS ====================
def log_alert(symbol, alert_type, message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO alerts (symbol, alert_type, message) VALUES (?, ?, ?)",
        (symbol, alert_type, message[:500]))
    conn.commit()
    conn.close()

def get_last_alert_time(symbol, alert_type=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if alert_type:
        c.execute("""SELECT sent_at FROM alerts 
            WHERE symbol=? AND alert_type=? 
            ORDER BY id DESC LIMIT 1""", (symbol, alert_type))
    else:
        c.execute("""SELECT sent_at FROM alerts 
            WHERE symbol=? ORDER BY id DESC LIMIT 1""", (symbol,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return datetime.fromisoformat(row[0])
        except:
            return None
    return None

# ==================== LEARNING ====================
def save_learning(user_id, concept, explanation):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO learning (user_id, concept, explanation) 
        VALUES (?, ?, ?)""", (user_id, concept, explanation[:2000]))
    conn.commit()
    conn.close()

# ==================== STATS ====================
def get_weekly_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    week_ago = datetime.now() - timedelta(days=7)
    
    # Alert counts
    c.execute("""SELECT alert_type, COUNT(*) FROM alerts 
        WHERE sent_at > ? GROUP BY alert_type""", (week_ago,))
    alerts = dict(c.fetchall())
    
    # Trade stats
    c.execute("""SELECT COUNT(*), 
        SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END),
        AVG(pnl_pct)
        FROM trades WHERE closed_at > ?""", (week_ago,))
    trade_row = c.fetchone()
    
    conn.close()
    return {
        'alerts': alerts,
        'total_trades': trade_row[0] or 0,
        'wins': trade_row[1] or 0,
        'losses': trade_row[2] or 0,
        'avg_pnl': trade_row[3] or 0,
    }

# ==================== CLEANUP ====================
def cleanup_old_data(days=30):
    """30 दिन से पुराना data हटाओ"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = datetime.now() - timedelta(days=days)
    c.execute("DELETE FROM alerts WHERE sent_at < ?", (cutoff,))
    c.execute("""DELETE FROM pending_setups 
        WHERE status != 'active' AND created_at < ?""", (cutoff,))
    conn.commit()
    conn.close()
    log.info(f"🧹 Cleanup done (older than {days} days)")

# ==================== TEST ====================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 MEMORY MODULE TEST")
    print("=" * 60)
    
    init_db()
    print("✅ DB ready")
    
    # Test conversation
    save_conversation('123', 'BTC कैसा है?', 'BTC अच्छा है', 'analysis', 'BTC')
    recent = get_recent_conversations('123', 3)
    print(f"✅ Recent convs: {len(recent)}")
    
    # Test preference
    set_preference('leverage', 15)
    set_preference('risk_pct', 2.0)
    print(f"✅ Leverage pref: {get_preference('leverage')}")
    
    # Test setup
    setup_id = save_setup('BTC/USDT', 'BUY_LIMIT', 'BUY', 62500, 62510, 61800, 64000, 65500,
                         75, 15, 'FORMING', 'Order Block + CVD Div')
    print(f"✅ Setup saved: ID {setup_id}")
    active = get_active_setups()
    print(f"✅ Active setups: {len(active)}")
    
    # Test stats
    stats = get_weekly_stats()
    print(f"✅ Weekly stats: {stats}")
    
    print("\n✅ Memory module test complete!")