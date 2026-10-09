# ==================== ANALYZER (Layer 2) ====================
# काम: 4 Sectors का analysis + Consensus + Risk Manager

import pandas as pd
import numpy as np
import ta
import logging
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score

from config import (
    SECTOR_WEIGHTS, MIN_AGENTS_AGREEING, MIN_CONFIDENCE,
    DEFAULT_LEVERAGE, MAX_LEVERAGE, MIN_CONFIDENCE_FOR_LEVERAGE,
)
from data_hub import (
    fetch_ohlcv, fetch_multi_timeframe, fetch_funding_rate,
    fetch_open_interest, fetch_fear_greed, fetch_btc_dominance,
)

log = logging.getLogger(__name__)


# ==================== UTILITY ====================
def _safe_float(val, default=0.0):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return float(val)
    except:
        return default


# ==================== SECTOR 1: MACRO (25%) ====================
def sector_macro(df, symbol):
    """Market regime + Fear&Greed + BTC Dominance"""
    if df is None or len(df) < 50:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data', 'state': 'UNKNOWN'}

    score = 0
    reasons = []
    state = 'NEUTRAL'

    # Sub 1: Trend (ADX + Choppiness)
    try:
        adx = _safe_float(ta.trend.ADXIndicator(df['high'], df['low'], df['close'], 14).adx().iloc[-1])
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], 14).average_true_range()
        high_max = df['high'].rolling(14).max()
        low_min = df['low'].rolling(14).min()
        denom = (high_max - low_min).replace(0, np.nan)
        chop_series = 100 * np.log10(atr.rolling(14).sum() / denom) / np.log10(14)
        chop = _safe_float(chop_series.iloc[-1], 50)

        if adx > 25 and chop < 40:
            score += 30
            state = 'TRENDING'
            reasons.append(f'📈 Trending (ADX:{adx:.0f})')
        elif adx > 30 and chop < 35:
            score += 35
            state = 'STRONG_TREND'
            reasons.append(f'🚀 Strong Trend (ADX:{adx:.0f})')
        elif adx < 20 and chop > 60:
            score -= 15
            state = 'RANGING'
            reasons.append(f'⚖️ Ranging (CHOP:{chop:.0f})')
        else:
            reasons.append(f'⚪ Neutral (ADX:{adx:.0f}, CHOP:{chop:.0f})')

        # Volatility check
        atr_pct = _safe_float(atr.iloc[-1] / df['close'].iloc[-1] * 100)
        if atr_pct > 3.0:
            state = 'VOLATILE'
            reasons.append(f'⚡ High Volatility ({atr_pct:.1f}%)')
    except Exception as e:
        log.debug(f"Macro trend error: {e}")

    # Sub 2: Fear & Greed
    try:
        fg = fetch_fear_greed()
        if fg is not None:
            if fg < 20:
                score += 25
                reasons.append(f'😱 Extreme Fear:{fg}')
            elif fg > 80:
                score -= 25
                reasons.append(f'🤑 Extreme Greed:{fg}')
            else:
                reasons.append(f'😐 F&G:{fg}')
    except:
        pass

    # Sub 3: BTC Dominance (altcoins के लिए)
    try:
        btc_dom = fetch_btc_dominance()
        if symbol != 'BTC/USDT' and btc_dom:
            if btc_dom > 55:
                score -= 10
                reasons.append(f'BTC.D high:{btc_dom:.1f}%')
            elif btc_dom < 45:
                score += 10
                reasons.append(f'Alt season (BTC.D:{btc_dom:.1f}%)')
    except:
        pass

    score = max(-100, min(100, score * 1.5))

    if score > 40:
        return {'signal': 'BULLISH', 'confidence': min(95, 50 + score/2), 'reason': ' | '.join(reasons), 'state': state}
    elif score < -40:
        return {'signal': 'BEARISH', 'confidence': min(95, 50 + abs(score)/2), 'reason': ' | '.join(reasons), 'state': state}
    return {'signal': 'NEUTRAL', 'confidence': 40, 'reason': ' | '.join(reasons), 'state': state}


