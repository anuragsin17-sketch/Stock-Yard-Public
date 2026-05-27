#!/usr/bin/env python3
"""
Radar Position Monitor
- Monitors Radar tab stocks for price triggers
- Sends Telegram when price reaches entry, target, or stoploss
- Updates radar_trades.json with current prices and status
"""

import os
import json
import requests
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT = os.environ.get('TELEGRAM_CHAT_ID')
RADAR_FILE = 'radar_trades.json'


def send_telegram(message: str) -> bool:
    """Send Telegram notification"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("⚠️ Telegram not configured")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            'chat_id': TELEGRAM_CHAT,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        if resp.status_code == 200:
            print("✅ Telegram sent")
            return True
        print(f"❌ Telegram failed: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
    return False


def load_radar() -> list:
    """Load radar trades from file"""
    if not os.path.exists(RADAR_FILE):
        return []
    try:
        with open(RADAR_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading radar trades: {e}")
        return []


def save_radar(trades: list):
    """Save radar trades to file"""
    try:
        with open(RADAR_FILE, 'w') as f:
            json.dump(trades, f, indent=2)
    except Exception as e:
        print(f"Error saving radar trades: {e}")


def get_live_price(ticker: str) -> float:
    """Get current price via yfinance"""
    try:
        symbol = ticker + '.NS' if not ticker.endswith('.NS') else ticker
        data = yf.download(symbol, period='1d', interval='1m',
                           progress=False, auto_adjust=True)
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"Price fetch error for {ticker}: {e}")
    return None


def monitor_radar_positions():
    """
    Monitor Radar tab stocks and send Telegram notifications:
    - When price reaches entry price → Trade Triggered
    - When price reaches target or stoploss → Position Closed
    """
    print(f"RADAR MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print("=" * 60)

    trades = load_radar()
    if not trades:
        print("No trades in radar_trades.json")
        return

    triggered_trades = [t for t in trades if t.get('status') in ['Pending', 'Triggered']]
    if not triggered_trades:
        print("No pending or triggered trades to monitor")
        return

    print(f"Monitoring {len(triggered_trades)} trades...")
    changed = False

    for trade in trades:
        status = trade.get('status', '')
        if status not in ['Pending', 'Triggered']:
            continue

        ticker = trade.get('ticker', '')
        entry_price = float(trade.get('entry_price', 0))
        target_price = float(trade.get('target', entry_price * 1.20))
        stoploss_price = float(trade.get('stop_loss', entry_price * 0.92))
        source = trade.get('source', 'Unknown')

        print(f"\n  {ticker}: Entry ₹{entry_price:.2f} | Target ₹{target_price:.2f} | Stop ₹{stoploss_price:.2f}")

        # Get live price
        current_price = get_live_price(ticker)
        if not current_price:
            print(f"  Could not get price for {ticker}")
            continue

        print(f"  Current price: ₹{current_price:.2f}")

        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        print(f"  P&L: {pnl_pct:+.2f}%")

        # Check if trade was just triggered (price reached entry)
        if status == 'Pending' and current_price >= entry_price * 0.99:  # Within 1% of entry
            trade['status'] = 'Triggered'
            trade['triggered_at'] = datetime.now().isoformat()
            changed = True

            msg = (
                f"🎯 *TRADE TRIGGERED*\n\n"
                f"Stock: *{ticker}*\n"
                f"Entry Price: ₹{entry_price:,.2f}\n"
                f"Current Price: ₹{current_price:,.2f}\n"
                f"Target: ₹{target_price:,.2f} _(+20%)_\n"
                f"Stop Loss: ₹{stoploss_price:,.2f} _(8% loss)_\n"
                f"Source: {source}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}"
            )
            send_telegram(msg)
            print(f"  ✅ Trade Triggered - Telegram sent!")

        # Check if position should be closed (target or stoploss hit)
        elif status == 'Triggered' and (current_price >= target_price or current_price <= stoploss_price):
            exit_reason = "Target Hit" if current_price >= target_price else "Stop Loss Hit"
            trade['status'] = 'Closed'
            trade['exit_price'] = round(current_price, 2)
            trade['closed_at'] = datetime.now().isoformat()
            trade['pnl_pct'] = round(pnl_pct, 2)
            trade['exit_reason'] = exit_reason
            changed = True

            icon = "🎯" if current_price >= target_price else "🛑"
            msg = (
                f"{icon} *POSITION CLOSED - {exit_reason}*\n\n"
                f"Stock: *{ticker}*\n"
                f"Entry: ₹{entry_price:,.2f}\n"
                f"Exit: ₹{current_price:,.2f}\n"
                f"P&L: *{pnl_pct:+.2f}%*\n"
                f"Source: {source}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}"
            )
            send_telegram(msg)
            print(f"  ✅ {exit_reason} - Telegram sent!")

        else:
            # Still open - update current price silently
            trade['current_price'] = round(current_price, 2)
            trade['current_pnl_pct'] = round(pnl_pct, 2)
            changed = True
            print(f"  Still open - P&L: {pnl_pct:+.2f}%")

    if changed:
        save_radar(trades)
        print(f"\nradar_trades.json updated")

    print("\nMonitoring complete")


if __name__ == "__main__":
    monitor_radar_positions()
