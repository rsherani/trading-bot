# ==================== KNOWLEDGE BASE (Layer 3) ====================
# काम: Trading concepts + Strategies का भंडार

# ============================================================
# PART 1: TRADING CONCEPTS (Hindi explanations)
# ============================================================
KNOWLEDGE_BASE = {
    # ============ INDICATORS ============
    'rsi': {
        'name': 'RSI (Relative Strength Index)',
        'category': 'Indicator',
        'hindi': 'RSI मोमेंटम इंडिकेटर है जो 0-100 के बीच रहता है। ये बताता है कि मार्केट में खरीदारी ज्यादा है या बिक्री।',
        'how': 'पिछले 14 कैंडल्स में औसत लाभ और हानि का अनुपात निकाला जाता है।',
        'bullish': '30 से नीचे (Oversold) = BUY, 50 से ऊपर = Bullish',
        'bearish': '70 से ऊपर (Overbought) = SELL, 50 से नीचे = Bearish',
        'divergence': 'Price नया Low बनाए पर RSI Higher Low = Bullish Div (BUY)',
        'mistake': '30/70 पर सीधे trade मत लो, confirmation का इंतज़ार करो'
    },
    'macd': {
        'name': 'MACD',
        'category': 'Indicator',
        'hindi': 'MACD ट्रेंड और मोमेंटम दोनों बताता है। इसमें 2 लाइनें होती हैं - MACD Line और Signal Line।',
        'how': '12 और 26 EMA का फर्क निकाला जाता है। Signal Line इसकी 9-period EMA है।',
        'bullish': 'MACD Line, Signal Line को ऊपर क्रॉस करे = BUY',
        'bearish': 'MACD Line, Signal Line को नीचे क्रॉस करे = SELL',
        'divergence': 'Histogram सिकुड़ रहा हो = मोमेंटम कमजोर',
        'mistake': 'सिर्फ MACD पर भरोसा मत करो, volume भी देखो'
    },
    'ema': {
        'name': 'EMA (Exponential Moving Average)',
        'category': 'Indicator',
        'hindi': 'EMA हाल की कीमतों को ज्यादा वज़न देता है। ये ट्रेंड बताने का सबसे अच्छा तरीका है।',
        'how': 'हर कैंडल को अलग वज़न दिया जाता है - जितनी नई, उतना ज्यादा वज़न।',
        'bullish': 'Price, EMA के ऊपर = Uptrend। 20 EMA > 50 EMA = Strong Uptrend',
        'bearish': 'Price, EMA के नीचे = Downtrend। 20 EMA < 50 EMA = Strong Downtrend',
        'golden_cross': '50 EMA, 200 EMA को ऊपर क्रॉस करे = Golden Cross (Bullish)',
        'death_cross': '50 EMA, 200 EMA को नीचे क्रॉस करे = Death Cross (Bearish)',
        'mistake': 'Range market में EMA क्रॉस फेक होते हैं'
    },
    'bollinger': {
        'name': 'Bollinger Bands',
        'category': 'Indicator',
        'hindi': 'Bollinger Bands में 3 लाइनें होती हैं - Upper, Middle (SMA 20), Lower। ये वोलेटिलिटी बताती हैं।',
        'how': 'Middle = 20 SMA। Upper = Middle + (2 × Standard Deviation)। Lower = Middle - (2 × SD)',
        'bullish': 'Price Lower Band को touch करके वापस आए = BUY',
        'bearish': 'Price Upper Band को touch करके वापस आए = SELL',
        'squeeze': 'Bands सिकुड़ जाएं = बड़ा मूव आने वाला है',
        'mistake': 'Strong trend में price band के साथ-साथ चलती है, रिवर्सल नहीं होता'
    },
    'atr': {
        'name': 'ATR (Average True Range)',
        'category': 'Indicator',
        'hindi': 'ATR वोलेटिलिटी बताता है। ज्यादा ATR = ज्यादा उतार-चढ़ाव = ज्यादा risk।',
        'how': 'पिछले 14 कैंडल्स के True Range का average।',
        'use': 'Stop Loss set करने में सबसे बेहतर। SL = Entry - (1.5 × ATR)',
        'mistake': 'Low ATR में position size बढ़ा सकते हो, high ATR में घटाओ'
    },
    'adx': {
        'name': 'ADX (Average Directional Index)',
        'category': 'Indicator',
        'hindi': 'ADX बताता है कि ट्रेंड कितना मजबूत है (दिशा नहीं)।',
        'how': '0-100 के बीच। +DI और -DI से ट्रेंड की strength निकाली जाती है।',
        'bullish': 'ADX > 25 = मजबूत ट्रेंड',
        'bearish': 'ADX < 20 = कमजोर/साइडवेज मार्केट',
        'mistake': 'ADX direction नहीं बताता, सिर्फ strength बताता है'
    },
    'stochastic': {
        'name': 'Stochastic Oscillator',
        'category': 'Indicator',
        'hindi': 'RSI जैसा ही है, लेकिन high-low range पर काम करता है।',
        'how': '%K और %D लाइनें होती हैं।',
        'bullish': '%K, %D को 20 के नीचे क्रॉस करे = BUY',
        'bearish': '%K, %D को 80 के ऊपर क्रॉस करे = SELL',
        'mistake': 'Strong trend में ये बहुत जल्दी overbought/oversold हो जाता है'
    },
    'vwap': {
        'name': 'VWAP (Volume Weighted Average Price)',
        'category': 'Indicator',
        'hindi': 'VWAP बताता है कि दिन का औसत खरीद-बिक्री मूल्य क्या रहा। Institutional traders इसे बहुत use करते हैं।',
        'how': 'हर trade की कीमत को उसके volume से गुणा करके average निकाला जाता है।',
        'bullish': 'Price VWAP के ऊपर = Bulls control',
        'bearish': 'Price VWAP के नीचे = Bears control',
        'use': 'Intraday traders का favorite। Pullback पर VWAP से BUY'
    },
    'supertrend': {
        'name': 'Supertrend',
        'category': 'Indicator',
        'hindi': 'Supertrend सबसे simple और effective trend-following इंडिकेटर है।',
        'how': 'ATR-based। हरा = uptrend, लाल = downtrend।',
        'bullish': 'Price हरी लाइन के ऊपर = BUY',
        'bearish': 'Price लाल लाइन के नीचे = SELL',
        'mistake': 'Sideways market में whipsaw होता है'
    },
    'ichimoku': {
        'name': 'Ichimoku Cloud',
        'category': 'Indicator',
        'hindi': 'Ichimoku एक ही इंडिकेटर में ट्रेंड, support, resistance सब देता है।',
        'how': 'Tenkan, Kijun, Senkou Span A, Senkou Span B से बनता है।',
        'bullish': 'Price cloud के ऊपर + Tenkan > Kijun',
        'bearish': 'Price cloud के नीचे + Tenkan < Kijun',
        'mistake': 'Beginner के लिए complex है, पहले basic सीखो'
    },
    'obv': {
        'name': 'OBV (On-Balance Volume)',
        'category': 'Indicator',
        'hindi': 'OBV वॉल्यूम के आधार पर buying और selling pressure बताता है।',
        'how': 'Price बढ़े तो volume जोड़ो, गिरे तो घटाओ।',
        'bullish': 'OBV नया high बनाए जबकि price नहीं = Bullish signal',
        'bearish': 'OBV नया low बनाए जबकि price नहीं = Bearish signal'
    },
    
    # ============ SMC / ICT CONCEPTS ============
    'bos': {
        'name': 'BOS (Break of Structure)',
        'category': 'SMC',
        'hindi': 'जब कीमत पिछले swing high (bullish में) या swing low (bearish में) को तोड़ दे।',
        'how': 'Uptrend में higher high बने = Bullish BOS। Downtrend में lower low बने = Bearish BOS।',
        'bullish': 'Bullish BOS = uptrend जारी रहेगा',
        'bearish': 'Bearish BOS = downtrend जारी रहेगा',
        'use': 'Trend continuation trades के लिए'
    },
    'choch': {
        'name': 'CHoCH (Change of Character)',
        'category': 'SMC',
        'hindi': 'जब ट्रेंड अपनी दिशा बदल दे।',
        'how': 'Uptrend में पहली बार lower low बने = Bearish CHoCH (reversal)',
        'bullish': 'Downtrend में पहली बार higher high बने = Bullish CHoCH',
        'bearish': 'Uptrend में पहली बार lower low बने = Bearish CHoCH',
        'use': 'Reversal trades के लिए सबसे अच्छा'
    },
    'fvg': {
        'name': 'FVG (Fair Value Gap)',
        'category': 'SMC',
        'hindi': 'जब एक कैंडल के high और तीसरी कैंडल के low के बीच gap बने।',
        'how': '3 कैंडल pattern: पहली कैंडल का high और तीसरी का low touch नहीं करते।',
        'bullish': 'Bullish FVG = कीमत वापस आकर भरेगी, वहाँ से BUY',
        'bearish': 'Bearish FVG = कीमत वापस आकर भरेगी, वहाँ से SELL',
        'use': 'Entry के लिए best price zone'
    },
    'order_block': {
        'name': 'Order Block',
        'category': 'SMC',
        'hindi': 'वो कैंडल जहाँ से institutional traders ने बड़ी position ली हो।',
        'how': 'Bullish OB = आखिरी bearish candle before strong bullish move',
        'bullish': 'Price वापस Bullish OB पर आए = BUY',
        'bearish': 'Price वापस Bearish OB पर आए = SELL',
        'use': 'Strong support/resistance की तरह काम करता है'
    },
    'liquidity_sweep': {
        'name': 'Liquidity Sweep',
        'category': 'SMC',
        'hindi': 'जब बड़े traders जानबूझकर price को high/low के ऊपर-नीचे ले जाएं ताकि retail traders के stop-loss हिट हों।',
        'how': 'Price नया high/low बनाकर तुरंत वापस आ जाए।',
        'bullish': 'Low sweep होकर वापस ऊपर = BUY (bears trapped)',
        'bearish': 'High sweep होकर वापस नीचे = SELL (bulls trapped)',
        'use': 'Reversal के लिए सबसे मजबूत signal'
    },
    'premium_discount': {
        'name': 'Premium vs Discount',
        'category': 'SMC',
        'hindi': 'Range के top 50% = Premium (महंगा), bottom 50% = Discount (सस्ता)।',
        'bullish': 'Discount zone में BUY करो',
        'bearish': 'Premium zone में SELL करो',
        'use': 'Buy low, sell high का स्मार्ट तरीका'
    },
    'kill_zone': {
        'name': 'ICT Kill Zones',
        'category': 'ICT',
        'hindi': 'Specific time windows जब market में सबसे ज्यादा moves आते हैं।',
        'how': 'London (12:30-3:30 PM IST), New York (6:30-9:30 PM IST)',
        'use': 'इन times पर trade करो, बाकी समय avoid करो'
    },
    'inducement': {
        'name': 'Inducement (IDM)',
        'category': 'SMC',
        'hindi': 'वो fake level जहाँ retail traders के stop-loss लगे होते हैं, बड़े traders वहाँ से चूसते हैं।',
        'how': 'Previous swing high/low जो चोटी की तरह दिखे।',
        'use': 'IDM के बाद असली move आता है, तब entry लो'
    },
    
    # ============ CHART PATTERNS ============
    'head_shoulders': {
        'name': 'Head and Shoulders',
        'category': 'Chart Pattern',
        'hindi': '3 चोटियाँ - बीच वाली सबसे ऊँची। Bearish reversal pattern।',
        'how': 'Left shoulder, Head (highest), Right shoulder। Neckline break होने पर sell।',
        'bearish': 'Neckline के नीचे break = SELL',
        'target': 'Head से neckline की दूरी जितना target'
    },
    'double_top': {
        'name': 'Double Top',
        'category': 'Chart Pattern',
        'hindi': 'दो बार same level पर rejection। Bearish reversal।',
        'bearish': 'दूसरी top के बाद neckline break = SELL',
        'target': 'Height of pattern'
    },
    'double_bottom': {
        'name': 'Double Bottom',
        'category': 'Chart Pattern',
        'hindi': 'दो बार same level पर support। Bullish reversal।',
        'bullish': 'दूसरे bottom के बाद neckline break = BUY',
        'target': 'Height of pattern'
    },
    'triangle': {
        'name': 'Triangle Pattern',
        'category': 'Chart Pattern',
        'hindi': 'Converging lines - price सिकुड़ता जाता है। Breakout आने वाला है।',
        'bullish': 'Ascending triangle = BUY (resistance break पर)',
        'bearish': 'Descending triangle = SELL (support break पर)',
        'symmetrical': 'किसी भी तरफ break हो सकता है, confirmation चाहिए'
    },
    'flag': {
        'name': 'Flag Pattern',
        'category': 'Chart Pattern',
        'hindi': 'तेज move के बाद छोटा consolidation, फिर वापस उसी दिशा में move।',
        'bullish': 'Bull flag = BUY (flag break पर)',
        'bearish': 'Bear flag = SELL',
        'use': 'Trend continuation के लिए सबसे भरोसेमंद'
    },
    'cup_handle': {
        'name': 'Cup and Handle',
        'category': 'Chart Pattern',
        'hindi': 'U-shape (Cup) + छोटा pullback (Handle)। Bullish continuation।',
        'bullish': 'Handle break पर BUY',
        'use': 'Long-term bullish pattern'
    },
    
    # ============ CANDLESTICK PATTERNS ============
    'doji': {
        'name': 'Doji',
        'category': 'Candle',
        'hindi': 'Open = Close, बहुत छोटा body। मार्केट कन्फ्यूज्ड है।',
        'use': 'Reversal का indication, confirmation चाहिए'
    },
    'hammer': {
        'name': 'Hammer',
        'category': 'Candle',
        'hindi': 'छोटा body ऊपर, लंबा lower wick। Bullish reversal।',
        'bullish': 'Downtrend के बाद Hammer = BUY signal'
    },
    'shooting_star': {
        'name': 'Shooting Star',
        'category': 'Candle',
        'hindi': 'छोटा body नीचे, लंबा upper wick। Bearish reversal।',
        'bearish': 'Uptrend के बाद Shooting Star = SELL'
    },
    'engulfing': {
        'name': 'Engulfing Pattern',
        'category': 'Candle',
        'hindi': 'दूसरी candle पहली को पूरा ढक ले।',
        'bullish': 'Bullish Engulfing = BUY',
        'bearish': 'Bearish Engulfing = SELL'
    },
    'morning_star': {
        'name': 'Morning Star',
        'category': 'Candle',
        'hindi': '3-candle pattern - बड़ी red, छोटी doji, बड़ी green। Bullish reversal।',
        'bullish': 'Downtrend के बाद = Strong BUY'
    },
    
    # ============ RISK MANAGEMENT ============
    'position_sizing': {
        'name': 'Position Sizing',
        'category': 'Risk',
        'hindi': 'ये बताता है कि एक trade में कितना पैसा लगाना है।',
        'formula': 'Size = (Capital × Risk%) / (Entry - Stop Loss)',
        'rule': 'एक trade में 1-2% से ज्यादा risk मत करो',
        'example': '₹1L capital, 2% risk, entry ₹100, SL ₹95: Size = 2000/5 = 400 units'
    },
    'risk_reward': {
        'name': 'Risk-Reward Ratio',
        'category': 'Risk',
        'hindi': 'जोखिम और मुनाफे का अनुपात।',
        'rule': 'कम से कम 1:2 R:R होना चाहिए',
        'example': '1% SL पर 2% TP = 1:2 R:R',
        'note': '1:2 R:R पर 40% win rate भी profitable है'
    },
    'kelly_criterion': {
        'name': 'Kelly Criterion',
        'category': 'Risk',
        'hindi': 'Optimal position size निकालने का mathematical formula।',
        'formula': 'f = (p × b - q) / b',
        'note': 'Half Kelly use करो (ज्यादा safe)'
    },
    'drawdown': {
        'name': 'Drawdown',
        'category': 'Risk',
        'hindi': 'Peak से current level तक गिरावट।',
        'rule': '5% daily और 10% weekly पर trading रोक दो',
        'note': '50% drawdown recover करने के लिए 100% gain चाहिए'
    },
    'stop_loss': {
        'name': 'Stop Loss',
        'category': 'Risk',
        'hindi': 'नुकसान की लिमिट। हर trade में जरूरी है।',
        'rule': 'Entry से पहले SL तय करो, बाद में नहीं',
        'atr_based': 'SL = Entry - (1.5 × ATR)',
        'never': 'SL को कभी नीचे मत खिसकाओ'
    },
}


