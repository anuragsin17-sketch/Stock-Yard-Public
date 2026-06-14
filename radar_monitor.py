#!/usr/bin/env python3
"""
Radar Monitor - Real-time Stop Loss / Target tracking for open Radar positions.

Runs as a systemd service on EC2. Every 60 seconds it:
  1. Reads radar_trades.json (Open / Triggered trades with target & stop_loss)
  2. Fetches live LTP from the local Angel One API (/api/get-quote)
  3. Fires a Telegram alert when price hits the target or stop loss
  4. Dedupes alerts via radar_alerted.json so you are not spammed

NOTE: Only trades stored in radar_trades.json are monitored. Stop-loss/target
values that exist only in the dashboard's localStorage are NOT visible here.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────
RADAR_FILE       = '/home/ubuntu/radar_trades.json'
DASHBOARD_FILE   = '/home/ubuntu/dashboard_radar.json'
ALERTED_FILE     = '/home/ubuntu/radar_alerted.json'
QUOTE_API        = 'http://127.0.0.1:5000/api/get-quote'
CHECK_INTERVAL   = 60  # seconds

TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')


def send_telegram(message):
    """Send a Telegram message."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info("Telegram alert sent")
            return True
        logger.warning(f"Telegram failed: {r.status_code} - {r.text}")
    except Exception as e:
        logger.warning(f"Telegram error: {e}")
    return False


def get_ltp(ticker):
    """Fetch live LTP from the local Angel One API."""
    try:
        r = requests.get(QUOTE_API, params={'symbol': ticker}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                return float(data.get('ltp', 0))
        logger.warning(f"Quote fetch failed for {ticker}: {r.status_code}")
    except Exception as e:
        logger.warning(f"Quote error for {ticker}: {e}")
    return None


def load_json(path, default):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if data else default
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving {path}: {e}")


def load_alerted():
    """Load today's alert dedup record. Resets daily."""
    today = datetime.now().strftime('%Y-%m-%d')
    data = load_json(ALERTED_FILE, {})
    if data.get('date') != today:
        data = {'date': today, 'alerts': {}}
    if 'alerts' not in data:
        data['alerts'] = {}
    return data


def check_trades():
    server_trades = load_json(RADAR_FILE, [])
    dash_trades   = load_json(DASHBOARD_FILE, [])

    if not isinstance(server_trades, list):
        server_trades = []
    if not isinstance(dash_trades, list):
        dash_trades = []

    # Merge both sources. Dashboard trades take priority (user-set SL/target),
    # deduped by ticker so we don't double-alert the same stock.
    by_ticker = {}
    for t in server_trades:
        tk = (t.get('ticker') or '').upper()
        if tk:
            by_ticker[tk] = t
    for t in dash_trades:
        tk = (t.get('ticker') or '').upper()
        if tk:
            by_ticker[tk] = t  # dashboard overrides server

    trades = list(by_ticker.values())
    if not trades:
        return

    alerted = load_alerted()
    dirty = False

    for trade in trades:
        status = trade.get('status', '')
        if status not in ('Open', 'Triggered'):
            continue

        ticker = trade.get('ticker', '')
        if not ticker:
            continue

        # Support both stop_loss and stoploss key variants
        target = trade.get('target') or trade.get('targetExit') or 0
        stop   = trade.get('stop_loss') or trade.get('stoploss') or trade.get('stopLoss') or 0
        try:
            target = float(target)
            stop   = float(stop)
        except (TypeError, ValueError):
            continue

        if target <= 0 and stop <= 0:
            continue

        ltp = get_ltp(ticker)
        if ltp is None or ltp <= 0:
            continue

        entry = float(trade.get('entry_price', 0) or 0)

        # ── Target hit ──────────────────────────────────────────────
        if target > 0 and ltp >= target:
            key = f"{ticker}_TARGET"
            if key not in alerted['alerts']:
                pnl_pct = ((ltp - entry) / entry * 100) if entry > 0 else 0
                send_telegram(
                    f"🎯 *TARGET HIT*\n\n"
                    f"📈 *{ticker}*\n"
                    f"💰 LTP: ₹{ltp:,.2f}\n"
                    f"🎯 Target: ₹{target:,.2f}\n"
                    f"📊 Entry: ₹{entry:,.2f}\n"
                    f"✅ P&L: {pnl_pct:+.2f}%\n\n"
                    f"_Consider booking profit._"
                )
                alerted['alerts'][key] = datetime.now().strftime('%H:%M')
                dirty = True
                logger.info(f"TARGET HIT alert sent for {ticker} @ {ltp}")

        # ── Stop loss hit ───────────────────────────────────────────
        if stop > 0 and ltp <= stop:
            key = f"{ticker}_SL"
            if key not in alerted['alerts']:
                pnl_pct = ((ltp - entry) / entry * 100) if entry > 0 else 0
                send_telegram(
                    f"🛑 *STOP LOSS HIT*\n\n"
                    f"📉 *{ticker}*\n"
                    f"💰 LTP: ₹{ltp:,.2f}\n"
                    f"🛑 Stop Loss: ₹{stop:,.2f}\n"
                    f"📊 Entry: ₹{entry:,.2f}\n"
                    f"❌ P&L: {pnl_pct:+.2f}%\n\n"
                    f"_Consider exiting to limit loss._"
                )
                alerted['alerts'][key] = datetime.now().strftime('%H:%M')
                dirty = True
                logger.info(f"STOP LOSS alert sent for {ticker} @ {ltp}")

    if dirty:
        save_json(ALERTED_FILE, alerted)


def main():
    logger.info("Radar Monitor starting...")
    logger.info(f"Watching {RADAR_FILE} + {DASHBOARD_FILE}, checking every {CHECK_INTERVAL}s")
    send_telegram("🟢 *Radar Monitor started* — watching open positions for SL/Target hits.")

    while True:
        try:
            check_trades()
        except Exception as e:
            logger.error(f"Monitor loop error: {e}", exc_info=True)
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