# ==================== SECTOR 2: STRUCTURE (30%) ====================
def sector_structure(df, symbol):
    """SMC + Volume Profile + S/R + MTF"""
    if df is None or len(df) < 100:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data'}

    score = 0
    reasons = []

    # Sub 1: SMC (BOS, CHoCH, FVG, Sweeps)
    try:
        lb = 5
        highs = df['high'].rolling(lb*2+1, center=True).max()
        lows = df['low'].rolling(lb*2+1, center=True).min()
        sh = df['high'][df['high'] == highs].dropna()
        sl = df['low'][df['low'] == lows].dropna()

        if len(sh) >= 2 and len(sl) >= 2:
            close = df['close'].iloc[-1]
            bos_bull = close > sh.iloc[-1]
            bos_bear = close < sl.iloc[-1]
            rh20 = df['high'].iloc[-20:-1].max()
            rl20 = df['low'].iloc[-20:-1].min()
            sweep_h = df['high'].iloc[-1] > rh20 and close < rh20
            sweep_l = df['low'].iloc[-1] < rl20 and close > rl20
            fvg_bull = df['low'].iloc[-1] > df['high'].iloc[-3]
            fvg_bear = df['high'].iloc[-1] < df['low'].iloc[-3]

            if sweep_l:
                score += 30
                reasons.append('🎯 Liquidity Sweep Bull')
            if bos_bull and fvg_bull:
                score += 25
                reasons.append('💥 BOS+FVG Bull')
            if sweep_h:
                score -= 30
                reasons.append('🎯 Liquidity Sweep Bear')
            if bos_bear and fvg_bear:
                score -= 25
                reasons.append('💥 BOS+FVG Bear')
    except Exception as e:
        log.debug(f"SMC error: {e}")

    # Sub 2: Volume Profile (POC)
    try:
        price_min = _safe_float(df['low'].min())
        price_max = _safe_float(df['high'].max())
        if price_max > price_min:
            bins = np.linspace(price_min, price_max, 101)
            df_vp = df.copy()
            df_vp['bin'] = pd.cut(df_vp['close'], bins=bins, labels=False, include_lowest=True)
            vp = df_vp.groupby('bin')['volume'].sum()
            if len(vp) > 0:
                poc_bin = vp.idxmax()
                poc_price = (bins[int(poc_bin)] + bins[int(poc_bin)+1]) / 2
                sorted_vp = vp.sort_values(ascending=False)
                cumsum = sorted_vp.cumsum()
                va_bins = cumsum[cumsum <= sorted_vp.sum() * 0.7].index.tolist()
                if va_bins:
                    va_high = bins[max(va_bins) + 1]
                    va_low = bins[min(va_bins)]
                    current = df['close'].iloc[-1]
                    if current > va_high:
                        score += 20
                        reasons.append(f'📊 Above VA (POC:{poc_price:.2f})')
                    elif current < va_low:
                        score -= 20
                        reasons.append(f'📊 Below VA (POC:{poc_price:.2f})')
                    else:
                        reasons.append(f'📊 In VA')
    except Exception as e:
        log.debug(f"VP error: {e}")

    # Sub 3: Support / Resistance
    try:
        recent = df.tail(100)
        current = df['close'].iloc[-1]
        top_highs = recent['high'].nlargest(5)
        bottom_lows = recent['low'].nsmallest(5)
        res_vals = top_highs[top_highs > current]
        sup_vals = bottom_lows[bottom_lows < current]

        if len(res_vals) > 0 and len(sup_vals) > 0:
            res = res_vals.min()
            sup = sup_vals.max()
            dist_sup = (current - sup) / current * 100
            dist_res = (res - current) / current * 100
            if dist_sup < 1.0 and dist_sup < dist_res:
                score += 20
                reasons.append(f'🛡️ Near Support ({dist_sup:.1f}%)')
            elif dist_res < 1.0 and dist_res < dist_sup:
                score -= 20
                reasons.append(f'🚧 Near Resistance ({dist_res:.1f}%)')
    except Exception as e:
        log.debug(f"S/R error: {e}")

    # Sub 4: Multi-Timeframe
    try:
        mtf_score = 0
        weights = {'quick': 0.2, 'confirm': 0.35, 'filter': 0.45}
        for tf_label, w in weights.items():
            tf_df = fetch_ohlcv(symbol, {'quick': '1m', 'confirm': '15m', 'filter': '1h'}[tf_label], 100)
            if tf_df is not None and len(tf_df) > 50:
                e20 = tf_df['close'].ewm(span=20).mean().iloc[-1]
                e50 = tf_df['close'].ewm(span=50).mean().iloc[-1]
                c = tf_df['close'].iloc[-1]
                if c > e20 > e50:
                    mtf_score += w * 100
                elif c < e20 < e50:
                    mtf_score -= w * 100
        score += mtf_score * 0.3
        if mtf_score > 70:
            reasons.append('📊 MTF Bullish')
        elif mtf_score < -70:
            reasons.append('📊 MTF Bearish')
    except Exception as e:
        log.debug(f"MTF error: {e}")

    score = max(-100, min(100, score))

    if score > 40:
        return {'signal': 'BULLISH', 'confidence': min(95, 50 + score/2), 'reason': ' | '.join(reasons) if reasons else 'Bullish'}
    elif score < -40:
        return {'signal': 'BEARISH', 'confidence': min(95, 50 + abs(score)/2), 'reason': ' | '.join(reasons) if reasons else 'Bearish'}
    return {'signal': 'NEUTRAL', 'confidence': 40, 'reason': ' | '.join(reasons) if reasons else 'No structure'}


