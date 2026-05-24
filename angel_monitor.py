#!/usr/bin/env python3
"""
Angel One Position Monitor
- Runs every 15 min during market hours
- Checks open positions in radar_trades.json
- Sends Telegram ONLY when something new happens
- Updates radar_trades.json with latest status
"""

import os
import json
import pyotp
import requests
import yfinance as yf
from datetime import datetime, date
from SmartApi import SmartConnect

API_KEY        = os.environ.get('ANGEL_API_KEY')
CLIENT_ID      = os.environ.get('ANGEL_CLIENT_ID')
PASSWORD       = os.environ.get('ANGEL_PASSWORD')
TOTP_SECRET    = os.environ.get('ANGEL_TOTP_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT  = os.environ.get('TELEGRAM_CHAT_ID')

RADAR_FILE = 'radar_trades.json'
BASE_URL   = "https://anuragsin17-sketch.github.io/Stock-Yard-Public"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            'chat_id': TELEGRAM_CHAT,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def load_radar():
    if not os.path.exists(RADAR_FILE):
        return []
    try:
        with open(RADAR_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_radar(trades):
    with open(RADAR_FILE, 'w') as f:
        json.dump(trades, f, indent=2)

def get_live_price(ticker):
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

def check_angel_order_status(smart, order_id):
    """Check if order is still open or executed in Angel One"""
    try:
        orders = smart.orderBook()
        if orders and orders.get('data'):
            for order in orders['data']:
                if order.get('orderid') == order_id:
                    return order.get('status', 'UNKNOWN')
    except Exception as e:
        print(f"Order status error: {e}")
    return None

def monitor_positions():
    print(f"POSITION MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print("="*60)

    trades = load_radar()
    open_trades = [t for t in trades if t.get('status') == 'Open']

    if not open_trades:
        print("No open positions to monitor")
        return

    print(f"Monitoring {len(open_trades)} open positions...")

    # Login to Angel One
    smart = None
    try:
        if all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
            smart = SmartConnect(api_key=API_KEY)
            totp = pyotp.TOTP(TOTP_SECRET).now()
            session = smart.generateSession(CLIENT_ID, PASSWORD, totp)
            if session and session.get('status') == True:
                print(f"Logged in to Angel One")
            else:
                smart = None
                print("Angel One login failed - using yfinance only")
    except Exception as e:
        smart = None
        print(f"Angel One login error: {e}")

    changed = False

    for trade in trades:
        if trade.get('status') != 'Open':
            continue

        ticker = trade['ticker']
        entry = trade['entry_price']
        target = trade['target']
        stop = trade['stop_loss']
        order_id = trade.get('order_id', '')

        print(f"\n  {ticker}: Entry Rs{entry} | Target Rs{target} | Stop Rs{stop}")

        # Check Angel One order status first
        angel_status = None
        if smart and order_id:
            angel_status = check_angel_order_status(smart, order_id)
            print(f"  Angel One status: {angel_status}")

        # Get live price
        current_price = get_live_price(ticker)
        if not current_price:
            print(f"  Could not get price for {ticker}")
            continue

        print(f"  Current price: Rs{current_price:.2f}")

        pnl_pct = ((current_price - entry) / entry) * 100
        print(f"  P&L: {pnl_pct:+.2f}%")

        # Determine if position closed
        new_status = None
        exit_price = current_price

        # Check Angel One order status
        if angel_status in ['complete', 'COMPLETE', 'filled', 'FILLED']:
            if current_price >= target * 0.98:
                new_status = 'Target Hit'
            else:
                new_status = 'Stop Loss'

        # Fallback: check price vs target/stop
        elif current_price >= target:
            new_status = 'Target Hit'
        elif current_price <= stop:
            new_status = 'Stop Loss'

        if new_status:
            trade['status'] = new_status
            trade['exit_price'] = round(exit_price, 2)
            trade['closed_at'] = datetime.now().isoformat()
            trade['final_pnl_pct'] = round(pnl_pct, 2)
            changed = True

            # Send Telegram notification
            icon = "TARGET HIT" if new_status == 'Target Hit' else "STOP LOSS HIT"
            color = "+20%" if new_status == 'Target Hit' else "-8%"

            msg = (
                f"{icon} - ANGEL ONE\n\n"
                f"Stock: {ticker}\n"
                f"Entry: Rs{entry:,.2f}\n"
                f"Exit: Rs{exit_price:,.2f}\n"
                f"P&L: {pnl_pct:+.2f}%\n"
                f"Source: {trade.get('source', 'Trendline')}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}\n\n"
                f"View Radar: {BASE_URL}"
            )
            send_telegram(msg)
            print(f"  {new_status} - Telegram sent!")

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
    monitor_positions()
