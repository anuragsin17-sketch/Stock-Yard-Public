#!/usr/bin/env python3
"""
Telegram Trade Poller - handles Confirm/Cancel trade buttons.

Flow:
  1. Alert arrives with "✅ Confirm Trade" / "❌ Cancel Trade" callback buttons
  2. Confirm  -> bot asks for share quantity (force reply)
  3. User types quantity -> order placed directly on Angel One via /api/place-order
  4. On success -> trade appended to radar_trades.json (shows in Radar, monitored for SL/Target)
  5. Cancel   -> trade stays in Trendline, nothing placed

Runs as the telegram-poller systemd service. Only ONE updates consumer may run
(polling), so the webhook service must be disabled.
"""

import os
import json
import time
import requests
from datetime import datetime

BOT_TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ')
CHAT_ID     = os.environ.get('TELEGRAM_CHAT_ID', '8901309420')
API         = f"https://api.telegram.org/bot{BOT_TOKEN}"
PLACE_ORDER = 'http://127.0.0.1:5000/api/place-order'
RADAR_FILE  = '/home/ubuntu/radar_trades.json'
PENDING_FILE = '/tmp/pending_trade.json'

offset = 0


def send_telegram(message, reply_markup=None):
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        requests.post(f"{API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"send_telegram error: {e}")


def answer_callback(query_id, text):
    try:
        requests.post(f"{API}/answerCallbackQuery",
                      json={'callback_query_id': query_id, 'text': text, 'show_alert': False},
                      timeout=10)
    except Exception as e:
        print(f"answer_callback error: {e}")


def load_pending():
    try:
        with open(PENDING_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save_pending(data):
    with open(PENDING_FILE, 'w') as f:
        json.dump(data, f)


def clear_pending():
    try:
        os.remove(PENDING_FILE)
    except Exception:
        pass


def append_to_radar(ticker, entry, target, sl, qty, order_id):
    """Add the placed trade to radar_trades.json so it shows in Radar and gets monitored."""
    trades = []
    try:
        with open(RADAR_FILE) as f:
            trades = json.load(f)
        if not isinstance(trades, list):
            trades = []
    except Exception:
        trades = []

    # Remove any existing open entry for the same ticker to avoid duplicates
    trades = [t for t in trades if not (
        (t.get('ticker', '').upper() == ticker.upper()) and
        t.get('status') in ('Open', 'Triggered')
    )]

    trades.append({
        'ticker': ticker.upper(),
        'order_id': str(order_id),
        'entry_price': entry,
        'current_price': entry,
        'quantity': qty,
        'target': target,
        'stop_loss': sl,
        'trade_value': round(entry * qty, 2),
        'status': 'Open',
        'source': 'Telegram',
        'triggered_at': datetime.now().isoformat(),
        'execution_platform': 'Angel One (Real - DELIVERY)'
    })

    try:
        with open(RADAR_FILE, 'w') as f:
            json.dump(trades, f, indent=2)
        print(f"Appended {ticker} to radar_trades.json")
    except Exception as e:
        print(f"Error writing radar_trades.json: {e}")


def place_order(ticker, entry, target, sl, qty):
    """Place a real order on Angel One via the local order handler API."""
    try:
        resp = requests.post(PLACE_ORDER, json={
            'symbol': ticker,
            'quantity': qty,
            'entry_price': entry,
            'target_price': target,
            'stop_loss': sl
        }, timeout=120)
        data = resp.json()
        return resp.status_code, data
    except requests.exceptions.Timeout:
        return 0, {'success': False, 'error': 'timeout', 'timed_out': True}
    except Exception as e:
        return 0, {'success': False, 'error': str(e)}


print("Telegram Trade Poller started")
send_telegram("🤖 *Trade Poller online* — Confirm/Cancel buttons are live.")

while True:
    try:
        r = requests.get(f"{API}/getUpdates", params={
            'offset': offset,
            'timeout': 30,
            'allowed_updates': json.dumps(['message', 'callback_query'])
        }, timeout=35)
        updates = r.json().get('result', [])

        for update in updates:
            offset = update['update_id'] + 1
            print(f"Update keys: {list(update.keys())}")

            # ── Button clicks ───────────────────────────────────────
            if 'callback_query' in update:
                cb = update['callback_query']
                query_id = cb['id']
                data = cb.get('data', '')
                print(f"Button: {data}")

                if data.startswith('confirm_trade:'):
                    parts = data.split(':')
                    ticker = parts[1]
                    entry  = float(parts[2])
                    target = float(parts[3])
                    sl     = float(parts[4])

                    answer_callback(query_id, "Enter quantity below")
                    save_pending({'ticker': ticker, 'entry': entry, 'target': target, 'sl': sl})
                    send_telegram(
                        f"📊 *ENTER QUANTITY*\n\n"
                        f"📈 {ticker}\n"
                        f"💹 Entry: ₹{entry:,.2f}\n"
                        f"🎯 Target: ₹{target:,.2f}\n"
                        f"🛑 SL: ₹{sl:,.2f}\n\n"
                        f"_Reply with the number of shares (e.g. 5, 10, 25):_",
                        reply_markup={'force_reply': True, 'input_field_placeholder': 'Enter quantity'}
                    )

                elif data.startswith('cancel_trade:'):
                    ticker = data.split(':')[1] if ':' in data else ''
                    clear_pending()
                    answer_callback(query_id, "Trade cancelled")
                    send_telegram(f"❌ *Trade cancelled* — {ticker} stays in Trendline.")

            # ── Quantity reply ──────────────────────────────────────
            if 'message' in update:
                msg = update['message']
                text = (msg.get('text') or '').strip()
                print(f"Message received: '{text}' (pending={os.path.exists(PENDING_FILE)})")

                # Accept any digit-only message as the quantity when a trade is pending.
                # (No need for the user to use Telegram's "reply" function.)
                if text.isdigit():
                    pending = load_pending()
                    print(f"Digit message, pending={pending}")
                    if pending:
                        qty = int(text)
                        ticker = pending['ticker']
                        entry  = pending['entry']
                        target = pending['target']
                        sl     = pending['sl']

                        if qty <= 0:
                            send_telegram("⚠️ Quantity must be greater than 0.")
                        else:
                            send_telegram(f"⏳ Placing order: {qty} × {ticker} @ ₹{entry:,.2f} ...")
                            status, result = place_order(ticker, entry, target, sl, qty)

                            if result.get('success'):
                                order_id = result.get('order_id', 'N/A')
                                append_to_radar(ticker, entry, target, sl, qty, order_id)
                                send_telegram(
                                    f"✅ *ORDER PLACED*\n\n"
                                    f"📈 {ticker}\n"
                                    f"📊 Qty: {qty}\n"
                                    f"💹 Entry: ₹{entry:,.2f}\n"
                                    f"🎯 Target: ₹{target:,.2f}\n"
                                    f"🛑 SL: ₹{sl:,.2f}\n"
                                    f"📋 Order ID: `{order_id}`\n\n"
                                    f"➡️ Moved to *Radar* — now tracked for SL/Target."
                                )
                                clear_pending()
                            else:
                                err = result.get('error', 'Unknown error')
                                # 402 = insufficient funds (validation_failed)
                                if result.get('validation_failed'):
                                    send_telegram(f"🚫 *Order rejected* — {err}\n_Trade stays in Trendline._")
                                elif result.get('timed_out'):
                                    # Order API is slow (Angel login). Order likely placed —
                                    # add to Radar so it's tracked; verify in Angel One app.
                                    append_to_radar(ticker, entry, target, sl, qty, 'PENDING_VERIFY')
                                    send_telegram(
                                        f"⚠️ *Order sent — confirmation slow*\n\n"
                                        f"📈 {ticker} × {qty} @ ₹{entry:,.2f}\n\n"
                                        f"The order was submitted but Angel One was slow to confirm. "
                                        f"Added to *Radar* for tracking — please verify in your Angel One app."
                                    )
                                else:
                                    send_telegram(f"❌ *Order failed* — {err}\n_Trade stays in Trendline._")
                                clear_pending()

    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Loop error: {e}")
        time.sleep(5)
