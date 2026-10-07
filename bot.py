import ccxt
import pandas as pd
import numpy as np
import requests
import time
import os
import ta
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score

print("=" * 60)
print("🏛️  INSTITUTIONAL AI TRADING SYSTEM v3.0")
print("=" * 60)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

COINS_TO_SCAN = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
                 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT']

AGENT_WEIGHTS = {
    'market_structure': 20,
    'order_flow': 18,
    'ml_quant': 15,
    'multi_timeframe': 15,
    'trend_momentum': 12,
    'sentiment': 10,
    'market_regime': 10,
}

MIN_CONSENSUS_SCORE = 72
MIN_AGENTS_AGREEING = 4
ALERT_COOLDOWN = 7200

last_alert_time = {}
fear_greed_cache = {'value': None, 'timestamp': 0}

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def fetch_ohlcv(symbol, timeframe='15m', limit=300):
    try:
        exchange = ccxt.bybit({'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except:
        return None

def fetch_funding_rate(symbol):
    try:
        exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
        rate = exchange.fetch_funding_rate(symbol)
        return rate.get('fundingRate', 0)
    except:
        return 0

def fetch_fear_greed():
    global fear_greed_cache
    if time.time() - fear_greed_cache['timestamp'] < 3600:
        return fear_greed_cache['value']
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        value = int(r.json()['data'][0]['value'])
        fear_greed_cache = {'value': value, 'timestamp': time.time()}
        return value
    except:
        return None

# ============ AGENT 1: MARKET REGIME ============
def agent_market_regime(df):
    if df is None or len(df) < 50:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data', 'state': 'UNKNOWN'}
    adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], 14).adx().iloc[-1]
    atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], 14).average_true_range()
    high_max = df['high'].rolling(14).max()
    low_min = df['low'].rolling(14).min()
    chop = (100 * np.log10(atr.rolling(14).sum() / (high_max - low_min)) / np.log10(14)).iloc[-1]
    atr_ratio = atr.iloc[-1] / atr.rolling(50).mean().iloc[-1] if atr.rolling(50).mean().iloc[-1] > 0 else 1

    if adx > 25 and chop < 38:
        state, conf = 'TRENDING', min(90, 50 + (adx - 25) * 2)
    elif adx < 20 and chop > 60:
        state, conf = 'RANGING', min(85, 50 + (chop - 60))
    elif atr_ratio > 1.8:
        state, conf = 'VOLATILE', min(80, 50 + (atr_ratio - 1.8) * 30)
    else:
        state, conf = 'NEUTRAL', 40
    return {'signal': 'NEUTRAL', 'confidence': conf, 'state': state, 'reason': f'ADX:{adx:.1f}, CHOP:{chop:.1f}'}

# ============ AGENT 2: TREND & MOMENTUM ============
def agent_trend_momentum(df):
    if df is None or len(df) < 100:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data'}
    e8 = df['close'].ewm(span=8).mean().iloc[-1]
    e13 = df['close'].ewm(span=13).mean().iloc[-1]
    e21 = df['close'].ewm(span=21).mean().iloc[-1]
    e34 = df['close'].ewm(span=34).mean().iloc[-1]
    e55 = df['close'].ewm(span=55).mean().iloc[-1]
    ribbon_bull = e8 > e13 > e21 > e34 > e55
    ribbon_bear = e8 < e13 < e21 < e34 < e55

    macd_hist = ta.trend.MACD(df['close']).macd_diff()
    macd_bull = macd_hist.iloc[-1] > 0 and macd_hist.iloc[-1] > macd_hist.iloc[-2]
    macd_bear = macd_hist.iloc[-1] < 0 and macd_hist.iloc[-1] < macd_hist.iloc[-2]

    atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], 10).average_true_range()
    hl2 = (df['high'] + df['low']) / 2
    close = df['close'].iloc[-1]
    st_bull = close > (hl2 - 3 * atr).iloc[-1]
    st_bear = close < (hl2 + 3 * atr).iloc[-1]

    bull = sum([ribbon_bull, macd_bull, st_bull])
    bear = sum([ribbon_bear, macd_bear, st_bear])

    if bull >= 2:
        return {'signal': 'BULLISH', 'confidence': 40 + bull * 20, 'reason': f'Ribbon:{ribbon_bull}, MACD:{macd_bull}, ST:{st_bull}'}
    elif bear >= 2:
        return {'signal': 'BEARISH', 'confidence': 40 + bear * 20, 'reason': f'Ribbon:{ribbon_bear}, MACD:{macd_bear}, ST:{st_bear}'}
    return {'signal': 'NEUTRAL', 'confidence': 30, 'reason': 'No trend'}

