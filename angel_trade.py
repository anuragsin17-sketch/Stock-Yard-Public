#!/usr/bin/env python3
"""
Angel One SmartAPI Trade Executor
Credentials stored ONLY in GitHub Secrets - never in code
"""

import os
import sys
import json
import time
import pyotp
import requests
from datetime import datetime
from SmartApi import SmartConnect

# ─── CREDENTIALS FROM GITHUB SECRETS ────────────────────────────────────────
API_KEY       = os.environ.get('ANGEL_API_KEY')
CLIENT_ID     = os.environ.get('ANGEL_CLIENT_ID')
PASSWORD      = os.environ.get('ANGEL_PASSWORD')
TOTP_SECRET   = os.environ.get('ANGEL_TOTP_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT  = os.environ.get('TELEGRAM_CHAT_ID')

# ─── ORDER PARAMS FROM WORKFLOW INPUT ────────────────────────────────────────
ACTION        = os.environ.get('TRADE_ACTION', 'BUY')   # BUY or SELL
SYMBOL        = os.environ.get('TRADE_SYMBOL', '')
TOKEN         = os.environ.get('TRADE_TOKEN', '')        # NSE token for symbol
QUANTITY      = int(os.environ.get('TRADE_QUANTITY', '0'))
PRICE         = float(os.environ.get('TRADE_PRICE', '0'))
STOP_LOSS     = float(os.environ.get('TRADE_STOPLOSS', '0'))
TARGET        = float(os.environ.get('TRADE_TARGET', '0'))
SOURCE        = os.environ.get('TRADE_SOURCE', 'Trendline')

def send_telegram(message):
    """Send Telegram notification"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("Telegram not configured")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            'chat_id': TELEGRAM_CHAT,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        print("Telegram notification sent")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_symbol_token(smart, symbol):
    """Get NSE token for a symbol"""
    try:
        # Search for symbol token
        data = smart.searchScrip("NSE", symbol)
        if data and data.get('data'):
            for item in data['data']:
                if item.get('tradingsymbol') == symbol and item.get('exch_seg') == 'NSE':
                    return item.get('symboltoken')
    except Exception as e:
        print(f"Token lookup error: {e}")
    return None

def place_order():
    """Place limit order in Angel One"""

    # Validate inputs
    if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
        msg = "❌ Angel One credentials not configured in GitHub Secrets"
        print(msg)
        send_telegram(msg)
        sys.exit(1)

    if not SYMBOL or QUANTITY <= 0 or PRICE <= 0:
        msg = f"❌ Invalid order params: {SYMBOL} qty={QUANTITY} price={PRICE}"
        print(msg)
        send_telegram(msg)
        sys.exit(1)

    print(f"🔄 Placing {ACTION} order: {SYMBOL} x{QUANTITY} @ ₹{PRICE}")

    try:
        # ── LOGIN ─────────────────────────────────────────────────────────
        smart = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        session = smart.generateSession(CLIENT_ID, PASSWORD, totp)

        if not session or session.get('status') == False:
            msg = f"❌ Angel One login failed: {session.get('message', 'Unknown error')}"
            print(msg)
            send_telegram(msg)
            sys.exit(1)

        print(f"✅ Logged in to Angel One as {CLIENT_ID}")

        # ── GET SYMBOL TOKEN ──────────────────────────────────────────────
        symbol_token = TOKEN if TOKEN else get_symbol_token(smart, SYMBOL)
        if not symbol_token:
            msg = f"❌ Could not find token for {SYMBOL}"
            print(msg)
            send_telegram(msg)
            sys.exit(1)

        print(f"✅ Symbol token: {symbol_token}")

        # ── PLACE LIMIT ORDER ─────────────────────────────────────────────
        order_params = {
            "variety":          "NORMAL",
            "tradingsymbol":    SYMBOL,
            "symboltoken":      symbol_token,
            "transactiontype":  ACTION,          # BUY or SELL
            "exchange":         "NSE",
            "ordertype":        "LIMIT",
            "producttype":      "DELIVERY",      # CNC for delivery
            "duration":         "DAY",
            "price":            str(PRICE),
            "squareoff":        "0",
            "stoploss":         "0",
            "quantity":         str(QUANTITY)
        }

        print(f"📋 Order params: {json.dumps(order_params, indent=2)}")

        order_response = smart.placeOrder(order_params)
        print(f"📊 Order response: {order_response}")

        if order_response and order_response.get('status') == True:
            order_id = order_response.get('data', {}).get('orderid', 'N/A')

            # Success notification
            msg = (
                f"✅ *Order Placed Successfully*\n\n"
                f"*Stock:* {SYMBOL}\n"
                f"*Action:* {ACTION}\n"
                f"*Qty:* {QUANTITY} shares\n"
                f"*Price:* ₹{PRICE:,.2f} (LIMIT)\n"
                f"*Stop Loss:* ₹{STOP_LOSS:,.2f}\n"
                f"*Target:* ₹{TARGET:,.2f}\n"
                f"*Order ID:* {order_id}\n"
                f"*Source:* {SOURCE}\n"
                f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n\n"
                f"_Angel One SmartAPI_"
            )
            print(f"✅ Order placed! ID: {order_id}")
            send_telegram(msg)

            # Save order to file for tracking
            order_log = {
                'order_id': order_id,
                'symbol': SYMBOL,
                'action': ACTION,
                'quantity': QUANTITY,
                'price': PRICE,
                'stop_loss': STOP_LOSS,
                'target': TARGET,
                'source': SOURCE,
                'timestamp': datetime.now().isoformat(),
                'status': 'PLACED'
            }
            with open('angel_orders.json', 'a') as f:
                f.write(json.dumps(order_log) + '\n')

        else:
            error_msg = order_response.get('message', 'Unknown error') if order_response else 'No response'
            msg = (
                f"❌ *Order Failed*\n\n"
                f"*Stock:* {SYMBOL}\n"
                f"*Error:* {error_msg}\n"
                f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}"
            )
            print(f"❌ Order failed: {error_msg}")
            send_telegram(msg)
            sys.exit(1)

    except Exception as e:
        msg = (
            f"❌ *Trade Execution Error*\n\n"
            f"*Stock:* {SYMBOL}\n"
            f"*Error:* {str(e)}\n"
            f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}"
        )
        print(f"❌ Exception: {e}")
        send_telegram(msg)
        sys.exit(1)

if __name__ == "__main__":
    place_order()
