# ==================== CHART GENERATOR (PRO v2) ====================
# Layout: Left = Clean Chart, Right = Signal Info Panel

import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

log = logging.getLogger(__name__)

CHARTS_DIR = 'charts'
os.makedirs(CHARTS_DIR, exist_ok=True)

# Colors
BG_COLOR = '#0d1117'
PANEL_COLOR = '#161b22'
GRID_COLOR = '#21262d'
TEXT_COLOR = '#c9d1d9'
TEXT_DIM = '#8b949e'
GREEN = '#26a69a'
RED = '#ef5350'
BLUE = '#2196f3'
ORANGE = '#ff9800'
YELLOW = '#ffeb3b'


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def generate_chart(symbol, df, signal_data=None, filename=None):
    """Professional chart with separate info panel"""
    if df is None or len(df) < 50:
        log.warning(f"Not enough data: {symbol}")
        return None

    try:
        # ---------- Prepare data ----------
        df_chart = df.copy().set_index('timestamp')
        df_chart = df_chart[['open', 'high', 'low', 'close', 'volume']]
        df_chart.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df_chart = df_chart.tail(80)

        df_chart['EMA_20'] = df_chart['Close'].ewm(span=20).mean()
        df_chart['EMA_50'] = df_chart['Close'].ewm(span=50).mean()
        df_chart['RSI'] = calculate_rsi(df_chart['Close'], 14)

        # ---------- Market colors & style ----------
        mc = mpf.make_marketcolors(
            up=GREEN, down=RED, edge='inherit',
            wick={'up': GREEN, 'down': RED},
            volume={'up': GREEN, 'down': RED},
        )

        style = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor=PANEL_COLOR,
            edgecolor=GRID_COLOR,
            figcolor=BG_COLOR,
            gridcolor=GRID_COLOR,
            gridstyle='-',
            gridaxis='both',
            y_on_right=False,
            rc={
                'axes.labelcolor': TEXT_COLOR,
                'xtick.color': TEXT_DIM,
                'ytick.color': TEXT_DIM,
                'font.size': 9,
                'axes.titlecolor': TEXT_COLOR,
            }
        )

        # ---------- Indicator addplots ----------
        addplots = [
            mpf.make_addplot(df_chart['EMA_20'], color=BLUE, width=1.0, panel=0),
            mpf.make_addplot(df_chart['EMA_50'], color=ORANGE, width=1.0, panel=0),
            mpf.make_addplot(df_chart['RSI'], color=YELLOW, width=1.0, panel=2, ylabel='RSI'),
        ]

        # ---------- Title ----------
        direction = signal_data.get('direction', '') if signal_data else ''
        confidence = signal_data.get('confidence', 0) if signal_data else 0
        arrow = '▲' if 'BUY' in direction else ('▼' if 'SELL' in direction else '●')
        title = f"\n{symbol}   {arrow}   {direction}"
        if confidence:
            title += f"   •   {confidence:.0f}% Conf"
        title += f"   •   15m   •   {datetime.now().strftime('%d %b %Y  %H:%M IST')}"

        # ---------- Filename ----------
        if filename is None:
            safe = symbol.replace('/', '_')
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe}_{ts}.png"
        filepath = os.path.join(CHARTS_DIR, filename)

        # ---------- Plot (with returnfig) ----------
        fig, axes = mpf.plot(
            df_chart,
            type='candle',
            style=style,
            title=title,
            ylabel='Price',
            ylabel_lower='Volume',
            volume=True,
            addplot=addplots,
            panel_ratios=(6, 2, 2),
            figsize=(18, 9),
            tight_layout=False,
            returnfig=True,
            warn_too_much_data=500,
            xrotation=15,
        )

        # ---------- Shrink all axes to left 68% ----------
        for ax in axes:
            if ax is None:
                continue
            pos = ax.get_position()
            ax.set_position([pos.x0, pos.y0, pos.width * 0.70, pos.height])

        # ---------- Add info panel on right ----------
        info_ax = fig.add_axes([0.735, 0.08, 0.245, 0.84])
        info_ax.set_xlim(0, 1)
        info_ax.set_ylim(0, 1)
        info_ax.set_xticks([])
        info_ax.set_yticks([])
        info_ax.set_facecolor(PANEL_COLOR)
        for spine in info_ax.spines.values():
            spine.set_edgecolor(GRID_COLOR)
            spine.set_linewidth(1.5)

        # ---------- Fill info panel ----------
        _draw_info_panel(info_ax, symbol, signal_data)

        # ---------- Overlays on price chart ----------
        ax_price = axes[0]
        ax_rsi = axes[4]

        if signal_data:
            _draw_chart_overlays(ax_price, df_chart, signal_data)

        # RSI lines
        if ax_rsi is not None:
            ax_rsi.axhline(70, color=RED, linestyle='--', linewidth=0.7, alpha=0.5)
            ax_rsi.axhline(30, color=GREEN, linestyle='--', linewidth=0.7, alpha=0.5)
            ax_rsi.axhline(50, color=GRID_COLOR, linestyle='-', linewidth=0.4, alpha=0.6)
            ax_rsi.set_ylim(0, 100)

        # ---------- Save ----------
        fig.savefig(filepath, dpi=110, bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)

        log.info(f"📊 Chart saved: {filepath}")
        return filepath

    except Exception as e:
        log.error(f"Chart error: {e}")
        import traceback
        traceback.print_exc()
        return None