# ============ AGENT 3: ORDER FLOW ============
def agent_order_flow(df):
    if df is None or len(df) < 50:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data'}
    df = df.copy()
    df['delta'] = np.where(df['close'] > df['open'], df['volume'],
                  np.where(df['close'] < df['open'], -df['volume'], 0))
    df['cvd'] = df['delta'].cumsum()

    price_change = df['close'].iloc[-1] - df['close'].iloc[-20]
    cvd_change = df['cvd'].iloc[-1] - df['cvd'].iloc[-20]
    cvd_bull = price_change < 0 and cvd_change > 0
    cvd_bear = price_change > 0 and cvd_change < 0

    recent = df.tail(10)
    buy_v = recent[recent['close'] > recent['open']]['volume'].sum()
    sell_v = recent[recent['close'] < recent['open']]['volume'].sum()
    total = buy_v + sell_v
    buy_ratio = buy_v / total if total > 0 else 0.5

    if cvd_bull and buy_ratio > 0.55:
        return {'signal': 'BULLISH', 'confidence': min(90, 60 + (buy_ratio - 0.55) * 100), 'reason': f'CVD Bull Div, Buy:{buy_ratio:.2f}'}
    elif cvd_bear and buy_ratio < 0.45:
        return {'signal': 'BEARISH', 'confidence': min(90, 60 + (0.45 - buy_ratio) * 100), 'reason': f'CVD Bear Div, Buy:{buy_ratio:.2f}'}
    return {'signal': 'NEUTRAL', 'confidence': 40, 'reason': 'No flow signal'}

# ============ AGENT 4: MARKET STRUCTURE (SMC) ============
def agent_market_structure(df):
    if df is None or len(df) < 50:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data'}
    lb = 5
    highs = df['high'].rolling(lb*2+1, center=True).max()
    lows = df['low'].rolling(lb*2+1, center=True).min()
    sh = df['high'][df['high'] == highs].dropna()
    sl = df['low'][df['low'] == lows].dropna()
    if len(sh) < 2 or len(sl) < 2:
        return {'signal': 'NEUTRAL', 'confidence': 30, 'reason': 'Few swings'}
    close = df['close'].iloc[-1]
    bos_bull = close > sh.iloc[-1]
    bos_bear = close < sl.iloc[-1]

    rh20 = df['high'].iloc[-20:-1].max()
    rl20 = df['low'].iloc[-20:-1].min()
    sweep_h = df['high'].iloc[-1] > rh20 and close < rh20
    sweep_l = df['low'].iloc[-1] < rl20 and close > rl20

    fvg_bull = df['low'].iloc[-1] > df['high'].iloc[-3]
    fvg_bear = df['high'].iloc[-1] < df['low'].iloc[-3]

    if sweep_l or (bos_bull and fvg_bull):
        conf = 70 + (10 if sweep_l else 0) + (10 if fvg_bull else 0)
        return {'signal': 'BULLISH', 'confidence': min(conf, 95), 'reason': f'Sweep:{sweep_l}, BOS:{bos_bull}, FVG:{fvg_bull}'}
    elif sweep_h or (bos_bear and fvg_bear):
        conf = 70 + (10 if sweep_h else 0) + (10 if fvg_bear else 0)
        return {'signal': 'BEARISH', 'confidence': min(conf, 95), 'reason': f'Sweep:{sweep_h}, BOS:{bos_bear}, FVG:{fvg_bear}'}
    return {'signal': 'NEUTRAL', 'confidence': 40, 'reason': 'No structure'}

# ============ AGENT 5: MULTI-TIMEFRAME ============
def agent_multi_timeframe(symbol):
    signals = []
    weights = {'15m': 0.2, '1h': 0.35, '4h': 0.45}
    for tf in ['15m', '1h', '4h']:
        df = fetch_ohlcv(symbol, tf, 100)
        if df is None or len(df) < 50:
            continue
        e20 = df['close'].ewm(span=20).mean().iloc[-1]
        e50 = df['close'].ewm(span=50).mean().iloc[-1]
        c = df['close'].iloc[-1]
        if c > e20 > e50:
            signals.append(('BULLISH', weights[tf]))
        elif c < e20 < e50:
            signals.append(('BEARISH', weights[tf]))
        else:
            signals.append(('NEUTRAL', weights[tf]))

    if not signals:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No MTF'}
    bw = sum(w for s, w in signals if s == 'BULLISH')
    brw = sum(w for s, w in signals if s == 'BEARISH')
    if bw >= 0.7:
        return {'signal': 'BULLISH', 'confidence': 60 + bw * 30, 'reason': f'MTF {bw*100:.0f}% bullish'}
    elif brw >= 0.7:
        return {'signal': 'BEARISH', 'confidence': 60 + brw * 30, 'reason': f'MTF {brw*100:.0f}% bearish'}
    return {'signal': 'NEUTRAL', 'confidence': 40, 'reason': 'MTF not aligned'}

