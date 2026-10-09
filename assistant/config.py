# ==================== CONFIG v7.0 ====================

# Fixed watchlist (हमेशा track होंगे)
FIXED_WATCHLIST = [
    'BTC/USDT',
    'PAXG/USDT',   # Gold
    'XAUT/USDT',   # Gold
]

# Auto top coins (volume के हिसाब से)
AUTO_TOP_COUNT = 10

# ⚠️ Stablecoins blacklist (इनका कोई signal नहीं बनेगा)
STABLECOIN_BLACKLIST = [
    'USDC/USDT', 'USDT/USDT', 'DAI/USDT', 'BUSD/USDT',
    'TUSD/USDT', 'FDUSD/USDT', 'USDP/USDT', 'USTC/USDT',
    'USDD/USDT', 'FRAX/USDT', 'PYUSD/USDT', 'USD1/USDT',
    'EURT/USDT', 'USDE/USDT', 'USDS/USDT', 'GUSD/USDT',
]

# Multi-Timeframe settings
TIMEFRAMES = {
    'quick': '1m',        # Fast detection
    'confirm': '15m',     # Confirmation
    'filter': '1h',       # Final filter
}

# Scan intervals (सेकंड में)
SCAN_INTERVAL_FAST = 60        # 1 मिनट — quick detect
SCAN_INTERVAL_NORMAL = 300     # 5 मिनट — full analysis
SETUP_MONITOR_INTERVAL = 30    # 30 सेकंड — active setups monitor
WATCHLIST_REFRESH = 3600       # 1 घंटा — top 10 refresh

# Alert cooldowns
ALERT_COOLDOWN = 7200          # 2 घंटे — same coin same signal
MIN_ALERT_GAP = 900            # 15 मिनट — same coin any alert

# Setup Engine
SETUP_EXPIRY = 3600            # 1 घंटा — setup valid time
MAX_ACTIVE_SETUPS = 5
WATCH_DISTANCE_PCT = 1.0       # 1% दूर हो तो WATCH alert
PREPARE_DISTANCE_PCT = 0.2     # 0.2% दूर हो तो PREPARE alert

# Leverage
MAX_LEVERAGE = 50
DEFAULT_LEVERAGE = 15
MIN_CONFIDENCE_FOR_LEVERAGE = 65

# Risk Management
DEFAULT_RISK_PCT = 2.0         # 2% per trade
DRAWDOWN_DAILY_LIMIT = 5.0     # 5% दिन में loss → pause
DRAWDOWN_WEEKLY_LIMIT = 10.0   # 10% हफ्ते में → aggressive block
CONSECUTIVE_LOSS_LIMIT = 3     # 3 losses → size आधा

# Sector Weights (Hedge Fund v5.0)
SECTOR_WEIGHTS = {
    'macro': 25,
    'structure': 30,
    'flow': 25,
    'quant': 20,
}

# Analysis
MIN_CANDLES = 300
MIN_CONFIDENCE = 60            # कम से कम 60% confidence
MIN_AGENTS_AGREEING = 3        # 4 sectors में से 3 agree करें

# Trading Concepts (Knowledge Base loading)
KNOWLEDGE_BASE_FILE = 'knowledge_base.json'
STRATEGIES_FILE = 'strategies.json'

# Database
DB_PATH = 'assistant_memory.db'

# Cache durations (सेकंड में)
CACHE_TICKERS = 60
CACHE_OHLCV = 300
CACHE_COINLIST = 3600
CACHE_FEAR_GREED = 3600
CACHE_NEWS = 900

# News
NEWS_IMPACT_KEYWORDS = ['FOMC', 'CPI', 'NFP', 'GDP', 'ETF', 'SEC', 'HACK', 'BAN', 'RATE']
NEWS_BLOCK_MINUTES = 30        # Event से 30 मिनट पहले और बाद

# Voice
VOICE_LANGUAGE = 'hi'
VOICE_ENABLED = True

# Timezone
TIMEZONE = 'Asia/Kolkata'

# Logging
LOG_LEVEL = 'INFO'