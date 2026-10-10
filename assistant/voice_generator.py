# ==================== VOICE GENERATOR v2 (edge-tts) ====================
# Kाम: Hindi voice alerts with natural sound + speed control

import os
import asyncio
import logging
from datetime import datetime

log = logging.getLogger(__name__)

VOICE_DIR = 'voice_alerts'
os.makedirs(VOICE_DIR, exist_ok=True)

# Voice settings
VOICE_NAME = "hi-IN-SwaraNeural"    # Female Hindi voice
VOICE_RATE = "+30%"                  # Speed boost (30% faster)
VOICE_VOLUME = "+0%"
VOICE_PITCH = "+0Hz"

# edge-tts check
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    log.warning("⚠️ edge-tts not installed. Run: pip install edge-tts")


def _clean_filename(symbol):
    return symbol.replace('/', '_').replace(' ', '')


def format_number_hindi(num):
    """Number को Hindi TTS के लिए format करो (decimal = 'पॉइंट')"""
    try:
        if num is None:
            return "शून्य"
        num = float(num)
        if num == int(num):
            return str(int(num))
        # 2 decimal places, dot को 'पॉइंट' से replace करो
        formatted = f"{num:.2f}"
        return formatted.replace(".", " पॉइंट ")
    except:
        return str(num)


async def _generate_voice_async(text, filepath):
    """edge-tts से voice generate करो"""
    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate=VOICE_RATE,
        volume=VOICE_VOLUME,
        pitch=VOICE_PITCH,
    )
    await communicate.save(filepath)


def generate_voice(symbol, signal_data, filename=None):
    """
    Hindi voice message बनाओ (edge-tts से, natural + faster)
    """
    if not EDGE_TTS_AVAILABLE:
        log.warning("edge-tts not available")
        return None

    try:
        direction = signal_data.get('direction', '')
        entry = signal_data.get('entry', 0)
        sl = signal_data.get('sl', 0)
        tp1 = signal_data.get('tp1', 0)
        tp2 = signal_data.get('tp2', 0)
        confidence = signal_data.get('confidence', 0)
        leverage = signal_data.get('leverage', 0)
        market_state = signal_data.get('market_state', 'NEUTRAL')

        # Action words
        if 'BUY' in direction:
            action = "खरीदने का"
        elif 'SELL' in direction:
            action = "बेचने का"
        else:
            action = ""

        coin_name = symbol.replace('/USDT', '').replace('/USD', '')

        # Coin Hindi names
        coin_hindi = {
            'BTC': 'बिटकॉइन',
            'ETH': 'एथेरियम',
            'SOL': 'सोलाना',
            'BNB': 'बी एन बी',
            'XRP': 'रिपल',
            'ADA': 'कार्डानो',
            'DOGE': 'डॉज कॉइन',
            'AVAX': 'एवलांच',
            'DOT': 'पोल्काडॉट',
            'LINK': 'चेनलिंक',
            'PAXG': 'गोल्ड',
            'XAUT': 'गोल्ड',
        }.get(coin_name, coin_name)

        # Market state Hindi
        state_hindi = {
            'TRENDING': 'मार्केट ट्रेंडिंग है।',
            'RANGING': 'मार्केट साइडवेज है।',
            'VOLATILE': 'मार्केट बहुत अस्थिर है।',
            'STRONG_TREND': 'मार्केट मजबूत ट्रेंड में है।',
            'NEUTRAL': 'मार्केट न्यूट्रल है।',
        }.get(market_state, '')

        # Numbers formatted
        entry_str = format_number_hindi(entry)
        sl_str = format_number_hindi(sl)
        tp1_str = format_number_hindi(tp1)
        tp2_str = format_number_hindi(tp2)
        lev_str = str(int(leverage)) if leverage else ""

        # Confidence text
        conf_int = int(confidence)
        if confidence >= 80:
            conf_text = f"कॉन्फिडेंस {conf_int} परसेंट। बहुत मजबूत सिग्नल।"
        elif confidence >= 70:
            conf_text = f"कॉन्फिडेंस {conf_int} परसेंट। अच्छा सिग्नल।"
        else:
            conf_text = f"कॉन्फिडेंस {conf_int} परसेंट। सावधानी से ट्रेड करो।"

        # Full text
        text_parts = [
            "भाई, ध्यान दो।",
            f"{coin_hindi} में {action} सिग्नल आया है।",
        ]
        if state_hindi:
            text_parts.append(state_hindi)
        text_parts.extend([
            f"एंट्री प्राइस {entry_str}।",
            f"स्टॉप लॉस लगाओ {sl_str} पर।",
            f"पहला टारगेट {tp1_str}।",
            f"दूसरा टारगेट {tp2_str}।",
        ])
        if lev_str:
            text_parts.append(f"लिवरेज {lev_str} गुना तक सुरक्षित है।")
        text_parts.extend([
            conf_text,
            "एक से दो परसेंट से ज्यादा रिस्क मत लो।",
            "ऑल द बेस्ट।",
        ])

        full_text = " ".join(text_parts)

        # Filename
        if filename is None:
            safe = _clean_filename(symbol)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe}_{ts}.mp3"

        filepath = os.path.join(VOICE_DIR, filename)

        # Run async
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # अगर loop already running है (जैसे async context में), to अलग thread use करो
            import threading
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_generate_voice_async(full_text, filepath))
                new_loop.close()
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
        else:
            loop.run_until_complete(_generate_voice_async(full_text, filepath))

        log.info(f"🔊 Voice saved: {filepath}")
        return filepath

    except Exception as e:
        log.error(f"Voice generation error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_simple_voice(text, filename=None):
    """कस्टम text का voice बनाओ"""
    if not EDGE_TTS_AVAILABLE:
        return None

    try:
        if filename is None:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"custom_{ts}.mp3"

        filepath = os.path.join(VOICE_DIR, filename)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import threading
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_generate_voice_async(text, filepath))
                new_loop.close()
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
        else:
            loop.run_until_complete(_generate_voice_async(text, filepath))

        log.info(f"🔊 Voice saved: {filepath}")
        return filepath
    except Exception as e:
        log.error(f"Voice error: {e}")
        return None