# ==================== SECTOR 3: FLOW (25%) ====================
def sector_flow(df, symbol):
    """CVD + Whale + Funding + Buy/Sell"""
    if df is None or len(df) < 50:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data'}

    score = 0
    reasons = []

    # Sub 1: CVD Divergence
    try:
        df_f = df.copy()
        df_f['delta'] = np.where(df_f['close'] > df_f['open'], df_f['volume'],
                          np.where(df_f['close'] < df_f['open'], -df_f['volume'], 0))
        df_f['cvd'] = df_f['delta'].cumsum()
        price_change = df_f['close'].iloc[-1] - df_f['close'].iloc[-20]
        cvd_change = df_f['cvd'].iloc[-1] - df_f['cvd'].iloc[-20]

        if price_change < 0 and cvd_change > 0:
            score += 35
            reasons.append('💧 CVD Bull Div')
        elif price_change > 0 and cvd_change < 0:
            score -= 35
            reasons.append('💧 CVD Bear Div')
    except Exception as e:
        log.debug(f"CVD error: {e}")

    # Sub 2: Whale Volume Detection
    try:
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        if avg_vol > 0:
            vol_ratio = df['volume'].iloc[-1] / avg_vol
            if vol_ratio > 3:
                if df['close'].iloc[-1] > df['open'].iloc[-1]:
                    score += 20
                    reasons.append(f'🐋 Whale Buy ({vol_ratio:.1f}x)')
                else:
                    score -= 20
                    reasons.append(f'🐋 Whale Sell ({vol_ratio:.1f}x)')
    except:
        pass

    # Sub 3: Funding Rate (Contrarian)
    try:
        funding = fetch_funding_rate(symbol)
        if funding is not None:
            if funding < -0.0005:
                score += 20
                reasons.append(f'💰 Funding Neg ({funding*100:.3f}%)')
            elif funding > 0.001:
                score -= 20
                reasons.append(f'💰 Funding Pos ({funding*100:.3f}%)')
    except:
        pass

    # Sub 4: Buy/Sell Pressure
    try:
        recent = df.tail(10)
        buy_v = recent[recent['close'] > recent['open']]['volume'].sum()
        sell_v = recent[recent['close'] < recent['open']]['volume'].sum()
        total = buy_v + sell_v
        if total > 0:
            ratio = buy_v / total
            if ratio > 0.6:
                score += 15
                reasons.append(f'📈 Buy Pressure {ratio:.2f}')
            elif ratio < 0.4:
                score -= 15
                reasons.append(f'📉 Sell Pressure {ratio:.2f}')
    except:
        pass

    score = max(-100, min(100, score))

    if score > 40:
        return {'signal': 'BULLISH', 'confidence': min(95, 50 + score/2), 'reason': ' | '.join(reasons) if reasons else 'Bullish flow'}
    elif score < -40:
        return {'signal': 'BEARISH', 'confidence': min(95, 50 + abs(score)/2), 'reason': ' | '.join(reasons) if reasons else 'Bearish flow'}
    return {'signal': 'NEUTRAL', 'confidence': 40, 'reason': ' | '.join(reasons) if reasons else 'No flow'}


