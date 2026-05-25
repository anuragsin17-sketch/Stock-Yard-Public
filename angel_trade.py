#!/usr/bin/env python3
"""
Angel One SmartAPI Trade Executor
Simple MARKET ORDER — just stock, action, quantity.
Credentials stored ONLY in GitHub Secrets.
"""

import os
import sys
import json
import pyotp
import requests
from datetime import datetime
from SmartApi import SmartConnect

# ── Credentials from GitHub Secrets ──────────────────────────────────────────
API_KEY        = os.environ.get('ANGEL_API_KEY', '').strip()
CLIENT_ID      = os.environ.get('ANGEL_CLIENT_ID', '').strip()
PASSWORD       = os.environ.get('ANGEL_PASSWORD', '').strip()
TOTP_SECRET    = os.environ.get('ANGEL_TOTP_SECRET', '').strip()
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
TELEGRAM_CHAT  = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

# ── Order params (only 3 required) ───────────────────────────────────────────
SYMBOL   = os.environ.get('TRADE_SYMBOL', '').strip().upper()
ACTION   = os.environ.get('TRADE_ACTION', 'BUY').strip().upper()
SOURCE   = os.environ.get('TRADE_SOURCE', 'Manual').strip()

def _safe_int(val, default=0):
    try:
        return max(0, int(str(val).strip()))
    except Exception:
        return default

QUANTITY = _safe_int(os.environ.get('TRADE_QUANTITY', '0'))

print("=== TRADE REQUEST ===")
print(f"SYMBOL   : {SYMBOL}")
print(f"ACTION   : {ACTION}")
print(f"QUANTITY : {QUANTITY}")
print(f"SOURCE   : {SOURCE}")
print(f"API_KEY  : {'SET' if API_KEY else 'MISSING'}")
print(f"CLIENT_ID: {'SET' if CLIENT_ID else 'MISSING'}")
print(f"PASSWORD : {'SET' if PASSWORD else 'MISSING'}")
print(f"TOTP     : {'SET' if TOTP_SECRET else 'MISSING'}")
print("=====================")


def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("Telegram not configured")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={'chat_id': TELEGRAM_CHAT, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10
        )
    except Exception as e:
        print(f"Telegram error: {e}")


def get_symbol_token(smart, symbol):
    """Get NSE token — returns (trading_symbol, token)"""
    symbol_map = {'CENTRALBNK': 'CENTRALBK'}
    search = symbol_map.get(symbol, symbol)

    # Try searchScrip first
    try:
        data = smart.searchScrip("NSE", search)
        print(f"searchScrip({search}): {data}")
        if data and data.get('data'):
            results = data['data']
            for item in results:
                ts = item.get('tradingsymbol', '')
                if ts == f"{search}-EQ":
                    return ts, item['symboltoken']
            for item in results:
                ts = item.get('tradingsymbol', '')
                if ts == search:
                    return ts, item['symboltoken']
            for item in results:
                ts = item.get('tradingsymbol', '')
                if ts.endswith('-EQ'):
                    return ts, item['symboltoken']
            item = results[0]
            return item.get('tradingsymbol', search), item['symboltoken']
    except Exception as e:
        print(f"searchScrip error: {e}")

    # Fallback: Angel One instrument master
    try:
        print("Trying instrument master fallback...")
        resp = requests.get(
            "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
            timeout=15
        )
        if resp.status_code == 200:
            for inst in resp.json():
                if inst.get('exch_seg') == 'NSE' and inst.get('symbol', '').upper() == f"{symbol}-EQ":
                    return inst['symbol'], inst['token']
    except Exception as e:
        print(f"Instrument master error: {e}")

    return None, None


def save_to_radar(order_id, symbol_token):
    radar_file = 'radar_trades.json'
    trades = []
    if os.path.exists(radar_file):
        try:
            with open(radar_file) as f:
                trades = json.load(f)
        except Exception:
            pass
    trades = [t for t in trades if not (t.get('ticker') == SYMBOL and t.get('status') == 'Open')]
    trades.append({
        'order_id': order_id,
        'ticker': SYMBOL,
        'symbol_token': symbol_token,
        'action': ACTION,
        'quantity': QUANTITY,
        'order_type': 'MARKET',
        'source': SOURCE,
        'status': 'Open',
        'placed_at': datetime.now().isoformat()
    })
    with open(radar_file, 'w') as f:
        json.dump(trades, f, indent=2)
    print(f"Saved to radar_trades.json")