def _draw_chart_overlays(ax, df_chart, signal_data):
    """Entry/SL/TP lines और signal marker on chart"""
    entry = signal_data.get('entry')
    sl = signal_data.get('sl')
    tp1 = signal_data.get('tp1')
    tp2 = signal_data.get('tp2')
    direction = signal_data.get('direction', '')

    last_x = len(df_chart) - 1

    # Risk/Reward zones
    if entry and sl:
        ax.fill_between([0, last_x + 8], sl, entry,
                        color=RED, alpha=0.06, zorder=1)
    if entry and tp2:
        ax.fill_between([0, last_x + 8], entry, tp2,
                        color=GREEN, alpha=0.06, zorder=1)

    # Lines with small labels
    label_x = last_x + 1

    if entry:
        ax.axhline(entry, color=BLUE, linestyle='-', linewidth=1.6, alpha=0.9, zorder=5)
        ax.text(label_x, entry, f' ENTRY\n {entry:.2f}',
                color=BLUE, fontsize=8, fontweight='bold',
                va='center', ha='left', zorder=6,
                bbox=dict(boxstyle='round,pad=0.25',
                          facecolor=PANEL_COLOR, edgecolor=BLUE, linewidth=1))

    if sl:
        ax.axhline(sl, color=RED, linestyle='--', linewidth=1.4, alpha=0.9, zorder=5)
        ax.text(label_x, sl, f' SL\n {sl:.2f}',
                color=RED, fontsize=8, fontweight='bold',
                va='center', ha='left', zorder=6,
                bbox=dict(boxstyle='round,pad=0.25',
                          facecolor=PANEL_COLOR, edgecolor=RED, linewidth=1))

    if tp1:
        ax.axhline(tp1, color=GREEN, linestyle='--', linewidth=1.2, alpha=0.85, zorder=5)
        ax.text(label_x, tp1, f' TP1 {tp1:.2f}',
                color=GREEN, fontsize=8, fontweight='bold',
                va='center', ha='left', zorder=6,
                bbox=dict(boxstyle='round,pad=0.2',
                          facecolor=PANEL_COLOR, edgecolor=GREEN, linewidth=0.8))

    if tp2:
        ax.axhline(tp2, color=GREEN, linestyle=':', linewidth=1.2, alpha=0.85, zorder=5)
        ax.text(label_x, tp2, f' TP2 {tp2:.2f}',
                color=GREEN, fontsize=8, fontweight='bold',
                va='center', ha='left', zorder=6,
                bbox=dict(boxstyle='round,pad=0.2',
                          facecolor=PANEL_COLOR, edgecolor=GREEN, linewidth=0.8))

    # Signal marker (big arrow)
    if entry:
        if 'BUY' in direction:
            ax.scatter([last_x], [entry], marker='^', s=350,
                       color=GREEN, edgecolor='white', linewidth=2,
                       zorder=10, label='BUY')
        else:
            ax.scatter([last_x], [entry], marker='v', s=350,
                       color=RED, edgecolor='white', linewidth=2,
                       zorder=10, label='SELL')


