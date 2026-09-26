import ccxt
import pandas as pd
import numpy as np
import requests
import time
import os
from smartmoneyconcepts import smc

print("--- 🤖 स्मार्ट मनी मल्टी-एक्सचेंज बॉट शुरू हो रहा है... ---")

# ✅ टोकन अब GitHub Secrets से आएगा
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 🌍 सभी बड़े अंतरराष्ट्रीय एक्सचेंजों की लिस्ट
EXCHANGES = ['binance', 'coinbase', 'bitget', 'kraken', 'okx', 
             'bybit', 'kucoin', 'gate', 'htx']

last_alert_time = {}

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram अलर्ट भेजा गया!")
        else:
            print(f"❌ Telegram एरर: {response.text}")
    except Exception as e:
        print(f"❌ Telegram दिक्कत: {e}")

def get_all_usdt_pairs():
    """किसी भी उपलब्ध एक्सचेंज से सभी USDT पेयर लोड करो"""
    for exchange_id in EXCHANGES:
        try:
            exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
            markets = exchange.load_markets()
            # सिर्फ USDT पेयर फ़िल्टर करो
            usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT')]
            if usdt_pairs:
                print(f"✅ {exchange_id} से {len(usdt_pairs)} USDT पेयर मिले।")
                return exchange_id, usdt_pairs
        except Exception as e:
            print(f"⚠️ {exchange_id} से पेयर लोड नहीं हुए: {e}")
            continue
    return None, []

def get_crypto_data(symbol, timeframe='5m', limit=200):
    """किसी भी उपलब्ध एक्सचेंज से डेटा लाने की कोशिश करो (Fallback)"""
    for exchange_id in EXCHANGES:
        try:
            exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            continue # अगर इस एक्सचेंज में नहीं मिला, तो अगला ट्राई करो
    return None

def calculate_all_signals(df, symbol):
    """किसी एक कॉइन का एनालिसिस करके सिग्नल निकालो"""
    if df is None or len(df) < 100:
        return None

    df['ema_25'] = df['close'].ewm(span=25, adjust=False).mean()
    df['ema_45'] = df['close'].ewm(span=45, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['bb_ma'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_ma'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_ma'] - (df['bb_std'] * 2)

    last = df.iloc[-1]
    prev = df.iloc[-2]
    signals = []

    if prev['ema_25'] <= prev['ema_45'] and last['ema_25'] > last['ema_45']:
        signals.append('TREND_BULL')
    elif prev['ema_25'] >= prev['ema_45'] and last['ema_25'] < last['ema_45']:
        signals.append('TREND_BEAR')

    last_rsi = last['rsi']
    if last_rsi > 55: signals.append('RSI_BULL')
    elif last_rsi < 45: signals.append('RSI_BEAR')

    if len(df) > 20:
        price_change = df['close'].diff(20)
        if price_change.iloc[-1] < 0 and df['close'].iloc[-1] > df['close'].iloc[-2]:
            signals.append('CVD_BULL_DIV')
        elif price_change.iloc[-1] > 0 and df['close'].iloc[-1] < df['close'].iloc[-2]:
            signals.append('CVD_BEAR_DIV')

    bb_width = (df['bb_upper'] - df['bb_lower']) / df['bb_ma']
    if bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1] * 0.8:
        signals.append('BB_SQUEEZE')

    high_diff = df['high'].diff()
    low_diff = -df['low'].diff()
    if high_diff.iloc[-1] > 0 and low_diff.iloc[-1] < 0:
        signals.append('ADX_STRONG')

    try:
        df_1h = get_crypto_data(symbol, '1h', 50)
        if df_1h is not None:
            ema_1h = df_1h['close'].ewm(span=20, adjust=False).mean()
            if df_1h['close'].iloc[-1] > ema_1h.iloc[-1]: signals.append('MTF_1H_BULL')
            else: signals.append('MTF_1H_BEAR')
    except: pass

    df_smc = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df_smc.columns = ['open', 'high', 'low', 'close', 'volume']
    
    try:
        swing = smc.swing_highs_lows(df_smc, swing_length=10)
        bos_choch = smc.bos_choch(df_smc, swing, close_break=True)
        if bos_choch['BOS'].iloc[-1] == 1 or bos_choch['CHOCH'].iloc[-1] == 1: signals.append('SMC_BULL')
        elif bos_choch['BOS'].iloc[-1] == -1 or bos_choch['CHOCH'].iloc[-1] == -1: signals.append('SMC_BEAR')
    except: pass

    try:
        fvg = smc.fvg(df_smc, join_consecutive=False)
        if fvg['FVG'].iloc[-1] == 1: signals.append('FVG_BULL')
        elif fvg['FVG'].iloc[-1] == -1: signals.append('FVG_BEAR')
    except: pass

    bull_count = sum(1 for s in signals if 'BULL' in s)
    bear_count = sum(1 for s in signals if 'BEAR' in s)

    if bull_count >= 4:
        return {"type": "SIGNAL", "action": "BUY 🟢", "symbol": symbol, "price": last['close'], "rsi": last_rsi, "score": f"{bull_count}/7", "signals": signals}
    elif bear_count >= 4:
        return {"type": "SIGNAL", "action": "SELL 🔴", "symbol": symbol, "price": last['close'], "rsi": last_rsi, "score": f"{bear_count}/7", "signals": signals}
    elif (bull_count == 3 or bear_count == 3) and 45 < last_rsi < 55:
        trend = "BULLISH 📈" if bull_count > bear_count else "BEARISH 📉"
        return {"type": "PREPARE", "action": "तैयार रहो ⏳", "symbol": symbol, "price": last['close'], "trend": trend, "rsi": last_rsi, "signals": signals}
    return None