# ============ AGENT 6: ML QUANT ============
def agent_ml_quant(df):
    if df is None or len(df) < 200:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data'}
    df = df.copy()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], 14).rsi()
    df['macd'] = ta.trend.MACD(df['close']).macd_diff()
    df['ema_20'] = ta.trend.EMAIndicator(df['close'], 20).ema_indicator()
    df['ema_50'] = ta.trend.EMAIndicator(df['close'], 50).ema_indicator()
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], 14).average_true_range()
    df['bb_w'] = ta.volatility.BollingerBands(df['close'], 20).bollinger_wband()
    df['vol_r'] = df['volume'] / df['volume'].rolling(20).mean()
    df['ret'] = df['close'].pct_change()
    df['vol'] = df['ret'].rolling(20).std()
    df['mom'] = df['close'] - df['close'].shift(10)
    df['cvd'] = (df['volume'] * np.sign(df['close'] - df['open'])).cumsum()
    df['cvd_c'] = df['cvd'].diff(5)
    df['ema_d'] = df['ema_20'] - df['ema_50']
    df['rsi_m'] = df['rsi'] - df['rsi'].shift(5)

    feats = ['rsi', 'macd', 'ema_20', 'ema_50', 'atr', 'bb_w', 'vol_r', 'ret',
             'vol', 'mom', 'cvd_c', 'ema_d', 'rsi_m']
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df = df.dropna()
    if len(df) < 100:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'Not enough clean data'}

    X, y = df[feats].values, df['target'].values
    tscv = TimeSeriesSplit(n_splits=3)
    accs = []
    for tr, te in tscv.split(X):
        m = XGBClassifier(n_estimators=80, max_depth=4, learning_rate=0.1, random_state=42, verbosity=0)
        m.fit(X[tr], y[tr])
        accs.append(accuracy_score(y[te], m.predict(X[te])))
    avg_acc = np.mean(accs)

    final = XGBClassifier(n_estimators=80, max_depth=4, learning_rate=0.1, random_state=42, verbosity=0)
    final.fit(X, y)
    proba = final.predict_proba(X[-1:])[0]
    pred = int(final.predict(X[-1:])[0])
    conf = max(proba) * 100

    if avg_acc < 0.55:
        return {'signal': 'NEUTRAL', 'confidence': 30, 'reason': f'Low accuracy: {avg_acc*100:.1f}%'}
    if conf < 62:
        return {'signal': 'NEUTRAL', 'confidence': conf, 'reason': f'Low confidence: {conf:.1f}%'}

    return {'signal': 'BULLISH' if pred == 1 else 'BEARISH', 'confidence': conf,
            'reason': f'ML Acc:{avg_acc*100:.1f}%, Conf:{conf:.1f}%'}

# ============ AGENT 7: SENTIMENT ============
def agent_sentiment(symbol):
    try:
        funding = fetch_funding_rate(symbol)
        fg = fetch_fear_greed()
        sig, conf, reasons = 'NEUTRAL', 40, []
        if funding < -0.0005:
            sig, conf = 'BULLISH', 65
            reasons.append(f'Funding {funding*100:.4f}%')
        elif funding > 0.001:
            sig, conf = 'BEARISH', 65
            reasons.append(f'Funding {funding*100:.4f}%')
        else:
            reasons.append(f'Funding {funding*100:.4f}%')
        if fg is not None:
            if fg < 20:
                sig, conf = 'BULLISH', max(conf, 70)
                reasons.append(f'F&G:{fg} Extreme Fear')
            elif fg > 80:
                sig, conf = 'BEARISH', max(conf, 70)
                reasons.append(f'F&G:{fg} Extreme Greed')
            else:
                reasons.append(f'F&G:{fg}')
        return {'signal': sig, 'confidence': conf, 'reason': ', '.join(reasons)}
    except Exception as e:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': str(e)}