# ============================================================
# PART 2: STRATEGIES (Rules + Setup)
# ============================================================
STRATEGIES = {
    'ema_crossover': {
        'name': 'EMA Crossover Strategy',
        'category': 'Trend Following',
        'timeframes': ['15m', '1h', '4h'],
        'entry_buy': '20 EMA, 50 EMA को ऊपर क्रॉस करे + volume spike',
        'entry_sell': '20 EMA, 50 EMA को नीचे क्रॉस करे + volume spike',
        'stop_loss': 'पिछला swing low (BUY) / swing high (SELL)',
        'target': '2:1 और 4:1 R:R',
        'best_market': 'Trending',
        'win_rate': '~55-60%'
    },
    'rsi_divergence': {
        'name': 'RSI Divergence Strategy',
        'category': 'Reversal',
        'timeframes': ['15m', '1h'],
        'entry_buy': 'Price नया low, RSI higher low + RSI < 40 से ऊपर',
        'entry_sell': 'Price नया high, RSI lower high + RSI > 60 से नीचे',
        'stop_loss': 'पिछला low/high से थोड़ा आगे',
        'target': '1:2 और 1:3',
        'best_market': 'Reversal',
        'win_rate': '~50-55%'
    },
    'bollinger_squeeze': {
        'name': 'Bollinger Squeeze Breakout',
        'category': 'Volatility',
        'entry_buy': 'Bandwidth कम, price Upper Band तोड़े = BUY',
        'entry_sell': 'Bandwidth कम, price Lower Band तोड़े = SELL',
        'stop_loss': 'Middle Band या 1.5 ATR',
        'target': '2:1 से 4:1',
        'best_market': 'Consolidation → Breakout',
        'win_rate': '~60%'
    },
    'smc_order_block': {
        'name': 'SMC Order Block Entry',
        'category': 'SMC',
        'entry_buy': 'Bullish OB retest + BOS bullish + FVG',
        'entry_sell': 'Bearish OB retest + BOS bearish + FVG',
        'stop_loss': 'OB के नीचे/ऊपर',
        'target': 'अगला liquidity pool',
        'best_market': 'Trending',
        'win_rate': '~65%'
    },
    'liquidity_sweep_reversal': {
        'name': 'Liquidity Sweep Reversal',
        'category': 'SMC',
        'entry_buy': 'Previous low sweep + तुरंत वापस ऊपर + CVD bull div',
        'entry_sell': 'Previous high sweep + तुरंत वापस नीचे + CVD bear div',
        'stop_loss': 'Sweep wick से थोड़ा आगे',
        'target': 'Opposite liquidity level',
        'best_market': 'Any',
        'win_rate': '~70%'
    },
    'vwap_bounce': {
        'name': 'VWAP Bounce',
        'category': 'Intraday',
        'timeframes': ['1m', '5m', '15m'],
        'entry_buy': 'Price VWAP से ऊपर + pullback VWAP पर + bounce',
        'entry_sell': 'Price VWAP से नीचे + pullback VWAP पर + rejection',
        'stop_loss': 'VWAP के पीछे 0.5 ATR',
        'target': 'अगला intraday high/low',
        'best_market': 'Trending day',
        'win_rate': '~60%'
    },
    'supertrend_rsi': {
        'name': 'Supertrend + RSI Combo',
        'category': 'Trend Following',
        'entry_buy': 'Supertrend green + RSI > 50',
        'entry_sell': 'Supertrend red + RSI < 50',
        'stop_loss': 'Supertrend line',
        'target': 'Trailing stop use करो',
        'best_market': 'Trending',
        'win_rate': '~55%'
    },
    'macd_rsi_combo': {
        'name': 'MACD + RSI Confluence',
        'category': 'Momentum',
        'entry_buy': 'MACD bullish cross + RSI 40-65 (not overbought)',
        'entry_sell': 'MACD bearish cross + RSI 35-60 (not oversold)',
        'stop_loss': '1.5 ATR',
        'target': '2:1 R:R',
        'best_market': 'Trending',
        'win_rate': '~58%'
    },
    'volume_breakout': {
        'name': 'Volume Breakout',
        'category': 'Breakout',
        'entry_buy': 'Price resistance तोड़े + volume 2x औसत से ज्यादा',
        'entry_sell': 'Price support तोड़े + volume 2x',
        'stop_loss': 'Breakout candle का low/high',
        'target': '2:1 R:R',
        'best_market': 'Trending',
        'win_rate': '~55%'
    },
    'cvd_divergence': {
        'name': 'CVD Divergence Strategy',
        'category': 'Order Flow',
        'entry_buy': 'Price नया low, CVD higher low = smart money buying',
        'entry_sell': 'Price नया high, CVD lower high = smart money selling',
        'stop_loss': 'Recent swing',
        'target': '2:1 से 3:1',
        'best_market': 'Any',
        'win_rate': '~65%'
    },
    'golden_cross': {
        'name': 'Golden Cross / Death Cross',
        'category': 'Long-term Trend',
        'timeframes': ['4h', '1d'],
        'entry_buy': '50 EMA, 200 EMA को ऊपर क्रॉस करे',
        'entry_sell': '50 EMA, 200 EMA को नीचे क्रॉस करे',
        'stop_loss': '200 EMA',
        'target': 'Long-term hold',
        'best_market': 'Bull/Bear market',
        'win_rate': '~50% (लेकिन बड़े moves)'
    },
    'fvg_retest': {
        'name': 'FVG Retest Entry',
        'category': 'SMC',
        'entry_buy': 'Bullish FVG बने + price वापस FVG में आए = BUY',
        'entry_sell': 'Bearish FVG बने + price वापस FVG में आए = SELL',
        'stop_loss': 'FVG के आगे',
        'target': 'अगला swing point',
        'best_market': 'Trending',
        'win_rate': '~62%'
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_concept(key):
    """Concept को Hindi explanation के साथ लाओ"""
    return KNOWLEDGE_BASE.get(key.lower().strip())

def get_strategy(key):
    """Strategy details लाओ"""
    return STRATEGIES.get(key.lower().strip())

def search_concept(text):
    """Text में कोई concept ढूंढो"""
    text_lower = text.lower()
    found = []
    for key, data in KNOWLEDGE_BASE.items():
        if key in text_lower or data['name'].lower() in text_lower:
            found.append((key, data))
    return found

def get_all_categories():
    """सारी categories की list"""
    categories = {}
    for key, data in KNOWLEDGE_BASE.items():
        cat = data.get('category', 'Other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(data['name'])
    return categories

def format_concept_reply(key):
    """Concept को nicely formatted Hindi reply में बदलो"""
    data = get_concept(key)
    if not data:
        return None
    
    reply = f"📚 <b>{data['name']}</b>\n"
    reply += f"🏷️ Category: {data.get('category', 'General')}\n\n"
    reply += f"💡 <b>ये क्या है:</b>\n{data.get('hindi', '')}\n\n"
    
    if data.get('how'):
        reply += f"⚙️ <b>कैसे काम करता है:</b>\n{data['how']}\n\n"
    if data.get('bullish'):
        reply += f"🟢 <b>Bullish:</b> {data['bullish']}\n"
    if data.get('bearish'):
        reply += f"🔴 <b>Bearish:</b> {data['bearish']}\n"
    if data.get('divergence'):
        reply += f"⚡ <b>Divergence:</b> {data['divergence']}\n"
    if data.get('use'):
        reply += f"🎯 <b>कब use करें:</b> {data['use']}\n"
    if data.get('formula'):
        reply += f"🧮 <b>Formula:</b> <code>{data['formula']}</code>\n"
    if data.get('rule'):
        reply += f"📏 <b>Rule:</b> {data['rule']}\n"
    if data.get('example'):
        reply += f"📝 <b>Example:</b> {data['example']}\n"
    if data.get('mistake'):
        reply += f"⚠️ <b>Common Mistake:</b> {data['mistake']}\n"
    
    return reply


def format_strategy_reply(key):
    """Strategy को nicely formatted Hindi reply में बदलो"""
    data = get_strategy(key)
    if not data:
        return None
    
    reply = f"🎯 <b>{data['name']}</b>\n"
    reply += f"🏷️ Category: {data.get('category', 'General')}\n"
    if data.get('timeframes'):
        reply += f"⏰ Timeframes: {', '.join(data['timeframes'])}\n"
    reply += "\n"
    
    if data.get('entry_buy'):
        reply += f"🟢 <b>BUY Entry:</b>\n{data['entry_buy']}\n\n"
    if data.get('entry_sell'):
        reply += f"🔴 <b>SELL Entry:</b>\n{data['entry_sell']}\n\n"
    if data.get('stop_loss'):
        reply += f"🛑 <b>Stop Loss:</b> {data['stop_loss']}\n"
    if data.get('target'):
        reply += f"🎯 <b>Target:</b> {data['target']}\n"
    if data.get('best_market'):
        reply += f"📊 <b>Best Market:</b> {data['best_market']}\n"
    if data.get('win_rate'):
        reply += f"📈 <b>Win Rate:</b> {data['win_rate']}\n"
    
    return reply


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 KNOWLEDGE BASE TEST")
    print("=" * 60)
    
    print(f"\n📚 Total Concepts: {len(KNOWLEDGE_BASE)}")
    print(f"🎯 Total Strategies: {len(STRATEGIES)}")
    
    print("\n📂 Categories:")
    cats = get_all_categories()
    for cat, items in cats.items():
        print(f"   {cat}: {len(items)} concepts")
    
    print("\n" + "=" * 60)
    print("📖 Sample: RSI")
    print("=" * 60)
    print(format_concept_reply('rsi'))
    
    print("\n" + "=" * 60)
    print("📖 Sample: SMC Order Block")
    print("=" * 60)
    print(format_concept_reply('order_block'))
    
    print("\n" + "=" * 60)
    print("🎯 Sample Strategy: Liquidity Sweep Reversal")
    print("=" * 60)
    print(format_strategy_reply('liquidity_sweep_reversal'))
    
    print("\n✅ Knowledge Base test complete!")