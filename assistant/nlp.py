# ==================== HINDI NLP ENGINE (Layer 4) ====================
# काम: हिंदी/Hinglish बात समझना और जवाब बनाना

import re
import logging
from knowledge import KNOWLEDGE_BASE, STRATEGIES, format_concept_reply, format_strategy_reply

log = logging.getLogger(__name__)


# ============================================================
# INTENT PATTERNS (क्या पूछ रहा है)
# ============================================================
INTENT_PATTERNS = {
    'greeting': [
        'hello', 'hi', 'hey', 'namaste', 'namaskar', 'hii',
        'kaise ho', 'kaise hain', 'kya haal', 'kya chal',
        'भाई', 'भैया', 'हैलो', 'नमस्ते', 'कैसे हो', 'क्या हाल'
    ],
    'thanks': [
        'thank', 'thanks', 'thankyou', 'thank you', 'shukriya',
        'dhanyavad', 'धन्यवाद', 'शुक्रिया', 'थैंक्स'
    ],
    'buy_question': [
        'kharid', 'kharidu', 'kharidna', 'buy karu', 'buy karun',
        'buy karu kya', 'lena', 'lu kya', 'le sakta', 'le sakte',
        'खरीद', 'खरीदूं', 'खरीदू', 'बाय करूं', 'बाय करू', 'लूं क्या',
        'lena chahiye', 'buy karu ya nahi', 'entry lu'
    ],
    'sell_question': [
        'bech', 'bechu', 'bechna', 'sell karu', 'sell karun',
        'sell karu kya', 'bech sakta', 'bech sakte',
        'बेच', 'बेचूं', 'बेचू', 'सेल करूं', 'सेल करू', 'बेच दूं'
    ],
    'trend_question': [
        'trend', 'tarika', 'taraf', 'kis taraf', 'kidhar', 'kahan ja',
        'kahan jaa', 'upar jaa', 'niche jaa', 'upar ja raha', 'niche ja raha',
        'trend kya', 'trend kaisa', 'kaisa chal', 'kaisa chal raha',
        'तरीका', 'ट्रेंड', 'किधर', 'कहां जा', 'कैसा चल'
    ],
    'analysis': [
        'analysis', 'analyse', 'analyze', 'bata', 'bataye', 'batao',
        'kya lag', 'kya laga', 'kya lagta', 'view', 'opinion',
        'kaisa hai', 'kaisa he', 'kya scene',
        'एनालिसिस', 'बताओ', 'बताये', 'क्या लग', 'कैसा है', 'क्या सीन'
    ],
    'should_i': [
        'kya karu', 'kya karun', 'karu kya', 'karun kya',
        'sahi hai', 'sahi h', 'theek hai', 'theek h',
        'trade karu', 'trade karun', 'trade lu', 'trade lun',
        'क्या करूं', 'क्या करू', 'करूं क्या', 'सही है', 'ठीक है', 'ट्रेड करूं'
    ],
    'market_question': [
        'market', 'bazar', 'बाजार', 'मार्केट', 'halat', 'हालत',
        'market kaisa', 'market kaisi', 'bazar kaisa'
    ],
    'stop_loss': [
        'stop loss', 'stoploss', 'sl kahan', 'sl kitna', 'sl lagau',
        'स्टॉप लॉस', 'एसएल', 'sl kaha', 'sl kaha lagau'
    ],
    'target': [
        'target', 'kitna upar', 'kitna niche', 'kitna jaayega',
        'लक्ष्य', 'टारगेट', 'कितना ऊपर', 'कितना नीचे'
    ],
    'leverage': [
        'leverage', 'lever', 'kitna leverage', 'lever kitna',
        'लिवरेज', 'लेवरेज', 'कितना लिवरेज'
    ],
    'entry': [
        'entry', 'entry kaha', 'entry price', 'kahan se lu',
        'एंट्री', 'कहां से', 'कहां लूं', 'एंट्री कहां'
    ],
    'quantity': [
        'quantity', 'kitna quantity', 'kitna lu', 'kitna lun',
        'kitna lagau', 'size', 'कितना', 'कितनी', 'साइज़', 'मात्रा'
    ],
    'learn_concept': [
        'kya hai', 'kya hota', 'kya h', 'kaise kaam', 'kaise work',
        'samjhao', 'samjha', 'batao', 'bata do', 'explain',
        'क्या है', 'क्या होता', 'कैसे काम', 'समझाओ', 'बता दो'
    ],
    'strategy_question': [
        'strategy', 'tarika batao', 'konsi strategy', 'konsa strategy',
        'स्ट्रैटेजी', 'तरीका बताओ', 'कौन सी स्ट्रैटेजी'
    ],
    'help': [
        'help', 'madad', 'kya kar sakte ho', 'commands', 'kya kar sakte',
        'हेल्प', 'मदद', 'क्या कर सकते', 'कमांड्स'
    ],
    'portfolio': [
        'portfolio', 'mera trade', 'mere trade', 'open trade',
        'पोर्टफोलियो', 'मेरे ट्रेड', 'ओपन ट्रेड'
    ],
    'stats': [
        'stats', 'performance', 'kitna profit', 'kitna loss',
        'meri performance', 'report', 'स्टैट्स', 'परफॉर्मेंस',
        'कितना प्रॉफिट', 'कितना लॉस', 'रिपोर्ट'
    ],
}