# ==================== SECTOR 4: QUANT (20%) ====================
def sector_quant(df, symbol):
    """ML Model + EMA Ribbon + MACD"""
    if df is None or len(df) < 150:
        return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'No data'}

    score = 0
    reasons = []

    # Sub 1: EMA Ribbon
    try:
        e8 = df['close'].ewm(span=8).mean().iloc[-1]
        e13 = df['close'].ewm(span=13).mean().iloc[-1]
        e21 = df['close'].ewm(span=21).mean().iloc[-1]
        e34 = df['close'].ewm(span=34).mean().iloc[-1]
        e55 = df['close'].ewm(span=55).mean().iloc[-1]
        if e8 > e13 > e21 > e34 > e55:
            score += 30
            reasons.append('📊 EMA Ribbon Bull')
        elif e8 < e13 < e21 < e34 < e55:
            score -= 30
            reasons.append('📊 EMA Ribbon Bear')
    except:
        pass

    # Sub 2: MACD
    try:
        macd_hist = ta.trend.MACD(df['close']).macd_diff()
        if macd_hist.iloc[-1] > 0 and macd_hist.iloc[-1] > macd_hist.iloc[-2]:
            score += 20
            reasons.append('📊 MACD Bull')
        elif macd_hist.iloc[-1] < 0 and macd_hist.iloc[-1] < macd_hist.iloc[-2]:
            score -= 20
            reasons.append('📊 MACD Bear')
    except:
        pass

    # Sub 3: ML Model
    try:
        df_ml = df.copy()
        df_ml['rsi'] = ta.momentum.RSIIndicator(df_ml['close'], 14).rsi()
        df_ml['macd'] = ta.trend.MACD(df_ml['close']).macd_diff()
        df_ml['ema_20'] = ta.trend.EMAIndicator(df_ml['close'], 20).ema_indicator()
        df_ml['ema_50'] = ta.trend.EMAIndicator(df_ml['close'], 50).ema_indicator()
        df_ml['atr'] = ta.volatility.AverageTrueRange(df_ml['high'], df_ml['low'], df_ml['close'], 14).average_true_range()
        df_ml['bb_w'] = ta.volatility.BollingerBands(df_ml['close'], 20).bollinger_wband()
        df_ml['vol_r'] = df_ml['volume'] / df_ml['volume'].rolling(20).mean()
        df_ml['ret'] = df_ml['close'].pct_change()
        df_ml['vol'] = df_ml['ret'].rolling(20).std()
        df_ml['mom'] = df_ml['close'] - df_ml['close'].shift(10)
        df_ml['cvd'] = (df_ml['volume'] * np.sign(df_ml['close'] - df_ml['open'])).cumsum()
        df_ml['cvd_c'] = df_ml['cvd'].diff(5)
        df_ml['ema_d'] = df_ml['ema_20'] - df_ml['ema_50']
        df_ml['rsi_m'] = df_ml['rsi'] - df_ml['rsi'].shift(5)
        df_ml['vol_z'] = (df_ml['volume'] - df_ml['volume'].rolling(20).mean()) / df_ml['volume'].rolling(20).std()
        df_ml['atr_norm'] = df_ml['atr'] / df_ml['close']
        df_ml['body'] = abs(df_ml['close'] - df_ml['open']) / (df_ml['high'] - df_ml['low'] + 1e-9)

        feats = ['rsi', 'macd', 'ema_20', 'ema_50', 'atr', 'bb_w', 'vol_r', 'ret',
                 'vol', 'mom', 'cvd_c', 'ema_d', 'rsi_m', 'vol_z', 'atr_norm', 'body']

        df_ml['target'] = (df_ml['close'].shift(-1) > df_ml['close']).astype(int)
        df_ml = df_ml.dropna()

        if len(df_ml) >= 100:
            X, y = df_ml[feats].values, df_ml['target'].values
            tscv = TimeSeriesSplit(n_splits=3)
            accs = []
            for tr, te in tscv.split(X):
                m = XGBClassifier(n_estimators=80, max_depth=4, learning_rate=0.08,
                                  random_state=42, verbosity=0)
                m.fit(X[tr], y[tr])
                accs.append(accuracy_score(y[te], m.predict(X[te])))
            avg_acc = np.mean(accs)

            final = XGBClassifier(n_estimators=80, max_depth=4, learning_rate=0.08,
                                  random_state=42, verbosity=0)
            final.fit(X, y)
            proba = final.predict_proba(X[-1:])[0]
            pred = int(final.predict(X[-1:])[0])
            conf = max(proba) * 100

            if avg_acc > 0.55 and conf > 62:
                if pred == 1:
                    score += 30
                    reasons.append(f'🤖 ML Bull {conf:.0f}%')
                else:
                    score -= 30
                    reasons.append(f'🤖 ML Bear {conf:.0f}%')
                reasons.append(f'🎯 Acc:{avg_acc*100:.1f}%')
    except Exception as e:
        log.debug(f"ML error: {e}")

    score = max(-100, min(100, score))

    if score > 40:
        return {'signal': 'BULLISH', 'confidence': min(95, 50 + score/2), 'reason': ' | '.join(reasons) if reasons else 'Bullish quant'}
    elif score < -40:
        return {'signal': 'BEARISH', 'confidence': min(95, 50 + abs(score)/2), 'reason': ' | '.join(reasons) if reasons else 'Bearish quant'}
    return {'signal': 'NEUTRAL', 'confidence': 40, 'reason': ' | '.join(reasons) if reasons else 'No quant'}


