# ==================== DATA HUB (Layer 1) ====================
# काम: सारा data fetch करना + cache करना

import ccxt
import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import datetime
from config import (
    FIXED_WATCHLIST, AUTO_TOP_COUNT,
    STABLECOIN_BLACKLIST,
    CACHE_TICKERS, CACHE_OHLCV, CACHE_COINLIST,
    CACHE_FEAR_GREED, TIMEZONE,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
log = logging.getLogger(__name__)

# ==================== CACHE ====================
_cache = {}

def _is_cache_valid(key, ttl):
    if key not in _cache:
        return False
    return (time.time() - _cache[key]['time']) < ttl

def _set_cache(key, value):
    _cache[key] = {'value': value, 'time': time.time()}

def _get_cache(key):
    return _cache.get(key, {}).get('value')

# ==================== EXCHANGE ====================
def get_exchange(name='bybit'):
    """Primary exchange handler"""
    return getattr(ccxt, name)({'enableRateLimit': True, 'timeout': 15000})

# ==================== COIN LIST ====================
def get_all_usdt_pairs(exchange_name='binance'):
    """सारे USDT pairs लाओ (cached 1 घंटा)"""
    cache_key = f'coinlist_{exchange_name}'
    if _is_cache_valid(cache_key, CACHE_COINLIST):
        return _get_cache(cache_key)
    
    try:
        ex = get_exchange(exchange_name)
        markets = ex.load_markets()
        pairs = [s for s in markets if s.endswith('/USDT')]
        _set_cache(cache_key, pairs)
        log.info(f"✅ {exchange_name} पर {len(pairs)} USDT pairs मिले")
        return pairs
    except Exception as e:
        log.error(f"❌ Coin list fetch failed ({exchange_name}): {e}")
        if exchange_name != 'bybit':
            return get_all_usdt_pairs('bybit')
        return FIXED_WATCHLIST.copy()

# ==================== TICKERS ====================
def get_tickers(exchange_name='binance'):
    """सारे tickers लाओ (cached 1 मिनट)"""
    cache_key = f'tickers_{exchange_name}'
    if _is_cache_valid(cache_key, CACHE_TICKERS):
        return _get_cache(cache_key)
    
    try:
        ex = get_exchange(exchange_name)
        tickers = ex.fetch_tickers()
        _set_cache(cache_key, tickers)
        return tickers
    except Exception as e:
        log.warning(f"⚠️ Tickers fetch failed ({exchange_name}): {e}")
        if exchange_name != 'bybit':
            return get_tickers('bybit')
        return {}

# ==================== AUTO TOP 10 ====================
def get_top_volume_pairs(count=AUTO_TOP_COUNT, exchange_name='binance'):
    """
    24h volume के हिसाब से top N coins लो
    Stablecoins को filter out किया जाएगा
    """
    try:
        tickers = get_tickers(exchange_name)
        if not tickers:
            return []
        
        all_pairs = get_all_usdt_pairs(exchange_name)
        
        # Filter valid pairs and sort by quoteVolume
        valid = []
        for pair in all_pairs:
            # 🔽 Stablecoins skip करो
            if pair in STABLECOIN_BLACKLIST:
                continue
            t = tickers.get(pair, {})
            vol = t.get('quoteVolume') or 0
            if vol > 0:
                valid.append((pair, vol))
        
        valid.sort(key=lambda x: x[1], reverse=True)
        top = [p[0] for p in valid[:count]]
        log.info(f"✅ Top {len(top)} coins by volume: {top[:5]}...")
        return top
    except Exception as e:
        log.error(f"❌ Top volume fetch error: {e}")
        return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']

# ==================== DYNAMIC WATCHLIST ====================
def get_watchlist():
    """
    Final watchlist = Fixed + Top 10
    Duplicates और Stablecoins हटाकर unique list
    """
    fixed = [c for c in FIXED_WATCHLIST if c not in STABLECOIN_BLACKLIST]
    top = get_top_volume_pairs(AUTO_TOP_COUNT)
    
    watchlist = list(dict.fromkeys(fixed + top))  # preserves order, removes dupes
    log.info(f"📋 Watchlist: {len(watchlist)} coins")
    return watchlist

# ==================== OHLCV ====================
def fetch_ohlcv(symbol, timeframe='15m', limit=300, exchange_name='bybit'):
    """OHLCV data लाओ (cached per timeframe)"""
    cache_key = f'ohlcv_{exchange_name}_{symbol}_{timeframe}_{limit}'
    ttl = 60 if timeframe == '1m' else CACHE_OHLCV
    if _is_cache_valid(cache_key, ttl):
        return _get_cache(cache_key)
    
    # Try primary exchange, then fallback
    for ex_name in [exchange_name, 'binance', 'okx']:
        try:
            ex = get_exchange(ex_name)
            ohlcv = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
            if ohlcv and len(ohlcv) > 20:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                _set_cache(cache_key, df)
                return df
        except Exception as e:
            log.debug(f"OHLCV failed on {ex_name} for {symbol}: {e}")
            continue
    
    return None

def fetch_multi_timeframe(symbol, limit=200):
    """तीनों timeframes का data एक साथ लो"""
    from config import TIMEFRAMES
    result = {}
    for label, tf in TIMEFRAMES.items():
        df = fetch_ohlcv(symbol, tf, limit=limit)
        if df is not None:
            result[label] = df
    return result

# ==================== FUNDING RATE ====================
def fetch_funding_rate(symbol):
    """Futures funding rate (cached 15 मिनट)"""
    cache_key = f'funding_{symbol}'
    if _is_cache_valid(cache_key, 900):
        return _get_cache(cache_key)
    
    try:
        ex = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
        rate = ex.fetch_funding_rate(symbol)
        val = rate.get('fundingRate', 0)
        _set_cache(cache_key, val)
        return val
    except Exception as e:
        return 0

# ==================== OPEN INTEREST ====================
def fetch_open_interest(symbol):
    """Open interest (cached 15 मिनट)"""
    cache_key = f'oi_{symbol}'
    if _is_cache_valid(cache_key, 900):
        return _get_cache(cache_key)
    
    try:
        ex = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
        oi = ex.fetch_open_interest(symbol)
        val = oi.get('openInterestValue', 0)
        _set_cache(cache_key, val)
        return val
    except:
        return 0

# ==================== FEAR & GREED ====================
def fetch_fear_greed():
    """Fear & Greed Index (cached 1 घंटा)"""
    cache_key = 'fear_greed'
    if _is_cache_valid(cache_key, CACHE_FEAR_GREED):
        return _get_cache(cache_key)
    
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        val = int(r.json()['data'][0]['value'])
        _set_cache(cache_key, val)
        return val
    except:
        return None

# ==================== BTC DOMINANCE ====================
def fetch_btc_dominance():
    """BTC dominance (cached 1 घंटा)"""
    cache_key = 'btc_dom'
    if _is_cache_valid(cache_key, 3600):
        return _get_cache(cache_key)
    
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        val = r.json()['data']['market_cap_percentage']['btc']
        _set_cache(cache_key, val)
        return val
    except:
        return 50

# ==================== TEST ====================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 DATA HUB TEST")
    print("=" * 60)
    
    print("\n1. Watchlist load कर रहे हैं...")
    wl = get_watchlist()
    print(f"   Total coins: {len(wl)}")
    print(f"   First 15: {wl[:15]}")
    
    print("\n2. BTC का 15m data...")
    df = fetch_ohlcv('BTC/USDT', '15m', 100)
    if df is not None:
        print(f"   Candles: {len(df)}")
        print(f"   Last close: {df['close'].iloc[-1]:.2f}")
    else:
        print("   ❌ Failed")
    
    print("\n3. Multi-timeframe check...")
    mtf = fetch_multi_timeframe('BTC/USDT')
    for tf, d in mtf.items():
        print(f"   {tf}: {len(d)} candles")
    
    print("\n4. Fear & Greed...")
    fg = fetch_fear_greed()
    print(f"   Value: {fg}")
    
    print("\n5. Funding rate...")
    fr = fetch_funding_rate('BTC/USDT')
    print(f"   Rate: {fr}")
    
    print("\n✅ Test complete!")