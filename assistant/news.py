# ==================== NEWS & SENTIMENT (Layer 1.5) ====================
# काम: News, Fear&Greed, Trending coins, Economic events
# सारे free sources, कोई API key नहीं चाहिए

import requests
import time
import logging
from datetime import datetime
import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

# Cache
_cache = {}

def _is_cache_valid(key, ttl):
    if key not in _cache:
        return False
    return (time.time() - _cache[key]['time']) < ttl

def _set_cache(key, value):
    _cache[key] = {'value': value, 'time': time.time()}

def _get_cache(key):
    return _cache.get(key, {}).get('value')


# ==================== FEAR & GREED ====================
def get_fear_greed():
    """Fear & Greed Index (0-100)"""
    key = 'fear_greed'
    if _is_cache_valid(key, 3600):
        return _get_cache(key)
    
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        data = r.json()['data'][0]
        result = {
            'value': int(data['value']),
            'classification': data['value_classification'],
            'timestamp': data['timestamp']
        }
        _set_cache(key, result)
        return result
    except Exception as e:
        log.warning(f"Fear&Greed error: {e}")
        return None


# ==================== TRENDING COINS ====================
def get_trending_coins():
    """CoinGecko से trending coins"""
    key = 'trending'
    if _is_cache_valid(key, 1800):
        return _get_cache(key)
    
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=10)
        data = r.json()
        coins = []
        for item in data.get('coins', [])[:10]:
            c = item['item']
            coins.append({
                'symbol': c['symbol'].upper(),
                'name': c['name'],
                'market_cap_rank': c.get('market_cap_rank', 999),
                'price_btc': c.get('price_btc', 0),
            })
        _set_cache(key, coins)
        return coins
    except Exception as e:
        log.warning(f"Trending error: {e}")
        return []


# ==================== BTC DOMINANCE ====================
def get_btc_dominance():
    """BTC dominance %"""
    key = 'btc_dom'
    if _is_cache_valid(key, 3600):
        return _get_cache(key)
    
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        data = r.json()['data']
        result = {
            'btc': data['market_cap_percentage']['btc'],
            'eth': data['market_cap_percentage']['eth'],
            'total_mcap': data['total_market_cap']['usd'],
            'total_volume': data['total_volume']['usd'],
            'mcap_change_24h': data.get('market_cap_change_percentage_24h_usd', 0),
        }
        _set_cache(key, result)
        return result
    except Exception as e:
        log.warning(f"BTC dominance error: {e}")
        return None