def place_order():
    # Validate credentials
    if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
        missing = [k for k, v in {'API_KEY': API_KEY, 'CLIENT_ID': CLIENT_ID,
                                   'PASSWORD': PASSWORD, 'TOTP_SECRET': TOTP_SECRET}.items() if not v]
        msg = f"Missing GitHub Secrets: {', '.join(missing)}"
        print(f"❌ {msg}")
        send_telegram(f"❌ Order failed — {msg}")
        sys.exit(1)

    # Validate order params
    if not SYMBOL:
        print("❌ TRADE_SYMBOL is empty")
        send_telegram("❌ Order failed — TRADE_SYMBOL is empty")
        sys.exit(1)
    if QUANTITY <= 0:
        print(f"❌ TRADE_QUANTITY is {QUANTITY} — must be > 0")
        send_telegram(f"❌ Order failed — invalid quantity: {QUANTITY}")
        sys.exit(1)
    if ACTION not in ('BUY', 'SELL'):
        print(f"❌ TRADE_ACTION is '{ACTION}' — must be BUY or SELL")
        send_telegram(f"❌ Order failed — invalid action: {ACTION}")
        sys.exit(1)

    print(f"\n🚀 Placing {ACTION} MARKET ORDER: {SYMBOL} x{QUANTITY}")

    try:
        # Login
        smart = SmartConnect(api_key=API_KEY)
        totp_code = pyotp.TOTP(TOTP_SECRET).now()
        print(f"TOTP: {totp_code}")
        session = smart.generateSession(CLIENT_ID, PASSWORD, totp_code)
        print(f"Session: {session}")

        if not session or not session.get('status'):
            msg = f"Login failed: {session.get('message', 'No session') if session else 'None returned'}"
            print(f"❌ {msg}")
            send_telegram(f"❌ {msg}")
            sys.exit(1)

        print(f"✅ Logged in as {CLIENT_ID}")

        # Get symbol token
        trading_symbol, symbol_token = get_symbol_token(smart, SYMBOL)
        if not symbol_token:
            msg = f"Symbol not found: {SYMBOL}"
            print(f"❌ {msg}")
            send_telegram(f"❌ {msg}")
            sys.exit(1)

        print(f"Symbol: {trading_symbol} | Token: {symbol_token}")

        # Place LIMIT ORDER — only Stock, Action, Entry Price, Quantity
        order_params = {
            "variety":         "NORMAL",
            "tradingsymbol":   trading_symbol,
            "symboltoken":     symbol_token,
            "transactiontype": ACTION,
            "exchange":        "NSE",
            "ordertype":       "LIMIT",
            "producttype":     "DELIVERY",
            "duration":        "DAY",
            "price":           str(round(PRICE, 2)),
            "quantity":        str(QUANTITY)
        }

        print(f"Order params: {json.dumps(order_params, indent=2)}")
        response = smart.placeOrder(order_params)
        print(f"Response: {response}")

        if not response:
            msg = f"No response from Angel One for {SYMBOL}"
            print(f"❌ {msg}")
            send_telegram(f"❌ {msg}")
            sys.exit(1)

        # Handle response — some versions return orderid directly as string
        if isinstance(response, str):
            order_id = response
            success = bool(order_id)
        else:
            success = response.get('status', False)
            data = response.get('data', {})
            order_id = data if isinstance(data, str) else (data.get('orderid', '') if data else '')

        if success or order_id:
            save_to_radar(order_id or 'N/A', symbol_token)
            msg = (
                f"✅ *ORDER PLACED — ANGEL ONE*\n\n"
                f"Stock: `{SYMBOL}`\n"
                f"Action: *{ACTION}* (MARKET)\n"
                f"Qty: *{QUANTITY}* shares\n"
                f"Order ID: `{order_id or 'N/A'}`\n"
                f"Source: {SOURCE}\n"
                f"Time: {datetime.now().strftime('%d %b %Y, %H:%M IST')}"
            )
            print(f"✅ Order placed! ID: {order_id}")
            send_telegram(msg)
        else:
            err = response.get('message', 'Unknown error') if isinstance(response, dict) else str(response)
            msg = f"Order FAILED for {SYMBOL}: {err}"
            print(f"❌ {msg}")
            send_telegram(f"❌ {msg}")
            sys.exit(1)

    except Exception as e:
        msg = f"Exception placing order for {SYMBOL}: {e}"
        print(f"❌ {msg}")
        send_telegram(f"❌ {msg}")
        sys.exit(1)


if __name__ == "__main__":
    place_order()