# ============ CONSENSUS ENGINE ============
def consensus_engine(agents_output, market_state):
    bull, bear, total = 0, 0, 0
    reasons, ag_bull, ag_bear = [], 0, 0

    for name, out in agents_output.items():
        if name == 'market_regime':
            continue
        w = AGENT_WEIGHTS.get(name, 10)
        total += w
        sig = out.get('signal', 'NEUTRAL')
        conf = out.get('confidence', 0)
        vote = w * (conf / 100)

        if sig == 'BULLISH':
            bull += vote
            ag_bull += 1
            reasons.append(f"🟢 {name}: {out.get('reason', '')}")
        elif sig == 'BEARISH':
            bear += vote
            ag_bear += 1
            reasons.append(f"🔴 {name}: {out.get('reason', '')}")
        else:
            reasons.append(f"⚪ {name}: {out.get('reason', '')}")

    if total == 0:
        return None
    bp = (bull / total) * 100
    bep = (bear / total) * 100

    if bp >= bep and bp >= MIN_CONSENSUS_SCORE * 0.6:
        direction, strength, agree = 'BULLISH', bp, ag_bull
    elif bep > bp and bep >= MIN_CONSENSUS_SCORE * 0.6:
        direction, strength, agree = 'BEARISH', bep, ag_bear
    else:
        return None

    if agree < MIN_AGENTS_AGREEING:
        return None
    if market_state == 'RANGING' and strength < 80:
        return None
    if market_state == 'VOLATILE' and strength < 85:
        return None

    return {'direction': direction, 'strength': strength, 'agreeing': agree, 'reasons': reasons}

# ============ MAIN ANALYSIS ============
def analyze_coin(symbol):
    print(f"\n🔍 {symbol}")
    df = fetch_ohlcv(symbol, '15m', 300)
    if df is None or len(df) < 100:
        return None

    regime = agent_market_regime(df)
    trend = agent_trend_momentum(df)
    flow = agent_order_flow(df)
    struct = agent_market_structure(df)
    ml = agent_ml_quant(df)
    mtf = agent_multi_timeframe(symbol)
    sent = agent_sentiment(symbol)

    agents = {
        'market_regime': regime, 'trend_momentum': trend, 'order_flow': flow,
        'market_structure': struct, 'ml_quant': ml, 'multi_timeframe': mtf, 'sentiment': sent,
    }

    print(f"  Regime:{regime['state']} | Trend:{trend['signal']} | Flow:{flow['signal']} | SMC:{struct['signal']} | ML:{ml['signal']} | MTF:{mtf['signal']} | Sent:{sent['signal']}")

    cons = consensus_engine(agents, regime['state'])
    if cons is None:
        return None

    entry = df['close'].iloc[-1]
    if cons['direction'] == 'BULLISH':
        sl = entry * 0.985
        tp = entry + (entry - sl) * 2
        action = 'BUY 🟢'
    else:
        sl = entry * 1.015
        tp = entry - (sl - entry) * 2
        action = 'SELL 🔴'

    return {'action': action, 'symbol': symbol, 'entry': entry, 'sl': sl, 'target': tp,
            'strength': cons['strength'], 'agreeing': cons['agreeing'],
            'state': regime['state'], 'reasons': cons['reasons']}

# ============ MAIN LOOP ============
if __name__ == "__main__":
    send_telegram_alert("🏛️ इंस्टीट्यूशनल AI सिस्टम v3.0 एक्टिवेट हो गया है! 7 एजेंट्स तैनात हैं।")

    start = time.time()
    while time.time() - start < 270:
        found = False
        for coin in COINS_TO_SCAN:
            try:
                result = analyze_coin(coin)
                if result:
                    now = time.time()
                    key = f"{result['symbol']}_{result['action']}"
                    if key not in last_alert_time or (now - last_alert_time[key] > ALERT_COOLDOWN):
                        last_alert_time[key] = now
                        found = True
                        msg = f"""🏛️ <b>इंस्टीट्यूशनल सिग्नल</b> 🏛️

<b>कॉइन:</b> {result['symbol']}
<b>सिग्नल:</b> {result['action']}
<b>मार्केट स्टेट:</b> {result['state']}
<b>एंट्री:</b> {result['entry']:.4f}
<b>स्टॉप लॉस:</b> {result['sl']:.4f}
<b>टारगेट (1:2):</b> {result['target']:.4f}

<b>कुल कॉन्फिडेंस:</b> {result['strength']:.1f}%
<b>सहमत एजेंट्स:</b> {result['agreeing']}/6

<b>एजेंट एनालिसिस:</b>
{chr(10).join(result['reasons'])}"""
                        send_telegram_alert(msg)
                        print(f"✅ SENT: {result['symbol']} {result['action']}")
            except Exception as e:
                print(f"Error {coin}: {e}")
            time.sleep(1)

        if not found:
            print("⏳ Scan complete. No institutional signal.")
        time.sleep(60)