# ==================== CRYPTO NEWS (RSS - No API Key) ====================
def _fetch_rss(url, source_name):
    """RSS feed से news निकालो"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            return []
        
        root = ET.fromstring(r.content)
        items = []
        for item in root.iter('item'):
            title_el = item.find('title')
            link_el = item.find('link')
            pubdate_el = item.find('pubDate')
            
            if title_el is not None and title_el.text:
                items.append({
                    'title': title_el.text.strip(),
                    'link': link_el.text.strip() if link_el is not None and link_el.text else '',
                    'pubdate': pubdate_el.text if pubdate_el is not None else '',
                    'source': source_name,
                })
        return items[:10]
    except Exception as e:
        log.debug(f"RSS error {source_name}: {e}")
        return []


def get_crypto_news():
    """Free RSS sources से crypto news"""
    key = 'news'
    if _is_cache_valid(key, 900):
        return _get_cache(key)
    
    sources = [
        ('https://cointelegraph.com/rss', 'CoinTelegraph'),
        ('https://coindesk.com/arc/outboundfeeds/rss/', 'CoinDesk'),
        ('https://bitcoinmagazine.com/.rss/full/', 'Bitcoin Magazine'),
        ('https://cryptoslate.com/feed/', 'CryptoSlate'),
    ]
    
    all_news = []
    for url, name in sources:
        news = _fetch_rss(url, name)
        all_news.extend(news)
        if len(all_news) >= 20:
            break
    
    # Impact scoring
    high_impact_words = ['hack', 'ban', 'sec', 'etf', 'regulation', 'crash',
                         'plunge', 'sue', 'lawsuit', 'bankruptcy', 'liquidation',
                         'fomc', 'fed', 'rate hike', 'rate cut', 'approval']
    
    for n in all_news:
        title_lower = n['title'].lower()
        n['impact'] = 'HIGH' if any(w in title_lower for w in high_impact_words) else 'MEDIUM'
    
    _set_cache(key, all_news)
    return all_news


def get_news_for_symbol(symbol):
    """किसी specific coin के लिए news filter"""
    symbol_base = symbol.replace('/USDT', '').replace('/USD', '').upper()
    
    # Symbol name mapping
    name_map = {
        'BTC': ['bitcoin', 'btc'],
        'ETH': ['ethereum', 'eth'],
        'SOL': ['solana', 'sol'],
        'BNB': ['binance coin', 'bnb'],
        'XRP': ['ripple', 'xrp'],
        'ADA': ['cardano', 'ada'],
        'DOGE': ['dogecoin', 'doge'],
        'AVAX': ['avalanche', 'avax'],
        'DOT': ['polkadot', 'dot'],
        'LINK': ['chainlink', 'link'],
        'PAXG': ['gold', 'paxg'],
        'XAUT': ['gold', 'tether gold', 'xaut'],
    }
    
    keywords = name_map.get(symbol_base, [symbol_base.lower()])
    all_news = get_crypto_news()
    
    matched = []
    for n in all_news:
        title_lower = n['title'].lower()
        if any(kw in title_lower for kw in keywords):
            matched.append(n)
    
    return matched[:5]


# ==================== ECONOMIC CALENDAR (Free) ====================
def get_economic_events():
    """आज के economic events (FOMC, CPI, NFP)"""
    key = 'events'
    if _is_cache_valid(key, 3600):
        return _get_cache(key)
    
    # Free public calendar (static list of recurring events)
    events = []
    today = datetime.now()
    weekday = today.weekday()  # 0=Monday, 6=Sunday
    
    # Monthly recurring events (approximate)
    day_of_month = today.day
    
    # Common events timing (approximate, IST)
    common_events = {
        'FOMC': 'Important - Federal Reserve meeting',
        'CPI': 'US Consumer Price Index',
        'NFP': 'US Non-Farm Payrolls',
        'PPI': 'US Producer Price Index',
        'GDP': 'US Gross Domestic Product',
    }
    
    try:
        # Try free source: tradingeconomics (public RSS)
        r = requests.get("https://tradingeconomics.com/rss/calendar", timeout=10)
        if r.status_code == 200:
            try:
                root = ET.fromstring(r.content)
                for item in root.iter('item')[:10]:
                    title = item.find('title')
                    if title is not None and title.text:
                        # Filter only important
                        t = title.text.lower()
                        impact = 'HIGH' if any(k in t for k in ['cpi', 'fomc', 'nfp', 'gdp', 'ppi', 'rate']) else 'MEDIUM'
                        events.append({
                            'title': title.text.strip(),
                            'impact': impact,
                        })
            except:
                pass
    except Exception as e:
        log.debug(f"Calendar error: {e}")
    
    _set_cache(key, events)
    return events


def is_high_impact_time():
    """High-impact news का समय है क्या?"""
    events = get_economic_events()
    for e in events:
        if e.get('impact') == 'HIGH':
            return True, e['title']
    return False, None


# ==================== MARKET SENTIMENT SUMMARY ====================
def get_market_sentiment():
    """सारे sentiment का summary"""
    fg = get_fear_greed()
    dom = get_btc_dominance()
    trending = get_trending_coins()
    news = get_crypto_news()
    
    sentiment = {
        'fear_greed': fg,
        'dominance': dom,
        'trending': trending[:5],
        'top_news': news[:5],
        'mood': 'NEUTRAL'
    }
    
    # Overall mood
    if fg:
        v = fg['value']
        if v < 25:
            sentiment['mood'] = 'EXTREME_FEAR'
        elif v < 45:
            sentiment['mood'] = 'FEAR'
        elif v < 55:
            sentiment['mood'] = 'NEUTRAL'
        elif v < 75:
            sentiment['mood'] = 'GREED'
        else:
            sentiment['mood'] = 'EXTREME_GREED'
    
    return sentiment


def format_sentiment_hindi():
    """Hindi में sentiment report"""
    s = get_market_sentiment()
    fg = s['fear_greed']
    dom = s['dominance']
    mood_emoji = {
        'EXTREME_FEAR': '😱',
        'FEAR': '😨',
        'NEUTRAL': '😐',
        'GREED': '😊',
        'EXTREME_GREED': '🤑',
    }
    
    text = "📰 <b>मार्केट सेंटीमेंट रिपोर्ट</b>\n\n"
    
    if fg:
        text += f"{mood_emoji.get(s['mood'], '')} <b>Fear & Greed:</b> {fg['value']} ({fg['classification']})\n"
    
    if dom:
        text += f"👑 <b>BTC Dominance:</b> {dom['btc']:.2f}%\n"
        text += f"📊 <b>Total Market Cap:</b> ${dom['total_mcap']/1e12:.2f}T\n"
        text += f"📈 <b>24h Change:</b> {dom['mcap_change_24h']:+.2f}%\n"
    
    trending = s.get('trending', [])
    if trending:
        text += f"\n🔥 <b>Trending Coins:</b>\n"
        for c in trending[:5]:
            text += f"• {c['symbol']} ({c['name']})\n"
    
    news = s.get('top_news', [])
    if news:
        text += f"\n📰 <b>Top News:</b>\n"
        for n in news[:3]:
            impact_icon = '🔴' if n['impact'] == 'HIGH' else '🟡'
            text += f"{impact_icon} {n['title'][:70]}...\n"
    
    return text


# ==================== TEST ====================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
    
    print("=" * 60)
    print("🧪 NEWS MODULE TEST")
    print("=" * 60)
    
    print("\n1. Fear & Greed...")
    fg = get_fear_greed()
    if fg:
        print(f"   Value: {fg['value']} ({fg['classification']})")
    else:
        print("   ❌ Failed")
    
    print("\n2. BTC Dominance...")
    dom = get_btc_dominance()
    if dom:
        print(f"   BTC: {dom['btc']:.2f}%")
        print(f"   ETH: {dom['eth']:.2f}%")
        print(f"   Total MCap: ${dom['total_mcap']/1e12:.2f}T")
    else:
        print("   ❌ Failed")
    
    print("\n3. Trending Coins...")
    trending = get_trending_coins()
    if trending:
        for c in trending[:5]:
            print(f"   #{c['market_cap_rank']} {c['symbol']} - {c['name']}")
    else:
        print("   ❌ Failed")
    
    print("\n4. Crypto News...")
    news = get_crypto_news()
    print(f"   Total fetched: {len(news)}")
    for n in news[:5]:
        impact = '🔴' if n['impact'] == 'HIGH' else '🟡'
        print(f"   {impact} [{n['source']}] {n['title'][:70]}")
    
    print("\n5. BTC-specific News...")
    btc_news = get_news_for_symbol('BTC/USDT')
    print(f"   BTC news: {len(btc_news)}")
    for n in btc_news[:3]:
        print(f"   • {n['title'][:70]}")
    
    print("\n6. Economic Events...")
    events = get_economic_events()
    print(f"   Events: {len(events)}")
    for e in events[:5]:
        print(f"   [{e['impact']}] {e['title'][:70]}")
    
    print("\n7. Market Sentiment Summary...")
    print(format_sentiment_hindi())
    
    print("\n✅ NEWS MODULE TEST COMPLETE")