# ============================================================
# COIN ALIASES (किस coin की बात)
# ============================================================
COIN_ALIASES = {
    # BTC
    'btc': 'BTC', 'bitcoin': 'BTC', 'बिटकॉइन': 'BTC', 'बीटीसी': 'BTC', 'बीटीसीए': 'BTC',
    
    # ETH
    'eth': 'ETH', 'ethereum': 'ETH', 'एथेरियम': 'ETH', 'एथ': 'ETH', 'इथेरियम': 'ETH',
    
    # SOL
    'sol': 'SOL', 'solana': 'SOL', 'सोलाना': 'SOL', 'सोल': 'SOL',
    
    # GOLD
    'gold': 'PAXG', 'सोना': 'PAXG', 'गोल्ड': 'PAXG', 'sone': 'PAXG',
    'paxg': 'PAXG', 'xaut': 'XAUT', 'sona': 'PAXG',
    
    # BNB
    'bnb': 'BNB', 'binance': 'BNB', 'बीएनबी': 'BNB',
    
    # XRP
    'xrp': 'XRP', 'ripple': 'XRP', 'रिपल': 'XRP',
    
    # ADA
    'ada': 'ADA', 'cardano': 'ADA', 'कार्डानो': 'ADA',
    
    # DOGE
    'doge': 'DOGE', 'dogecoin': 'DOGE', 'डॉग': 'DOGE', 'डोग': 'DOGE',
    
    # AVAX
    'avax': 'AVAX', 'avalanche': 'AVAX', 'एवलांच': 'AVAX',
    
    # DOT
    'dot': 'DOT', 'polkadot': 'DOT', 'पोल्काडॉट': 'DOT',
    
    # LINK
    'link': 'LINK', 'chainlink': 'LINK', 'लिंक': 'LINK',
    
    # Others
    'near': 'NEAR', 'uni': 'UNI', 'uniswap': 'UNI',
    'sui': 'SUI', 'zec': 'ZEC', 'zcash': 'ZEC',
}


# ============================================================
# HINDI STOPWORDS (फालतू शब्द हटाने के लिए)
# ============================================================
HINDI_STOPWORDS = [
    'kya', 'hai', 'he', 'h', 'ka', 'ki', 'ke', 'ko', 'se', 'me', 'mein',
    'par', 'tha', 'thi', 'the', 'abhi', 'now', 'please', 'plz', 'bro',
    'bhai', 'bhaiya', 'yaar', 'yr', 'kaise', 'kaisa', 'kaisi', 'kab',
    'kahan', 'kyun', 'kyu', 'toh', 'to', 'phir', 'fir',
    'क्या', 'है', 'हैं', 'का', 'की', 'के', 'को', 'से', 'में', 'पर',
    'भाई', 'यार', 'कैसे', 'कैसा', 'कैसी', 'कब', 'कहां', 'क्यों',
    'तो', 'फिर', 'अभी', 'प्लीज',
]


# ============================================================
# CORE FUNCTIONS
# ============================================================
def detect_intent(text):
    """क्या पूछ रहे हो?"""
    if not text:
        return 'unknown'
    
    text_lower = text.lower().strip()
    scores = {}
    
    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if pattern in text_lower:
                score += len(pattern)  # Longer pattern = higher confidence
        if score > 0:
            scores[intent] = score
    
    if not scores:
        return 'unknown'
    
    return max(scores, key=scores.get)


def detect_symbols(text):
    """कौन-कौन से coins की बात हो रही है?"""
    if not text:
        return []
    
    text_lower = text.lower()
    found = []
    
    for alias, symbol in COIN_ALIASES.items():
        # Word boundary check
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text_lower):
            if symbol not in found:
                found.append(symbol)
    
    # Direct symbol check (uppercase)
    for coin in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX',
                 'DOT', 'LINK', 'PAXG', 'XAUT', 'NEAR', 'UNI', 'SUI', 'ZEC']:
        pattern = r'\b' + coin + r'\b'
        if re.search(pattern, text.upper()):
            if coin not in found:
                found.append(coin)
    
    return found


def remove_stopwords(text):
    """फालतू शब्द हटाओ"""
    if not text:
        return ''
    
    words = text.lower().split()
    cleaned = [w for w in words if w not in HINDI_STOPWORDS and len(w) > 1]
    return ' '.join(cleaned)