# ==================== CONSENSUS ENGINE ====================
def consensus_engine(sectors, market_state='NEUTRAL'):
    """4 sectors की सहमति से final decision"""
    bull, bear, total = 0, 0, 0
    reasons = []
    ag_bull, ag_bear = 0, 0

    # Dynamic threshold
    if market_state == 'RANGING':
        min_score = 82
    elif market_state == 'VOLATILE':
        min_score = 85
    elif market_state == 'STRONG_TREND':
        min_score = 68
    elif market_state == 'TRENDING':
        min_score = 72
    else:
        min_score = 78

    for name, out in sectors.items():
        if name == 'macro' and out.get('state'):
            market_state = out['state']
        w = SECTOR_WEIGHTS.get(name, 25)
        total += w
        sig = out.get('signal', 'NEUTRAL')
        conf = out.get('confidence', 0)
        vote = w * (conf / 100)

        icon = '🟢' if sig == 'BULLISH' else ('🔴' if sig == 'BEARISH' else '⚪')
        reasons.append(f"{icon} {name.upper()}: {out.get('reason', '')}")

        if sig == 'BULLISH':
            bull += vote
            ag_bull += 1
        elif sig == 'BEARISH':
            bear += vote
            ag_bear += 1

    if total == 0:
        return None

    bp = (bull / total) * 100
    bep = (bear / total) * 100

    if bp >= bep and ag_bull >= MIN_AGENTS_AGREEING and bp >= min_score * 0.6:
        direction, strength, agree = 'BULLISH', bp, ag_bull
    elif bep > bp and ag_bear >= MIN_AGENTS_AGREEING and bep >= min_score * 0.6:
        direction, strength, agree = 'BEARISH', bep, ag_bear
    else:
        return None

    if strength < min_score:
        return None

    return {
        'direction': direction,
        'strength': strength,
        'agreeing': agree,
        'reasons': reasons,
        'threshold': min_score,
        'market_state': market_state,
    }