if __name__ == "__main__":
    # 🧪 टेस्ट मैसेज (सिर्फ एक बार, शुरू में)
    send_telegram_alert("🧪 नया मल्टी-एक्सचेंज बॉट शुरू हो गया है!")

    # 1. किसी भी उपलब्ध एक्सचेंज से सभी USDT पेयर लोड करो
    best_exchange, all_pairs = get_all_usdt_pairs()
    
    if not all_pairs:
        print("❌ कोई भी एक्सचेंज अभी काम नहीं कर रहा। बॉट बंद हो रहा है।")
    else:
        print(f"✅ {best_exchange} से डेटा लिया जाएगा। कुल {len(all_pairs)} कॉइन्स स्कैन होंगे।")

        # 2. स्कैन शुरू करो (GitHub Actions की समय सीमा के अंदर)
        start_time = time.time()
        scan_count = 0
        
        while time.time() - start_time < 270:  # 4.5 मिनट
            signals_found = False
            
            for coin in all_pairs:
                if time.time() - start_time > 270:
                    break
                
                df = get_crypto_data(coin)
                result = calculate_all_signals(df, coin) if df is not None else None
                
                if result:
                    current_time = time.time()
                    alert_key = f"{result['symbol']}_{result['action']}"
                    
                    # स्पैम चेक (30 मिनट का कूलडाउन)
                    if alert_key not in last_alert_time or (current_time - last_alert_time[alert_key] > 1800):
                        last_alert_time[alert_key] = current_time
                        signals_found = True
                        
                        if result['type'] == "SIGNAL":
                            message = f"🚨 <b>{result['action']} SIGNAL</b> 🚨\n<b>कॉइन:</b> {result['symbol']}\n<b>कीमत:</b> {result['price']:.6f}\n<b>RSI:</b> {result['rsi']:.2f}\n<b>कॉन्फ्लुएंस स्कोर:</b> {result['score']}\n<b>मैच हुए सिग्नल:</b> {', '.join(result['signals'])}"
                            send_telegram_alert(message)
                            
                        elif result['type'] == "PREPARE":
                            message = f"⏳ <b>तैयार रहो!</b> ⏳\n<b>कॉइन:</b> {result['symbol']}\n<b>कीमत:</b> {result['price']:.6f}\n<b>ट्रेंड:</b> {result['trend']}"
                            send_telegram_alert(message)
                            
                time.sleep(0.2)  # रेट लिमिट से बचने के लिए
                scan_count += 1
            
            if not signals_found:
                print(f"⏳ स्कैन पूरा हुआ। 30 सेकंड बाद फिर स्कैन करेंगे...")
                
            time.sleep(30)
        
        print(f"✅ स्कैन पूरा हुआ। कुल {scan_count} कॉइन्स स्कैन किए गए।")