def cleanup_old_voices(days=1):
    """पुरानी voice files delete करो"""
    try:
        now = datetime.now()
        count = 0
        for f in os.listdir(VOICE_DIR):
            if f.endswith('.mp3'):
                path = os.path.join(VOICE_DIR, f)
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if (now - mtime).days > days:
                    os.remove(path)
                    count += 1
        if count:
            log.info(f"🧹 Cleaned {count} old voices")
    except Exception as e:
        log.debug(f"Cleanup error: {e}")


def is_available():
    return EDGE_TTS_AVAILABLE


# ==================== TEST ====================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

    print("=" * 60)
    print("🧪 VOICE GENERATOR v2 TEST (edge-tts)")
    print("=" * 60)

    if not EDGE_TTS_AVAILABLE:
        print("\n❌ edge-tts install नहीं है।")
        print("   Install: pip install edge-tts")
        exit(1)

    print(f"\n✅ edge-tts available")
    print(f"   Voice: {VOICE_NAME}")
    print(f"   Rate:  {VOICE_RATE}")

    # Test 1: BUY
    print("\n1. BUY signal voice (BTC)...")
    signal_buy = {
        'direction': 'BUY',
        'entry': 82950.50,
        'sl': 82100.75,
        'tp1': 84000.25,
        'tp2': 85000.00,
        'confidence': 78,
        'leverage': 15,
        'market_state': 'TRENDING',
    }
    path = generate_voice('BTC/USDT', signal_buy)
    if path:
        print(f"   ✅ {path}")
        print(f"   Size: {os.path.getsize(path)/1024:.1f} KB")

    # Test 2: SELL
    print("\n2. SELL signal voice (ETH)...")
    signal_sell = {
        'direction': 'SELL',
        'entry': 2497.33,
        'sl': 2510.80,
        'tp1': 2470.45,
        'tp2': 2440.60,
        'confidence': 72,
        'leverage': 10,
        'market_state': 'VOLATILE',
    }
    path = generate_voice('ETH/USDT', signal_sell)
    if path:
        print(f"   ✅ {path}")

    # Test 3: Gold
    print("\n3. Gold signal voice (PAXG)...")
    signal_gold = {
        'direction': 'BUY',
        'entry': 4200.50,
        'sl': 4150.25,
        'tp1': 4260.75,
        'tp2': 4330.00,
        'confidence': 82,
        'leverage': 20,
        'market_state': 'STRONG_TREND',
    }
    path = generate_voice('PAXG/USDT', signal_gold)
    if path:
        print(f"   ✅ {path}")

    # Test 4: Custom
    print("\n4. Custom Hindi voice...")
    path = generate_simple_voice("नमस्ते भाई। एंट्री प्राइस 62,000 पॉइंट 500 है।")
    if path:
        print(f"   ✅ {path}")

    cleanup_old_voices(days=7)

    print("\n✅ VOICE GENERATOR v2 TEST COMPLETE")
    print(f"📁 Voice folder: {os.path.abspath(VOICE_DIR)}")