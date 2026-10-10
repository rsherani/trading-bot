# ==================== MAIN ASSISTANT BOT (Layer 6) ====================
# काम: Telegram interface — सब modules को जोड़ता है

import os
import logging
import asyncio
import time
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes,
)

# ==================== IMPORTS ====================
from config import (
    FIXED_WATCHLIST, AUTO_TOP_COUNT,
    SCAN_INTERVAL_NORMAL, SETUP_MONITOR_INTERVAL,
    MAX_ACTIVE_SETUPS, DEFAULT_LEVERAGE, DEFAULT_RISK_PCT,
    MIN_CONFIDENCE,
)
from data_hub import (
    fetch_ohlcv, get_watchlist, get_top_volume_pairs,
    fetch_fear_greed, fetch_btc_dominance,
)
from memory import (
    init_db, save_conversation, get_recent_conversations,
    get_last_symbol, set_preference, get_preference,
    get_active_setups, get_open_trades, get_trade_history,
    get_weekly_stats, open_trade, close_trade, log_alert,
)
from nlp import (
    parse_message, format_greeting, format_thanks,
    format_help, format_unknown,
)
from knowledge import format_concept_reply, format_strategy_reply, KNOWLEDGE_BASE, STRATEGIES
from analyzer import analyze
from predictive import (
    scan_for_setups, update_setup_states,
    format_watch_alert, format_prepare_alert,
    format_trigger_alert, format_invalidated_alert,
    send_telegram as predictive_send,
)
from news import (
    format_sentiment_hindi, get_market_sentiment,
    get_news_for_symbol, get_economic_events,
)
from chart_generator import generate_chart, cleanup_old_charts
from voice_generator import generate_voice, cleanup_old_voices, is_available as voice_available

# ==================== CONFIG ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
log = logging.getLogger(__name__)

ASSISTANT_TOKEN = os.environ.get("ASSISTANT_TOKEN")
USER_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Global state
BOT_STATE = {
    'alerts_enabled': True,
    'alert_mode': 'normal',      # normal, silent, aggressive
    'paused_until': 0,
    'last_scan_time': 0,
    'chart_enabled': True,
    'voice_enabled': True,
}


# ==================== UTILITY ====================
def is_authorized(update: Update) -> bool:
    """सिर्फ owner ही use कर सके"""
    try:
        return str(update.effective_chat.id) == str(USER_CHAT_ID)
    except:
        return False


def is_paused() -> bool:
    return time.time() < BOT_STATE['paused_until']


async def send_chart_and_text(bot, chat_id, text, symbol, signal_data):
    """Chart + text send करो"""
    if BOT_STATE['chart_enabled'] and signal_data:
        try:
            chart_path = generate_chart(symbol, fetch_ohlcv(symbol, '15m', 200), signal_data)
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as f:
                    await bot.send_photo(chat_id=chat_id, photo=f, caption=text[:1000],
                                         parse_mode='HTML')
                return
        except Exception as e:
            log.error(f"Chart send error: {e}")
    # Fallback: text only
    await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')


async def send_voice_alert(bot, chat_id, symbol, signal_data):
    """Voice alert send करो"""
    if not BOT_STATE['voice_enabled'] or not voice_available():
        return
    try:
        voice_path = generate_voice(symbol, signal_data)
        if voice_path and os.path.exists(voice_path):
            with open(voice_path, 'rb') as f:
                await bot.send_voice(chat_id=chat_id, voice=f)
    except Exception as e:
        log.error(f"Voice send error: {e}")