def detect_concept(text):
    """कोई concept पूछा गया है?"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Direct concept key match
    for key in KNOWLEDGE_BASE.keys():
        pattern = r'\b' + re.escape(key.replace('_', ' ')) + r'\b'
        if re.search(pattern, text_lower):
            return key
        pattern2 = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern2, text_lower):
            return key
    
    # Full name match
    for key, data in KNOWLEDGE_BASE.items():
        name_lower = data['name'].lower()
        # Extract main word (e.g., "RSI (Relative Strength Index)" → "rsi")
        main_word = name_lower.split('(')[0].strip()
        if main_word and re.search(r'\b' + re.escape(main_word) + r'\b', text_lower):
            return key
    
    return None


def detect_strategy(text):
    """कोई strategy पूछी गई है?"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    for key in STRATEGIES.keys():
        keyword = key.replace('_', ' ')
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            return key
        if re.search(r'\b' + re.escape(key) + r'\b', text_lower):
            return key
    
    for key, data in STRATEGIES.items():
        name_lower = data['name'].lower()
        main_word = name_lower.split('strategy')[0].strip()
        if main_word and re.search(r'\b' + re.escape(main_word) + r'\b', text_lower):
            return key
    
    return None


def parse_message(text):
    """एक ही function जो सब कुछ parse करे"""
    if not text:
        return {
            'raw': '',
            'intent': 'unknown',
            'symbols': [],
            'concept': None,
            'strategy': None,
            'cleaned': '',
        }
    
    intent = detect_intent(text)
    symbols = detect_symbols(text)
    concept = detect_concept(text)
    strategy = detect_strategy(text)
    cleaned = remove_stopwords(text)
    
    return {
        'raw': text,
        'intent': intent,
        'symbols': symbols,
        'concept': concept,
        'strategy': strategy,
        'cleaned': cleaned,
    }


# ============================================================
# HINDI REPLY FORMATTERS
# ============================================================
def format_greeting():
    return (
        "🙏 <b>नमस्ते भाई!</b>\n\n"
        "मैं ठीक हूँ। तुम बताओ, आज क्या जानना है?\n\n"
        "💬 <b>ऐसे पूछ सकते हो:</b>\n"
        "• <code>BTC कैसा है?</code>\n"
        "• <code>ETH में बाय करूं क्या?</code>\n"
        "• <code>गोल्ड का ट्रेंड क्या है?</code>\n"
        "• <code>RSI क्या है?</code>\n"
        "• <code>SMC strategy बताओ</code>\n\n"
        "बस हिंदी में लिखो, मैं समझ जाऊंगा! 😊"
    )


def format_thanks():
    return "🙏 आपका स्वागत है भाई! कुछ और जानना हो तो बताओ।"


def format_help():
    return (
        "🤖 <b>मैं क्या-क्या कर सकता हूँ:</b>\n\n"
        "📊 <b>Analysis:</b>\n"
        "• <code>BTC कैसा है?</code>\n"
        "• <code>ETH का trend बताओ</code>\n"
        "• <code>SOL में entry कहां लूं?</code>\n\n"
        "🧠 <b>Learning:</b>\n"
        "• <code>RSI क्या है?</code>\n"
        "• <code>Order Block समझाओ</code>\n"
        "• <code>Liquidity Sweep क्या है?</code>\n\n"
        "🎯 <b>Strategies:</b>\n"
        "• <code>EMA crossover strategy</code>\n"
        "• <code>Divergence strategy बताओ</code>\n\n"
        "💼 <b>Portfolio:</b>\n"
        "• <code>मेरे trades</code>\n"
        "• <code>performance बताओ</code>\n\n"
        "❓ कुछ और? बस हिंदी में पूछो!"
    )


def format_unknown(text, symbols):
    """समझ नहीं आया तो help दो"""
    if symbols:
        return (
            f"🤔 भाई, मैं <b>{', '.join(symbols)}</b> के बारे में समझ गया, "
            "पर तुम क्या जानना चाहते हो ये clear नहीं है।\n\n"
            "ऐसे पूछो:\n"
            f"• <code>{symbols[0]} कैसा है?</code>\n"
            f"• <code>{symbols[0]} में बाय करूं?</code>\n"
            f"• <code>{symbols[0]} का ट्रेंड?</code>"
        )
    
    return (
        "🤔 भाई, समझ नहीं आया। माफ़ी!\n\n"
        "ऐसे पूछो:\n"
        "• <code>BTC कैसा है?</code>\n"
        "• <code>RSI क्या है?</code>\n"
        "• <code>Help</code>"
    )


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
    
    print("=" * 60)
    print("🧪 NLP ENGINE TEST")
    print("=" * 60)
    
    test_messages = [
        "hello bhai",
        "BTC कैसा है?",
        "ETH में बाय करूं क्या?",
        "गोल्ड का ट्रेंड क्या है?",
        "SOL sell करूं?",
        "RSI क्या है?",
        "Order block समझाओ",
        "Liquidity sweep strategy बताओ",
        "kya karu abhi",
        "thanks bhai",
        "help",
        "मेरे trades दिखाओ",
        "performance बताओ",
        "DOGE में entry कहां लूं?",
        "कुछ भी अजीब बात",
    ]
    
    for msg in test_messages:
        parsed = parse_message(msg)
        print(f"\n📝 Input: {msg}")
        print(f"   Intent: {parsed['intent']}")
        print(f"   Symbols: {parsed['symbols']}")
        print(f"   Concept: {parsed['concept']}")
        print(f"   Strategy: {parsed['strategy']}")
    
    print("\n" + "=" * 60)
    print("✅ NLP ENGINE TEST COMPLETE")
    print("=" * 60)