def _draw_info_panel(ax, symbol, signal_data):
    """Right-side panel में signal details"""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    if not signal_data:
        ax.text(0.5, 0.5, "No signal\n(Simple chart)",
                color=TEXT_DIM, fontsize=14, ha='center', va='center')
        return

    direction = signal_data.get('direction', 'N/A')
    entry = signal_data.get('entry', 0)
    sl = signal_data.get('sl', 0)
    tp1 = signal_data.get('tp1', 0)
    tp2 = signal_data.get('tp2', 0)
    confidence = signal_data.get('confidence', 0)
    rr1 = signal_data.get('rr1', 0)
    rr2 = signal_data.get('rr2', 0)
    leverage = signal_data.get('leverage', 0)
    leverage_reason = signal_data.get('leverage_reason', '')

    is_buy = 'BUY' in direction
    arrow = '▲' if is_buy else '▼'
    dir_color = GREEN if is_buy else RED

    y = 0.96

    # ===== Header =====
    ax.text(0.5, y, "SIGNAL DETAILS",
            color=TEXT_DIM, fontsize=10, ha='center', va='top',
            fontweight='bold', style='italic')
    y -= 0.05

    # ===== Direction =====
    ax.text(0.5, y, f"{arrow}  {direction}",
            color=dir_color, fontsize=22, ha='center', va='top',
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5',
                      facecolor=PANEL_COLOR, edgecolor=dir_color, linewidth=2))
    y -= 0.12

    # ===== Symbol & Timeframe =====
    ax.text(0.5, y, symbol,
            color=TEXT_COLOR, fontsize=13, ha='center', va='top',
            fontweight='bold')
    y -= 0.04
    ax.text(0.5, y, "Timeframe: 15m",
            color=TEXT_DIM, fontsize=9, ha='center', va='top')
    y -= 0.06

    # ===== Divider =====
    ax.plot([0.08, 0.92], [y, y], color=GRID_COLOR, linewidth=1)
    y -= 0.03

    # ===== Price Levels =====
    levels = [
        ("ENTRY", entry, BLUE, True),
        ("STOP LOSS", sl, RED, True),
        ("TAKE PROFIT 1", tp1, GREEN, False),
        ("TAKE PROFIT 2", tp2, GREEN, False),
    ]

    for label, value, color, bold in levels:
        # Label
        ax.text(0.10, y, label, color=TEXT_DIM, fontsize=10,
                ha='left', va='top', fontweight='bold' if bold else 'normal')
        # Value
        ax.text(0.92, y, f"{value:.2f}", color=color, fontsize=12,
                ha='right', va='top', fontweight='bold',
                fontfamily='monospace')
        y -= 0.06

    y -= 0.01
    ax.plot([0.08, 0.92], [y, y], color=GRID_COLOR, linewidth=1)
    y -= 0.04

    # ===== R:R Ratio =====
    ax.text(0.10, y, "Risk : Reward", color=TEXT_DIM, fontsize=10,
            ha='left', va='top')
    ax.text(0.92, y, f"1:{rr1:.1f} / 1:{rr2:.1f}", color=YELLOW,
            fontsize=11, ha='right', va='top', fontweight='bold',
            fontfamily='monospace')
    y -= 0.055

    # ===== Confidence =====
    ax.text(0.10, y, "Confidence", color=TEXT_DIM, fontsize=10,
            ha='left', va='top')
    ax.text(0.92, y, f"{confidence:.0f}%", color=YELLOW,
            fontsize=11, ha='right', va='top', fontweight='bold',
            fontfamily='monospace')
    y -= 0.055

    # ===== Leverage =====
    if leverage:
        ax.text(0.10, y, "Leverage", color=TEXT_DIM, fontsize=10,
                ha='left', va='top')
        ax.text(0.92, y, f"{leverage}x", color=YELLOW,
                fontsize=11, ha='right', va='top', fontweight='bold',
                fontfamily='monospace')
        y -= 0.055

    y -= 0.02
    ax.plot([0.08, 0.92], [y, y], color=GRID_COLOR, linewidth=1)
    y -= 0.04

    # ===== Legend =====
    ax.text(0.10, y, "LEGEND", color=TEXT_DIM, fontsize=9,
            ha='left', va='top', fontweight='bold', style='italic')
    y -= 0.05

    legend_items = [
        ("EMA 20", BLUE, '-'),
        ("EMA 50", ORANGE, '-'),
        ("Entry", BLUE, '-'),
        ("Stop Loss", RED, '--'),
        ("Take Profit", GREEN, '--'),
    ]

    for name, color, ls in legend_items:
        # Line sample
        ax.plot([0.10, 0.28], [y + 0.012, y + 0.012],
                color=color, linewidth=2, linestyle=ls)
        # Label
        ax.text(0.32, y, name, color=TEXT_COLOR, fontsize=9,
                ha='left', va='top')
        y -= 0.048


