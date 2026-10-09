# ==================== PREDICTIVE SETUP ENGINE (Layer 2.5) ====================
# काम: पहले से बताना कि setup बन रहा है (WATCH → PREPARE → TRIGGER)

import os
import time
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime

from config import (
    SETUP_EXPIRY, MAX_ACTIVE_SETUPS,
    WATCH_DISTANCE_PCT, PREPARE_DISTANCE_PCT,
    MIN_ALERT_GAP,
)
from data_hub import fetch_ohlcv, get_watchlist
from memory import (
    save_setup, get_active_setups, update_setup_state, close_setup,
    log_alert, get_last_alert_time,
)
from analyzer import analyze

log = logging.getLogger(__name__)

# Test mode - अगर True है तो Telegram नहीं भेजेगा, सिर्फ log करेगा
DRY_RUN = False

TELEGRAM_TOKEN = os.environ.get("ASSISTANT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram(message):
    if DRY_RUN:
        log.info(f"[DRY RUN] Would send: {message[:80]}...")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log.error(f"Telegram error: {e}")


# ==================== KEY LEVEL DETECTION ====================
def detect_key_levels(df, lookback=100):
    """Support, Resistance, POC levels detect करो"""
    levels = {'supports': [], 'resistances': [], 'poc': None, 'va_high': None, 'va_low': None}
    if df is None or len(df) < lookback:
        return levels
    
    recent = df.tail(lookback)
    current = float(df['close'].iloc[-1])
    
    swing_highs = recent['high'].nlargest(5).values
    swing_lows = recent['low'].nsmallest(5).values
    
    levels['resistances'] = sorted([float(h) for h in swing_highs if h > current])[:3]
    levels['supports'] = sorted([float(l) for l in swing_lows if l < current], reverse=True)[:3]
    
    try:
        price_min = float(df['low'].min())
        price_max = float(df['high'].max())
        if price_max > price_min:
            bins = np.linspace(price_min, price_max, 101)
            df_vp = df.copy()
            df_vp['bin'] = pd.cut(df_vp['close'], bins=bins, labels=False, include_lowest=True)
            vp = df_vp.groupby('bin')['volume'].sum()
            if len(vp) > 0:
                poc_bin = vp.idxmax()
                poc_price = (bins[int(poc_bin)] + bins[int(poc_bin)+1]) / 2
                levels['poc'] = float(poc_price)
                sorted_vp = vp.sort_values(ascending=False)
                cumsum = sorted_vp.cumsum()
                va_bins = cumsum[cumsum <= sorted_vp.sum() * 0.7].index.tolist()
                if va_bins:
                    levels['va_high'] = float(bins[max(va_bins) + 1])
                    levels['va_low'] = float(bins[min(va_bins)])
    except Exception as e:
        log.debug(f"VP error: {e}")
    
    return levels


# ==================== SETUP CREATION ====================
def try_create_buy_setup(symbol, df, levels, confidence, reason):
    """अगर BUY setup बन सकता है तो बनाओ"""
    current = float(df['close'].iloc[-1])
    candidates = list(levels.get('supports', []))
    poc = levels.get('poc')
    if poc and poc < current:
        candidates.append(poc)
    candidates = sorted(set(candidates), reverse=True)
    
    if not candidates:
        return None
    
    trigger = candidates[0]
    distance_pct = (current - trigger) / current * 100
    
    if distance_pct > WATCH_DISTANCE_PCT or distance_pct < 0:
        return None
    
    entry = trigger * 1.001
    sl = trigger * 0.99
    risk = entry - sl
    tp1 = entry + (risk * 2)
    tp2 = entry + (risk * 4)
    
    setup_id = save_setup(
        symbol=symbol, setup_type='BUY_LIMIT', direction='BUY',
        trigger_level=trigger, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
        confidence=confidence, leverage=15, state='FORMING',
        reason=reason, expiry_sec=SETUP_EXPIRY,
    )
    log.info(f"📝 Created BUY setup for {symbol} @ {trigger:.4f}")
    return setup_id


def try_create_sell_setup(symbol, df, levels, confidence, reason):
    """अगर SELL setup बन सकता है तो बनाओ"""
    current = float(df['close'].iloc[-1])
    candidates = list(levels.get('resistances', []))
    poc = levels.get('poc')
    if poc and poc > current:
        candidates.append(poc)
    candidates = sorted(set(candidates))
    
    if not candidates:
        return None
    
    trigger = candidates[0]
    distance_pct = (trigger - current) / current * 100
    
    if distance_pct > WATCH_DISTANCE_PCT or distance_pct < 0:
        return None
    
    entry = trigger * 0.999
    sl = trigger * 1.01
    risk = sl - entry
    tp1 = entry - (risk * 2)
    tp2 = entry - (risk * 4)
    
    setup_id = save_setup(
        symbol=symbol, setup_type='SELL_LIMIT', direction='SELL',
        trigger_level=trigger, entry=entry, sl=sl, tp1=tp1, tp2=tp2,
        confidence=confidence, leverage=15, state='FORMING',
        reason=reason, expiry_sec=SETUP_EXPIRY,
    )
    log.info(f"📝 Created SELL setup for {symbol} @ {trigger:.4f}")
    return setup_id


# ==================== ALERT FORMATTERS ====================
def format_watch_alert(setup, price):
    distance = abs(price - setup['trigger_level']) / price * 100
    return f"""👀 <b>WATCH: {setup['symbol']}</b>

💰 अभी: <code>{price:.4f}</code>
📍 Level: <code>{setup['trigger_level']:.4f}</code> ({distance:.2f}% दूर)
🎯 Setup: {setup['setup_type']}
📊 Confidence: {setup['confidence']:.0f}%

⏳ तैयार रहो, करीब आ रहा है..."""


def format_prepare_alert(setup, price):
    distance = abs(price - setup['trigger_level']) / price * 100
    return f"""⏳ <b>PREPARE: {setup['symbol']}</b>

💰 अभी: <code>{price:.4f}</code>
📍 Trigger: <code>{setup['trigger_level']:.4f}</code> ({distance:.2f}% दूर!)

🎯 <b>Entry तैयार रखो:</b>
   Entry: <code>{setup['entry']:.4f}</code>
   SL: <code>{setup['stop_loss']:.4f}</code>
   TP1: <code>{setup['target1']:.4f}</code>
   TP2: <code>{setup['target2']:.4f}</code>

📊 Confidence: {setup['confidence']:.0f}%
⚠️ Trigger होते ही लेना।"""


def format_trigger_alert(setup, price):
    risk = abs(setup['entry'] - setup['stop_loss'])
    rr1 = abs(setup['target1'] - setup['entry']) / risk if risk > 0 else 0
    rr2 = abs(setup['target2'] - setup['entry']) / risk if risk > 0 else 0
    return f"""🚨 <b>TRIGGER: {setup['symbol']}</b>

✅ Level तोड़ दिया! अभी {setup['direction']} लो।

💰 <b>Entry:</b> <code>{setup['entry']:.4f}</code>
🛑 <b>Stop Loss:</b> <code>{setup['stop_loss']:.4f}</code>
🎯 <b>TP1:</b> <code>{setup['target1']:.4f}</code> (1:{rr1:.1f})
🎯 <b>TP2:</b> <code>{setup['target2']:.4f}</code> (1:{rr2:.1f})

🎚️ <b>Leverage:</b> {setup['leverage_suggested']}x max
📊 Confidence: {setup['confidence']:.0f}%

💡 <b>कारण:</b> {setup['reason']}

⚠️ Position: Capital का 2% max"""


def format_invalidated_alert(setup, price):
    return f"""❌ <b>{setup['symbol']} Setup Cancel</b>

कारण: कीमत {setup['trigger_level']:.4f} के गलत तरफ चली गई
📍 Current: <code>{price:.4f}</code>

❌ ये setup अब valid नहीं है। Entry मत लो।"""


# ==================== STATE MACHINE ====================
def update_setup_states():
    """सारे active setups check करो और state update करो"""
    alerts_to_send = []
    active_setups = get_active_setups()
    if not active_setups:
        return alerts_to_send
    
    symbols = list(set(s['symbol'] for s in active_setups))
    
    for symbol in symbols:
        df = fetch_ohlcv(symbol, '1m', 10)
        if df is None or len(df) < 2:
            continue
        
        current_price = float(df['close'].iloc[-1])
        
        for setup in active_setups:
            if setup['symbol'] != symbol:
                continue
            
            setup_id = setup['id']
            direction = setup['direction']
            trigger = float(setup['trigger_level'])
            state = setup['state']
            
            if state in ('TRIGGERED', 'CANCELLED', 'INVALIDATED'):
                continue
            
            # Invalidation check
            if direction == 'BUY' and current_price < trigger * 0.98:
                close_setup(setup_id, 'invalidated')
                alerts_to_send.append(('INVALIDATED', setup, current_price))
                continue
            elif direction == 'SELL' and current_price > trigger * 1.02:
                close_setup(setup_id, 'invalidated')
                alerts_to_send.append(('INVALIDATED', setup, current_price))
                continue
            
            # Distance calculation
            if direction == 'BUY':
                distance_pct = (current_price - trigger) / current_price * 100
            else:
                distance_pct = (trigger - current_price) / current_price * 100
            
            if distance_pct < 0:
                distance_pct = 0  # crossed
            
            # State transitions
            if state == 'FORMING' and distance_pct <= WATCH_DISTANCE_PCT:
                update_setup_state(setup_id, 'WATCHING')
                last = get_last_alert_time(symbol, 'WATCH')
                if last is None or (datetime.now() - last).total_seconds() > MIN_ALERT_GAP:
                    log_alert(symbol, 'WATCH', 'watch')
                    alerts_to_send.append(('WATCH', setup, current_price))
            
            elif state == 'WATCHING' and distance_pct <= PREPARE_DISTANCE_PCT:
                update_setup_state(setup_id, 'PREPARING')
                last = get_last_alert_time(symbol, 'PREPARE')
                if last is None or (datetime.now() - last).total_seconds() > MIN_ALERT_GAP:
                    log_alert(symbol, 'PREPARE', 'prepare')
                    alerts_to_send.append(('PREPARE', setup, current_price))
            
            # Trigger check
            if state in ('FORMING', 'WATCHING', 'PREPARING'):
                triggered = False
                if direction == 'BUY' and current_price >= trigger:
                    triggered = True
                elif direction == 'SELL' and current_price <= trigger:
                    triggered = True
                
                if triggered:
                    update_setup_state(setup_id, 'TRIGGERED')
                    close_setup(setup_id, 'triggered')
                    log_alert(symbol, 'TRIGGER', 'trigger')
                    alerts_to_send.append(('TRIGGER', setup, current_price))
    
    return alerts_to_send


# ==================== SCAN FOR NEW SETUPS ====================
def scan_for_setups(max_new=2):
    """Watchlist scan करके नए setups बनाओ"""
    active = get_active_setups()
    if len(active) >= MAX_ACTIVE_SETUPS:
        log.info(f"⏸️ Max {MAX_ACTIVE_SETUPS} active setups. Skipping.")
        return 0
    
    watchlist = get_watchlist()
    created = 0
    
    for symbol in watchlist:
        if any(s['symbol'] == symbol for s in active):
            continue
        if len(active) + created >= MAX_ACTIVE_SETUPS or created >= max_new:
            break
        
        try:
            df = fetch_ohlcv(symbol, '15m', 200)
            if df is None or len(df) < 100:
                continue
            
            result = analyze(symbol)
            if result is None or result.get('verdict') == 'NO_TRADE':
                continue
            if result.get('consensus') is None:
                continue
            
            direction = result['verdict']
            confidence = result['strength']
            reasons = result['consensus'].get('reasons', [])
            reason = ' | '.join(reasons[:3]) if reasons else 'Multi-sector consensus'
            
            levels = detect_key_levels(df)
            
            if direction == 'BUY':
                sid = try_create_buy_setup(symbol, df, levels, confidence, reason)
            else:
                sid = try_create_sell_setup(symbol, df, levels, confidence, reason)
            
            if sid:
                created += 1
        except Exception as e:
            log.debug(f"Scan error {symbol}: {e}")
    
    return created


# ==================== MAIN LOOP ====================
def main_loop(scan_interval=300, monitor_interval=30):
    """Continuous loop: हर 5 मिनट scan, हर 30 सेकंड monitor"""
    log.info("🚀 Predictive Engine starting...")
    last_scan = 0
    
    while True:
        try:
            now = time.time()
            
            if now - last_scan >= scan_interval:
                active = get_active_setups()
                log.info(f"🔍 Scanning... (active: {len(active)})")
                created = scan_for_setups()
                if created:
                    log.info(f"✅ Created {created} new setup(s)")
                last_scan = now
            
            alerts = update_setup_states()
            for atype, setup, price in alerts:
                if atype == 'WATCH':
                    msg = format_watch_alert(setup, price)
                elif atype == 'PREPARE':
                    msg = format_prepare_alert(setup, price)
                elif atype == 'TRIGGER':
                    msg = format_trigger_alert(setup, price)
                elif atype == 'INVALIDATED':
                    msg = format_invalidated_alert(setup, price)
                else:
                    continue
                send_telegram(msg)
                log.info(f"📤 Sent {atype} for {setup['symbol']}")
            
            time.sleep(monitor_interval)
        except KeyboardInterrupt:
            log.info("Stopped.")
            break
        except Exception as e:
            log.error(f"Loop error: {e}")
            time.sleep(60)


# ==================== TEST ====================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
    DRY_RUN = True  # Test में Telegram नहीं भेजेंगे
    
    print("=" * 60)
    print("🧪 PREDICTIVE ENGINE TEST")
    print("=" * 60)
    
    # Test 1: Key levels
    print("\n1. Key level detection (BTC)...")
    df = fetch_ohlcv('BTC/USDT', '15m', 200)
    if df is not None:
        levels = detect_key_levels(df)
        print(f"   POC: {levels['poc']}")
        print(f"   Supports: {[f'{s:.2f}' for s in levels['supports']]}")
        print(f"   Resistances: {[f'{r:.2f}' for r in levels['resistances']]}")
        print(f"   VA High: {levels['va_high']}")
        print(f"   VA Low: {levels['va_low']}")
    
    # Test 2: Scan for setups
    print("\n2. Scanning for new setups (may take 1-2 min)...")
    created = scan_for_setups(max_new=1)
    print(f"   Created: {created} setup(s)")
    
    active = get_active_setups()
    print(f"   Active setups: {len(active)}")
    for s in active:
        print(f"   - {s['symbol']} {s['setup_type']} @ {s['trigger_level']:.4f} [{s['state']}]")
    
    # Test 3: Monitor once
    print("\n3. Monitoring active setups...")
    alerts = update_setup_states()
    print(f"   Alerts generated: {len(alerts)}")
    for atype, setup, price in alerts:
        print(f"   - {atype}: {setup['symbol']} @ {price:.4f}")
    
    print("\n✅ Predictive Engine test complete!")