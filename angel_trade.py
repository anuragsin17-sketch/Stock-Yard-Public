#!/usr/bin/env python3
"""
Trade Notification Trigger
Sends Telegram notification when a trade is manually confirmed
Can be called from UI or webhook
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
    """Load radar trades"""
    if not os.path.exists(RADAR_FILE):
        return []
    try:
        with open(RADAR_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def save_radar(trades: list):
    """Save radar trades"""
    try:
        with open(RADAR_FILE, 'w') as f:
            json.dump(trades, f, indent=2)
    except Exception as e:
        print(f"Error saving radar trades: {e}")


def notify_trade_confirmation(ticker: str, entry_price: float, target_price: float, 
                              stoploss_price: float, source: str = 'Manual'):
    """
    Send Telegram notification for a manually confirmed trade
    
    Args:
        ticker: Stock symbol
        entry_price: Entry price
        target_price: Target price (20% gain)
        stoploss_price: Stop loss price (8% loss)
        source: Source of the trade (Volume, Trendline, Manual)
    """
    print(f"\n{'='*60}")
    print(f"TRADE CONFIRMATION - {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*60}")
    print(f"Stock: {ticker}")
    print(f"Entry: ₹{entry_price:.2f}")
    print(f"Target: ₹{target_price:.2f}")
    print(f"Stop Loss: ₹{stoploss_price:.2f}")
    print(f"Source: {source}")

    # Add to radar
    radar_trades = load_radar()
    
    # Check if already exists
    if any(t.get('ticker') == ticker and t.get('status') in ['Triggered', 'Pending'] for t in radar_trades):
        print(f"⚠️ {ticker} already in Radar")
        return False

    radar_trades.append({
        'ticker': ticker,
        'source': source,
        'entry_price': round(entry_price, 2),
        'target': round(target_price, 2),
        'stop_loss': round(stoploss_price, 2),
        'status': 'Pending',
        'confirmed_at': datetime.now().isoformat()
    })
    save_radar(radar_trades)

    # Send Telegram
    msg = (
        f"✅ *TRADE CONFIRMED*\n\n"
        f"Stock: *{ticker}*\n"
        f"Entry Price: ₹{entry_price:,.2f}\n"
        f"Target: ₹{target_price:,.2f} _(+20%)_\n"
        f"Stop Loss: ₹{stoploss_price:,.2f} _(8% loss)_\n"
        f"Source: {source}\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}\n\n"
        f"Waiting for entry price to be hit..."
    )
    send_telegram(msg)
    print(f"✅ Trade added to Radar and Telegram sent!")
    print(f"{'='*60}\n")
    return True


if __name__ == "__main__":
    # Example usage (can be called from UI or webhook)
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: python angel_trade.py <ticker> <entry_price> <target_price> <stoploss_price> [source]")
        print("Example: python angel_trade.py INFY 1500 1800 1380 Volume")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    entry_price = float(sys.argv[2])
    target_price = float(sys.argv[3])
    stoploss_price = float(sys.argv[4])
    source = sys.argv[5] if len(sys.argv) > 5 else 'Manual'
    
    notify_trade_confirmation(ticker, entry_price, target_price, stoploss_price, source)