def generate_simple_chart(symbol, df, filename=None):
    return generate_chart(symbol, df, signal_data=None, filename=filename)


def cleanup_old_charts(days=1):
    try:
        now = datetime.now()
        count = 0
        for f in os.listdir(CHARTS_DIR):
            if f.endswith('.png'):
                path = os.path.join(CHARTS_DIR, f)
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if (now - mtime).days > days:
                    os.remove(path)
                    count += 1
        if count:
            log.info(f"🧹 Cleaned {count} old charts")
    except Exception as e:
        log.debug(f"Cleanup error: {e}")


# ==================== TEST ====================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

    print("=" * 60)
    print("🧪 PRO CHART GENERATOR v2 TEST")
    print("=" * 60)

    from data_hub import fetch_ohlcv

    print("\n1. Simple chart (BTC)...")
    df = fetch_ohlcv('BTC/USDT', '15m', 200)
    if df is not None:
        path = generate_simple_chart('BTC/USDT', df)
        if path:
            print(f"   ✅ {path}")
            print(f"   Size: {os.path.getsize(path)/1024:.1f} KB")

    print("\n2. BUY signal chart (ETH)...")
    df_eth = fetch_ohlcv('ETH/USDT', '15m', 200)
    if df_eth is not None:
        price = float(df_eth['close'].iloc[-1])
        atr = float((df_eth['high'] - df_eth['low']).rolling(14).mean().iloc[-1])
        sl = price - (2 * atr)
        tp1 = price + (2.5 * atr)
        tp2 = price + (5 * atr)
        risk = price - sl
        rr1 = (tp1 - price) / risk
        rr2 = (tp2 - price) / risk

        signal = {
            'entry': price, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
            'direction': 'BUY', 'confidence': 78,
            'rr1': rr1, 'rr2': rr2,
            'leverage': 15, 'leverage_reason': 'Confidence 78%, ATR 1.2%',
        }
        path = generate_chart('ETH/USDT', df_eth, signal_data=signal)
        if path:
            print(f"   ✅ {path}")

    print("\n3. SELL signal chart (BTC)...")
    df_btc = fetch_ohlcv('BTC/USDT', '15m', 200)
    if df_btc is not None:
        price = float(df_btc['close'].iloc[-1])
        atr = float((df_btc['high'] - df_btc['low']).rolling(14).mean().iloc[-1])
        sl = price + (2 * atr)
        tp1 = price - (2.5 * atr)
        tp2 = price - (5 * atr)
        risk = sl - price
        rr1 = (price - tp1) / risk
        rr2 = (price - tp2) / risk

        signal = {
            'entry': price, 'sl': sl, 'tp1': tp1, 'tp2': tp2,
            'direction': 'SELL', 'confidence': 72,
            'rr1': rr1, 'rr2': rr2,
            'leverage': 10, 'leverage_reason': 'Confidence 72%, ATR 1.5%',
        }
        path = generate_chart('BTC/USDT', df_btc, signal_data=signal)
        if path:
            print(f"   ✅ {path}")

    cleanup_old_charts(days=7)

    print("\n✅ CHART GENERATOR v2 TEST COMPLETE")
    print(f"📁 Charts: {os.path.abspath(CHARTS_DIR)}")