# ==================== COMMAND HANDLERS ====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(format_greeting(), parse_mode='HTML')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(format_help(), parse_mode='HTML')


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    hours = 1
    if context.args and context.args[0].isdigit():
        hours = int(context.args[0])
    BOT_STATE['paused_until'] = time.time() + (hours * 3600)
    await update.message.reply_text(
        f"⏸️ Alerts paused for {hours} hour(s).\n"
        f"Resume with /resume",
        parse_mode='HTML'
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['paused_until'] = 0
    BOT_STATE['alerts_enabled'] = True
    await update.message.reply_text("▶️ Alerts resumed!", parse_mode='HTML')


async def cmd_silent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['alert_mode'] = 'silent'
    await update.message.reply_text(
        "🔇 <b>Silent Mode</b>\n"
        "अब सिर्फ 80%+ confidence वाले signals आएंगे।",
        parse_mode='HTML'
    )


async def cmd_aggressive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['alert_mode'] = 'aggressive'
    await update.message.reply_text(
        "🚀 <b>Aggressive Mode</b>\n"
        "अब 60%+ confidence वाले signals आएंगे।",
        parse_mode='HTML'
    )


async def cmd_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['alert_mode'] = 'normal'
    await update.message.reply_text("⚖️ Normal mode activated", parse_mode='HTML')


async def cmd_chart_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['chart_enabled'] = True
    await update.message.reply_text("📊 Charts ON", parse_mode='HTML')


async def cmd_chart_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['chart_enabled'] = False
    await update.message.reply_text("📊 Charts OFF", parse_mode='HTML')


async def cmd_voice_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['voice_enabled'] = True
    await update.message.reply_text("🔊 Voice ON", parse_mode='HTML')


async def cmd_voice_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    BOT_STATE['voice_enabled'] = False
    await update.message.reply_text("🔇 Voice OFF", parse_mode='HTML')


async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    wl = get_watchlist()
    text = "📋 <b>वर्तमान Watchlist:</b>\n\n"
    for i, sym in enumerate(wl, 1):
        text += f"{i}. {sym}\n"
    text += f"\n<b>Total:</b> {len(wl)} coins"
    await update.message.reply_text(text, parse_mode='HTML')


async def cmd_setups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    setups = get_active_setups()
    if not setups:
        await update.message.reply_text("📭 अभी कोई active setup नहीं है।")
        return
    text = f"🎯 <b>Active Setups ({len(setups)}):</b>\n\n"
    for s in setups:
        emoji = '🟢' if s['direction'] == 'BUY' else '🔴'
        text += f"{emoji} <b>{s['symbol']}</b> [{s['state']}]\n"
        text += f"   Trigger: {s['trigger_level']:.2f}\n"
        text += f"   Entry: {s['entry']:.2f} | SL: {s['stop_loss']:.2f}\n"
        text += f"   Conf: {s['confidence']:.0f}%\n\n"
    await update.message.reply_text(text, parse_mode='HTML')


async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    trades = get_trade_history(20)
    if not trades:
        await update.message.reply_text("📭 अभी तक कोई trade नहीं है।")
        return
    text = f"📓 <b>Trade History (Last {len(trades)}):</b>\n\n"
    for t in trades[:10]:
        emoji = '🟢' if t['direction'] == 'BUY' else '🔴'
        pnl = t.get('pnl_pct') or 0
        pnl_emoji = '✅' if pnl > 0 else ('❌' if pnl < 0 else '⚪')
        text += f"{emoji} <b>{t['symbol']}</b> {pnl_emoji} {pnl:+.2f}%\n"
    await update.message.reply_text(text, parse_mode='HTML')


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    s = get_weekly_stats()
    text = "📊 <b>Weekly Performance</b>\n\n"
    text += f"<b>Total Trades:</b> {s['total_trades']}\n"
    text += f"🟢 Wins: {s['wins']}\n"
    text += f"🔴 Losses: {s['losses']}\n"
    if s['avg_pnl']:
        text += f"<b>Avg PnL:</b> {s['avg_pnl']:+.2f}%\n"
    if s['total_trades'] > 0:
        wr = (s['wins'] / s['total_trades']) * 100
        text += f"<b>Win Rate:</b> {wr:.1f}%\n"
    await update.message.reply_text(text, parse_mode='HTML')


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    text = format_sentiment_hindi()
    await update.message.reply_text(text, parse_mode='HTML')


async def cmd_leverage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if context.args and context.args[0].isdigit():
        lev = int(context.args[0])
        if 1 <= lev <= 50:
            set_preference('default_leverage', lev)
            await update.message.reply_text(f"✅ Default leverage set to {lev}x")
        else:
            await update.message.reply_text("❌ 1-50 के बीच लिखो")
    else:
        current = get_preference('default_leverage', DEFAULT_LEVERAGE)
        await update.message.reply_text(f"Current leverage: {current}x\nUsage: /leverage 15")


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if context.args and context.args[0].replace('.', '').isdigit():
        risk = float(context.args[0])
        if 0.5 <= risk <= 5.0:
            set_preference('risk_pct', risk)
            await update.message.reply_text(f"✅ Risk per trade: {risk}%")
        else:
            await update.message.reply_text("❌ 0.5-5% के बीच लिखो")
    else:
        current = get_preference('risk_pct', DEFAULT_RISK_PCT)
        await update.message.reply_text(f"Current risk: {current}%\nUsage: /risk 2")


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    top = get_top_volume_pairs(10)
    text = "🏆 <b>Top 10 by Volume:</b>\n\n"
    for i, sym in enumerate(top, 1):
        text += f"{i}. {sym}\n"
    await update.message.reply_text(text, parse_mode='HTML')


# ==================== MESSAGE HANDLER (Hindi NLP) ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    
    user_text = update.message.text.strip()
    user_id = str(update.effective_chat.id)
    
    if not user_text:
        return
    
    # Send "thinking" message
    thinking = await update.message.reply_text("🤔 सोच रहा हूँ...")
    
    try:
        parsed = parse_message(user_text)
        intent = parsed['intent']
        symbols = parsed['symbols']
        concept = parsed['concept']
        strategy = parsed['strategy']
        
        # ---------- Route by intent ----------
        
        # 1. Greeting
        if intent == 'greeting':
            reply = format_greeting()
            await thinking.edit_text(reply, parse_mode='HTML')
        
        # 2. Thanks
        elif intent == 'thanks':
            reply = format_thanks()
            await thinking.edit_text(reply, parse_mode='HTML')
        
        # 3. Help
        elif intent == 'help':
            reply = format_help()
            await thinking.edit_text(reply, parse_mode='HTML')
        
        # 4. Learn concept
        elif concept:
            reply = format_concept_reply(concept)
            if reply:
                await thinking.edit_text(reply, parse_mode='HTML')
            else:
                await thinking.edit_text("🤔 भाई, वो concept नहीं मिला।")
        
        # 5. Strategy question
        elif strategy:
            reply = format_strategy_reply(strategy)
            if reply:
                await thinking.edit_text(reply, parse_mode='HTML')
            else:
                await thinking.edit_text("🤔 भाई, वो strategy नहीं मिली।")
        
        # 6. News / sentiment
        elif intent == 'market_question':
            reply = format_sentiment_hindi()
            await thinking.edit_text(reply, parse_mode='HTML')
        
        # 7. Portfolio
        elif intent == 'portfolio':
            trades = get_open_trades()
            if not trades:
                await thinking.edit_text("📭 कोई open trade नहीं है।")
            else:
                text = f"💼 <b>Open Trades ({len(trades)}):</b>\n\n"
                for t in trades:
                    emoji = '🟢' if t['direction'] == 'BUY' else '🔴'
                    text += f"{emoji} {t['symbol']} @ {t['entry']:.2f}\n"
                await thinking.edit_text(text, parse_mode='HTML')
        
        # 8. Stats
        elif intent == 'stats':
            s = get_weekly_stats()
            text = f"📊 <b>Weekly Stats</b>\n\n"
            text += f"Trades: {s['total_trades']}\n"
            text += f"Wins: {s['wins']} | Losses: {s['losses']}\n"
            if s['total_trades'] > 0:
                wr = (s['wins'] / s['total_trades']) * 100
                text += f"Win Rate: {wr:.1f}%\n"
            await thinking.edit_text(text, parse_mode='HTML')
        
        # 9. Analysis (यह सबसे जरूरी है)
        elif intent in ('analysis', 'buy_question', 'sell_question', 'trend_question',
                        'should_i', 'entry', 'stop_loss', 'target', 'leverage', 'quantity'):
            if not symbols:
                last_sym = get_last_symbol(user_id)
                if last_sym:
                    symbols = [last_sym.replace('/USDT', '').replace('/USD', '')]
            
            if not symbols:
                await thinking.edit_text(
                    "🤔 भाई, किस coin के बारे में पूछ रहे हो?\n\n"
                    "जैसे: <code>BTC कैसा है?</code>",
                    parse_mode='HTML'
                )
                save_conversation(user_id, user_text, 'no_symbol', intent, '')
                return
            
            # Analyze first symbol
            coin = symbols[0]
            full_symbol = coin + '/USDT' if '/' not in coin else coin
            
            # Update thinking
            try:
                await thinking.edit_text(f"🔍 <b>{full_symbol}</b> का एनालिसिस हो रहा है...\n(30-60 सेकंड लगेंगे)", parse_mode='HTML')
            except:
                pass
            
            # Run analysis
            result = analyze(full_symbol)
            
            if result is None:
                await thinking.edit_text(f"❌ {full_symbol} का डेटा नहीं मिला।")
                return
            
            # Build Hindi response
            reply = build_analysis_reply(result, intent)
            
            # Delete thinking message
            try:
                await thinking.delete()
            except:
                pass
            
            # Send chart + text
            signal_data = None
            if result.get('verdict') != 'NO_TRADE':
                signal_data = {
                    'entry': result.get('entry', 0),
                    'sl': result.get('sl', 0),
                    'tp1': result.get('tp1', 0),
                    'tp2': result.get('tp2', 0),
                    'direction': result.get('verdict', ''),
                    'confidence': result.get('strength', 0),
                    'rr1': result.get('rr1', 0),
                    'rr2': result.get('rr2', 0),
                    'leverage': result.get('leverage', 0),
                    'leverage_reason': result.get('leverage_reason', ''),
                    'market_state': result.get('market_state', 'NEUTRAL'),
                }
            
            await send_chart_and_text(
                context.bot,
                update.effective_chat.id,
                reply,
                full_symbol,
                signal_data if BOT_STATE['chart_enabled'] else None
            )
            
            # Save
            save_conversation(user_id, user_text, reply[:500], intent, full_symbol)
        
        # 10. Fallback
        else:
            reply = format_unknown(user_text, symbols)
            await thinking.edit_text(reply, parse_mode='HTML')
            save_conversation(user_id, user_text, reply[:200], intent, ','.join(symbols))
    
    except Exception as e:
        log.error(f"Message handling error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await thinking.edit_text(
                f"❌ भाई, कुछ गड़बड़ हो गई। फिर से try करो।\n<i>Error: {str(e)[:100]}</i>",
                parse_mode='HTML'
            )
        except:
            pass


def build_analysis_reply(result, intent):
    """Analysis result को Hindi reply में बदलो"""
    symbol = result['symbol']
    verdict = result.get('verdict', 'NO_TRADE')
    price = result.get('price', 0)
    
    if verdict == 'NO_TRADE':
        reply = f"📊 <b>{symbol}</b>\n\n"
        reply += f"💰 कीमत: <code>{price:.2f}</code>\n"
        reply += f"⏸️ <b>अभी कोई साफ सिग्नल नहीं है।</b>\n\n"
        reply += f"<b>कारण:</b> {result.get('reason', 'No consensus')}\n\n"
        
        # Sector details
        sectors = result.get('sectors', {})
        if sectors:
            reply += "<b>सेक्टर विश्लेषण:</b>\n"
            for name, data in sectors.items():
                sig = data.get('signal', 'NEUTRAL')
                icon = '🟢' if sig == 'BULLISH' else ('🔴' if sig == 'BEARISH' else '⚪')
                reply += f"{icon} {name.upper()}: {data.get('reason', '')[:60]}\n"
        return reply
    
    # Signal case
    dir_hindi = "खरीदने (BUY)" if verdict == 'BUY' else "बेचने (SELL)"
    
    reply = f"📊 <b>{symbol}</b>\n"
    reply += f"💰 कीमत: <code>{price:.2f}</code>\n\n"
    reply += f"🎯 <b>सिग्नल:</b> {dir_hindi} का मौका\n"
    reply += f"📊 <b>Market State:</b> {result.get('market_state', 'N/A')}\n"
    reply += f"💪 <b>Confidence:</b> {result.get('strength', 0):.0f}%\n"
    reply += f"🤝 <b>सहमत सेक्टर:</b> {result.get('agreeing', 0)}/4\n\n"
    
    reply += f"<b>📍 ट्रेड सेटअप:</b>\n"
    reply += f"एंट्री: <code>{result.get('entry', 0):.2f}</code>\n"
    reply += f"स्टॉप लॉस: <code>{result.get('sl', 0):.2f}</code>\n"
    reply += f"टारगेट 1: <code>{result.get('tp1', 0):.2f}</code> (1:{result.get('rr1', 0):.1f})\n"
    reply += f"टारगेट 2: <code>{result.get('tp2', 0):.2f}</code> (1:{result.get('rr2', 0):.1f})\n\n"
    
    lev = result.get('leverage', 0)
    if lev:
        reply += f"🎚️ <b>Leverage:</b> {lev}x max (सुरक्षित)\n\n"
    
    # Reasons
    reasons = result.get('reasons', [])
    if reasons:
        reply += f"<b>🔍 कारण:</b>\n"
        for r in reasons[:5]:
            reply += f"{r}\n"
    
    reply += f"\n⚠️ <i>Position: Capital का 2% max. SL जरूर लगाना।</i>"
    return reply


# ==================== BACKGROUND TASKS ====================
async def background_scan(bot):
    """Background loop — setups scan + monitor"""
    log.info("🚀 Background scanner started")
    last_scan = 0
    
    while True:
        try:
            if is_paused():
                await asyncio.sleep(60)
                continue
            
            now = time.time()
            
            # Scan for new setups
            if now - last_scan >= SCAN_INTERVAL_NORMAL:
                active = get_active_setups()
                if len(active) < MAX_ACTIVE_SETUPS:
                    log.info(f"🔍 Scanning ({len(active)} active)...")
                    created = scan_for_setups(max_new=2)
                    if created:
                        log.info(f"✅ Created {created} setups")
                last_scan = now
            
            # Monitor active setups
            alerts = update_setup_states()
            for atype, setup, price in alerts:
                # Filter by alert mode
                conf = setup.get('confidence', 0)
                mode = BOT_STATE['alert_mode']
                if mode == 'silent' and conf < 80:
                    continue
                if mode == 'aggressive' and conf < 60:
                    continue
                if mode == 'normal' and conf < MIN_CONFIDENCE:
                    continue
                
                # Format message
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
                
                # Send text
                try:
                    await bot.send_message(chat_id=USER_CHAT_ID, text=msg, parse_mode='HTML')
                except Exception as e:
                    log.error(f"Alert send error: {e}")
                    continue
                
                # If TRIGGER → chart + voice
                if atype == 'TRIGGER':
                    signal_data = {
                        'entry': setup.get('entry', 0),
                        'sl': setup.get('stop_loss', 0),
                        'tp1': setup.get('target1', 0),
                        'tp2': setup.get('target2', 0),
                        'direction': setup.get('direction', ''),
                        'confidence': setup.get('confidence', 0),
                        'leverage': setup.get('leverage_suggested', 0),
                        'market_state': 'TRENDING',
                    }
                    # Chart
                    if BOT_STATE['chart_enabled']:
                        try:
                            chart_path = generate_chart(setup['symbol'], fetch_ohlcv(setup['symbol'], '15m', 200), signal_data)
                            if chart_path and os.path.exists(chart_path):
                                with open(chart_path, 'rb') as f:
                                    await bot.send_photo(chat_id=USER_CHAT_ID, photo=f)
                        except Exception as e:
                            log.error(f"Trigger chart error: {e}")
                    
                    # Voice
                    await send_voice_alert(bot, USER_CHAT_ID, setup['symbol'], signal_data)
                    
                    # Auto-save to journal
                    try:
                        open_trade(
                            symbol=setup['symbol'],
                            direction=setup['direction'],
                            entry=setup.get('entry', 0),
                            sl=setup.get('stop_loss', 0),
                            tp1=setup.get('target1', 0),
                            tp2=setup.get('target2', 0),
                            leverage=setup.get('leverage_suggested', DEFAULT_LEVERAGE),
                            size=0,
                            setup_id=setup['id'],
                        )
                    except Exception as e:
                        log.error(f"Journal save error: {e}")
            
            await asyncio.sleep(SETUP_MONITOR_INTERVAL)
        
        except Exception as e:
            log.error(f"Background scan error: {e}")
            await asyncio.sleep(60)


async def periodic_cleanup():
    """Cleanup old charts/voices every hour"""
    while True:
        try:
            await asyncio.sleep(3600)
            cleanup_old_charts(days=1)
            cleanup_old_voices(days=1)
        except Exception as e:
            log.error(f"Cleanup error: {e}")


async def post_init(app: Application):
    """Bot startup — commands + background tasks"""
    # Set commands
    commands = [
        BotCommand("start", "Start"),
        BotCommand("help", "Help"),
        BotCommand("watchlist", "View watchlist"),
        BotCommand("setups", "Active setups"),
        BotCommand("journal", "Trade history"),
        BotCommand("stats", "Weekly stats"),
        BotCommand("news", "Market sentiment"),
        BotCommand("top", "Top 10 coins"),
        BotCommand("pause", "Pause alerts"),
        BotCommand("resume", "Resume alerts"),
        BotCommand("silent", "Silent mode"),
        BotCommand("aggressive", "Aggressive mode"),
        BotCommand("normal", "Normal mode"),
        BotCommand("chart_on", "Enable charts"),
        BotCommand("chart_off", "Disable charts"),
        BotCommand("voice_on", "Enable voice"),
        BotCommand("voice_off", "Disable voice"),
        BotCommand("leverage", "Set leverage"),
        BotCommand("risk", "Set risk %"),
    ]
    await app.bot.set_my_commands(commands)
    
    # Startup message
    try:
        await app.bot.send_message(
            chat_id=USER_CHAT_ID,
            text=(
                "🏛️ <b>AI Trading Assistant</b> लाइव हो गया!\n\n"
                "✅ सभी modules ready हैं\n"
                "✅ Background scanning चालू\n"
                "✅ Charts + Voice alerts enabled\n\n"
                "बस हिंदी में पूछो, मैं जवाब दूँगा।\n"
                "<code>BTC कैसा है?</code> टाइप करके test करो।"
            ),
            parse_mode='HTML'
        )
    except Exception as e:
        log.error(f"Startup message error: {e}")
    
    # Start background tasks
    asyncio.create_task(background_scan(app.bot))
    asyncio.create_task(periodic_cleanup())
    log.info("✅ Background tasks started")


# ==================== MAIN ====================
def main():
    if not ASSISTANT_TOKEN:
        print("❌ ASSISTANT_TOKEN नहीं मिला")
        return
    if not USER_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID नहीं मिला")
        return
    
    log.info("=" * 60)
    log.info("🏛️ AI TRADING ASSISTANT STARTING")
    log.info("=" * 60)
    
    # Initialize DB
    init_db()
    log.info("✅ Database ready")
    
    # Build app
    app = Application.builder().token(ASSISTANT_TOKEN).post_init(post_init).build()
    
    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("silent", cmd_silent))
    app.add_handler(CommandHandler("aggressive", cmd_aggressive))
    app.add_handler(CommandHandler("normal", cmd_normal))
    app.add_handler(CommandHandler("chart_on", cmd_chart_on))
    app.add_handler(CommandHandler("chart_off", cmd_chart_off))
    app.add_handler(CommandHandler("voice_on", cmd_voice_on))
    app.add_handler(CommandHandler("voice_off", cmd_voice_off))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("setups", cmd_setups))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("leverage", cmd_leverage))
    app.add_handler(CommandHandler("risk", cmd_risk))
    app.add_handler(CommandHandler("top", cmd_top))
    
    # Message handler (any text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    log.info("✅ Handlers registered")
    log.info("🚀 Bot polling started...")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()