# ==================== RISK MANAGER ====================
def risk_manager_check(symbol, direction, df, active_trades=None):
    """Risk वेटो — अगर risk ज्यादा है तो reject करो"""
    if active_trades is None:
        active_trades = []

    # 1. Volatility check
    try:
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], 14).average_true_range()
        atr_pct = atr.iloc[-1] / df['close'].iloc[-1] * 100
        if atr_pct > 5.0:
            return False, f'Extreme volatility ({atr_pct:.1f}%)', 0
    except:
        pass

    # 2. Correlation check
    try:
        same_dir = sum(1 for t in active_trades if t.get('direction') == direction)
        if same_dir >= 3:
            return False, f'Too many {direction} trades already', 0
    except:
        pass

    # 3. Default size
    size_mult = 1.0
    return True, 'Approved', size_mult


# ==================== LEVERAGE CALCULATOR ====================
def calculate_leverage(confidence, atr_pct, sl_distance_pct):
    """Confidence + volatility के हिसाब से leverage सुझाव"""
    if confidence < MIN_CONFIDENCE_FOR_LEVERAGE:
        return 0, 'No leverage (low confidence)'

    # Base from confidence
    if confidence >= 85:
        base = 25
    elif confidence >= 75:
        base = 20
    elif confidence >= 65:
        base = 15
    else:
        base = 10

    # Volatility adjustment
    if atr_pct > 3.0:
        base = min(base, 5)
    elif atr_pct > 2.0:
        base = min(base, 10)
    elif atr_pct > 1.5:
        base = min(base, 15)

    # SL distance check (liquidation buffer)
    max_safe = int(1 / (sl_distance_pct * 0.7)) if sl_distance_pct > 0 else MAX_LEVERAGE
    final = min(base, max_safe, MAX_LEVERAGE)

    return final, f'Confidence {confidence:.0f}%, ATR {atr_pct:.1f}%, SL {sl_distance_pct:.2f}%'


