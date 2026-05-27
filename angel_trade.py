#!/usr/bin/env python3
"""
Trade Notification System
Sends Telegram notifications when:
1. Stock price reaches entry price (Trade Triggered)
2. Stock price reaches target or stoploss (Position Closed)
"""

import os
import json
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
TELEGRAM_CHAT = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
RADAR_FILE = 'radar_trades.json'


def send_telegram(message: str) -> bool:
    """Send Telegram notification"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("⚠️ Telegram not configured")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={'chat_id': TELEGRAM_CHAT, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10
        )
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


def check_trade_triggers():
    """
    Monitor Radar tab stocks and send Telegram notifications:
    - When price = entry price → Trade Triggered
    - When price = target or stoploss → Position Closed
    """
    print(f"TRADE NOTIFICATION CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print("=" * 60)

    trades = load_radar()
    if not trades:
        print("No trades in radar_trades.json")
        return

    print(f"Checking {len(trades)} trades...")
    changed = False

    for trade in trades:
        ticker = trade.get('ticker', '')
        status = trade.get('status', '')
        entry_price = float(trade.get('entry_price', 0))
        current_price = float(trade.get('current_price', entry_price))
        target_price = float(trade.get('target', entry_price * 1.20))
        stoploss_price = float(trade.get('stop_loss', entry_price * 0.92))
        source = trade.get('source', 'Unknown')

        print(f"\n  {ticker}: Entry ₹{entry_price:.2f} | Current ₹{current_price:.2f} | Target ₹{target_price:.2f} | Stop ₹{stoploss_price:.2f}")

        # Check if trade was just triggered (price reached entry)
        if status == 'Pending' and current_price >= entry_price * 0.99:  # Within 1% of entry
            trade['status'] = 'Triggered'
            trade['triggered_at'] = datetime.now().isoformat()
            changed = True

            pnl_pct = ((current_price - entry_price) / entry_price) * 100
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
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            exit_reason = "Target Hit" if current_price >= target_price else "Stop Loss Hit"
            trade['status'] = 'Closed'
            trade['exit_price'] = current_price
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

    if changed:
        save_radar(trades)
        print(f"\nradar_trades.json updated")

    print("\nNotification check complete")


if __name__ == "__main__":
    check_trade_triggers()