# ==================== MAIN ANALYSIS ====================
def analyze(symbol):
    """Complete analysis of a symbol"""
    log.info(f"🔍 Analyzing {symbol}...")

    df = fetch_ohlcv(symbol, '15m', 300)
    if df is None or len(df) < 100:
        log.warning(f"No data for {symbol}")
        return None

    # Run all 4 sectors
    macro = sector_macro(df, symbol)
    structure = sector_structure(df, symbol)
    flow = sector_flow(df, symbol)
    quant = sector_quant(df, symbol)

    sectors = {
        'macro': macro,
        'structure': structure,
        'flow': flow,
        'quant': quant,
    }

    market_state = macro.get('state', 'NEUTRAL')

    # Consensus
    consensus = consensus_engine(sectors, market_state)
    if consensus is None:
        return {
            'symbol': symbol,
            'verdict': 'NO_TRADE',
            'price': _safe_float(df['close'].iloc[-1]),
            'sectors': sectors,
            'consensus': None,
            'reason': 'No consensus',
        }

    # Risk check
    approved, risk_reason, size_mult = risk_manager_check(symbol, consensus['direction'], df)
    if not approved:
        return {
            'symbol': symbol,
            'verdict': 'NO_TRADE',
            'price': _safe_float(df['close'].iloc[-1]),
            'sectors': sectors,
            'consensus': consensus,
            'reason': f'Risk Manager: {risk_reason}',
        }

    # Dynamic SL/TP based on ATR
    atr = _safe_float(ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], 14).average_true_range().iloc[-1])
    entry = _safe_float(df['close'].iloc[-1])
    atr_pct = (atr / entry) * 100 if entry > 0 else 0

    if consensus['direction'] == 'BULLISH':
        sl = entry - (2.0 * atr)
        tp1 = entry + (2.5 * atr)
        tp2 = entry + (5.0 * atr)
        action = 'BUY'
    else:
        sl = entry + (2.0 * atr)
        tp1 = entry - (2.5 * atr)
        tp2 = entry - (5.0 * atr)
        action = 'SELL'

    sl_distance_pct = abs(entry - sl) / entry * 100 if entry > 0 else 0
    leverage, lev_reason = calculate_leverage(consensus['strength'], atr_pct, sl_distance_pct)

    risk = abs(entry - sl)
    rr1 = abs(tp1 - entry) / risk if risk > 0 else 0
    rr2 = abs(tp2 - entry) / risk if risk > 0 else 0

    return {
        'symbol': symbol,
        'verdict': action,
        'price': entry,
        'entry': entry,
        'sl': sl,
        'tp1': tp1,
        'tp2': tp2,
        'rr1': rr1,
        'rr2': rr2,
        'leverage': leverage,
        'leverage_reason': lev_reason,
        'atr': atr,
        'atr_pct': atr_pct,
        'size_mult': size_mult,
        'sectors': sectors,
        'consensus': consensus,
        'strength': consensus['strength'],
        'agreeing': consensus['agreeing'],
        'market_state': consensus['market_state'],
        'reasons': consensus['reasons'],
        'threshold': consensus['threshold'],
    }


# ==================== TEST ====================
if __name__ == "__main__":
    import time
    print("\n" + "=" * 60)
    print("🧪 ANALYZER TEST")
    print("=" * 60)

    test_coins = ['BTC/USDT', 'ETH/USDT', 'PAXG/USDT']

    for coin in test_coins:
        print(f"\n{'='*60}")
        start = time.time()
        result = analyze(coin)
        elapsed = time.time() - start

        if result is None:
            print(f"❌ {coin}: No data")
            continue

        print(f"📊 {result['symbol']}")
        print(f"   Verdict: {result['verdict']}")
        print(f"   Price: {result['price']:.4f}")
        print(f"   Market State: {result.get('market_state', 'N/A')}")

        if result['verdict'] != 'NO_TRADE':
            print(f"   Entry: {result['entry']:.4f}")
            print(f"   SL: {result['sl']:.4f}")
            print(f"   TP1: {result['tp1']:.4f} (1:{result['rr1']:.1f})")
            print(f"   TP2: {result['tp2']:.4f} (1:{result['rr2']:.1f})")
            print(f"   Leverage: {result['leverage']}x")
            print(f"   Strength: {result['strength']:.1f}%")
            print(f"   Agreeing: {result['agreeing']}/4")
            print(f"   Leverage Reason: {result['leverage_reason']}")
        else:
            print(f"   Reason: {result['reason']}")

        print(f"   Time: {elapsed:.1f}s")

        # Print sector details
        for sec_name, sec_data in result['sectors'].items():
            sig = sec_data.get('signal', 'NEUTRAL')
            conf = sec_data.get('confidence', 0)
            print(f"   [{sec_name.upper()}] {sig} ({conf:.0f}%)")

    print("\n" + "=" * 60)
    print("✅ ANALYZER TEST COMPLETE")
    print("=" * 60)