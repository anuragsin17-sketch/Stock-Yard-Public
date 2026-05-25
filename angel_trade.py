#!/usr/bin/env python3
"""
Angel One SmartAPI Trade Executor
Places BRACKET ORDER (entry + target + stop in one order)
Credentials stored ONLY in GitHub Secrets
"""

import os
import sys
import json
import pyotp
import requests
from datetime import datetime
from SmartApi import SmartConnect

# Credentials from GitHub Secrets
API_KEY        = os.environ.get('ANGEL_API_KEY')
CLIENT_ID      = os.environ.get('ANGEL_CLIENT_ID')
PASSWORD       = os.environ.get('ANGEL_PASSWORD')
TOTP_SECRET    = os.environ.get('ANGEL_TOTP_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT  = os.environ.get('TELEGRAM_CHAT_ID')

# Order params from workflow input
ACTION       = os.environ.get('TRADE_ACTION', 'BUY')
SYMBOL       = os.environ.get('TRADE_SYMBOL', '')
QUANTITY     = int(os.environ.get('TRADE_QUANTITY', '0'))
PRICE        = float(os.environ.get('TRADE_PRICE', '0'))
STOP_LOSS    = float(os.environ.get('TRADE_STOPLOSS', '0'))
TARGET       = float(os.environ.get('TRADE_TARGET', '0'))
SOURCE       = os.environ.get('TRADE_SOURCE', 'Trendline')

def send_telegram(message):
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
    except Exception as e:
        print(f"Telegram error: {e}")

def get_symbol_token(smart, symbol):
    """Get NSE token for symbol - returns (trading_symbol, token)"""
    # Known symbol corrections for Angel One naming
    symbol_map = {
        'CENTRALBNK': 'CENTRALBK',
        'M&M': 'M%26M',
    }
    search_symbol = symbol_map.get(symbol, symbol)

    # Try direct search first
    try:
        data = smart.searchScrip("NSE", search_symbol)
        print(f"searchScrip response for {search_symbol}: {data}")
        if data and data.get('data'):
            results = data['data']
            # Priority 1: exact match with -EQ suffix
            for item in results:
                ts = item.get('tradingsymbol', '')
                if ts == f"{search_symbol}-EQ":
                    print(f"Found exact EQ match: {ts} = {item.get('symboltoken')}")
                    return ts, item.get('symboltoken')
            # Priority 2: exact symbol match
            for item in results:
                ts = item.get('tradingsymbol', '')
                if ts == search_symbol:
                    print(f"Found exact match: {ts} = {item.get('symboltoken')}")
                    return ts, item.get('symboltoken')
            # Priority 3: any -EQ result
            for item in results:
                ts = item.get('tradingsymbol', '')
                if ts.endswith('-EQ') and search_symbol in ts:
                    print(f"Found EQ fallback: {ts} = {item.get('symboltoken')}")
                    return ts, item.get('symboltoken')
            # Last resort: first result
            item = results[0]
            ts = item.get('tradingsymbol', search_symbol)
            print(f"Using first result: {ts} = {item.get('symboltoken')}")
            return ts, item.get('symboltoken')
        else:
            print(f"No results from searchScrip for {search_symbol}")
    except Exception as e:
        print(f"searchScrip error for {symbol}: {e}")

    # Fallback: try downloading Angel One instrument list
    try:
        print(f"Trying instrument list fallback for {symbol}...")
        resp = requests.get(
            "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
            timeout=15
        )
        if resp.status_code == 200:
            instruments = resp.json()
            # Search for NSE EQ instrument
            for inst in instruments:
                if (inst.get('exch_seg') == 'NSE' and
                    inst.get('symbol', '').upper() == f"{symbol}-EQ"):
                    token = inst.get('token')
                    ts = inst.get('symbol')
                    print(f"Found via instrument list: {ts} = {token}")
                    return ts, token
            # Try without -EQ
            for inst in instruments:
                if (inst.get('exch_seg') == 'NSE' and
                    inst.get('name', '').upper() == symbol.upper()):
                    token = inst.get('token')
                    ts = inst.get('symbol')
                    print(f"Found via name match: {ts} = {token}")
                    return ts, token
    except Exception as e:
        print(f"Instrument list fallback error: {e}")

    print(f"ERROR: Could not find token for {symbol} by any method")
    return None, None

def save_trade_to_radar(order_id, symbol_token):
    """Save trade to radar_trades.json for monitoring"""
    radar_file = 'radar_trades.json'
    trades = []
    if os.path.exists(radar_file):
        try:
            with open(radar_file, 'r') as f:
                trades = json.load(f)
        except Exception:
            trades = []

    trade = {
        'order_id': order_id,
        'ticker': SYMBOL,
        'symbol_token': symbol_token,
        'action': ACTION,
        'quantity': QUANTITY,
        'entry_price': PRICE,
        'stop_loss': STOP_LOSS,
        'target': TARGET,
        'source': SOURCE,
        'status': 'Open',
        'placed_at': datetime.now().isoformat(),
        'alerted': False
    }

    # Remove existing open trade for same ticker
    trades = [t for t in trades if not (t['ticker'] == SYMBOL and t['status'] == 'Open')]
    trades.append(trade)

    with open(radar_file, 'w') as f:
        json.dump(trades, f, indent=2)
    print(f"Trade saved to radar_trades.json")

def place_order():
    if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
        msg = "Angel One credentials not configured in GitHub Secrets"
        print(msg)
        send_telegram(f"ERROR: {msg}")
        sys.exit(1)

    if not SYMBOL or QUANTITY <= 0 or PRICE <= 0:
        msg = f"Invalid order params: {SYMBOL} qty={QUANTITY} price={PRICE}"
        print(msg)
        send_telegram(f"ERROR: {msg}")
        sys.exit(1)

    print(f"Placing {ACTION} BRACKET ORDER: {SYMBOL} x{QUANTITY} @ Rs{PRICE}")
    print(f"Target: Rs{TARGET} | Stop: Rs{STOP_LOSS}")

    try:
        # Login
        smart = SmartConnect(api_key=API_KEY)
        totp_code = pyotp.TOTP(TOTP_SECRET).now()
        print(f"TOTP generated: {totp_code}")
        print(f"Logging in as CLIENT_ID: {CLIENT_ID}")
        print(f"API_KEY set: {'YES' if API_KEY else 'NO'}")
        print(f"PASSWORD set: {'YES' if PASSWORD else 'NO'}")
        print(f"TOTP_SECRET set: {'YES' if TOTP_SECRET else 'NO'}")
        session = smart.generateSession(CLIENT_ID, PASSWORD, totp_code)
        print(f"Session response: {session}")

        if not session or session.get('status') == False:
            msg = f"Angel One login failed: {session.get('message', 'Unknown') if session else 'No session returned'}"
            print(msg)
            send_telegram(f"ERROR: {msg}")
            sys.exit(1)

        print(f"Logged in as {CLIENT_ID}")

        # Get symbol token - returns (trading_symbol, token)
        trading_symbol, symbol_token = get_symbol_token(smart, SYMBOL)
        if not symbol_token:
            msg = f"Could not find token for {SYMBOL} in Angel One."
            print(msg)
            send_telegram(f"ERROR: {msg}")
            sys.exit(1)

        print(f"Using symbol: {trading_symbol}, token: {symbol_token}")

        # Place NORMAL LIMIT ORDER for delivery (CNC)
        # Bracket orders (ROBO) only work for intraday, not delivery
        order_params = {
            "variety":         "NORMAL",
            "tradingsymbol":   trading_symbol,   # Use full symbol like CENTRALBK-EQ
            "symboltoken":     symbol_token,
            "transactiontype": ACTION,
            "exchange":        "NSE",
            "ordertype":       "LIMIT",
            "producttype":     "DELIVERY",
            "duration":        "DAY",
            "price":           str(PRICE),
            "squareoff":       "0",
            "stoploss":        "0",
            "quantity":        str(QUANTITY)
        }

        print(f"Order params: {json.dumps(order_params, indent=2)}")
        order_response = smart.placeOrder(order_params)
        print(f"Response: {order_response}")

        if order_response and order_response.get('status') == True:
            order_id = order_response.get('data', {}).get('orderid', 'N/A')

            # Save to radar for monitoring
            save_trade_to_radar(order_id, symbol_token)

            # Success Telegram
            msg = (
                f"ORDER PLACED - ANGEL ONE\n\n"
                f"Stock: {SYMBOL}\n"
                f"Action: {ACTION} (LIMIT - DELIVERY)\n"
                f"Qty: {QUANTITY} shares\n"
                f"Entry: Rs{PRICE:,.2f}\n"
                f"Target: Rs{TARGET:,.2f} (+{((TARGET-PRICE)/PRICE*100):.1f}%)\n"
                f"Stop Loss: Rs{STOP_LOSS:,.2f} (-{((PRICE-STOP_LOSS)/PRICE*100):.1f}%) - Monthly Close\n"
                f"Order ID: {order_id}\n"
                f"Source: {SOURCE}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}\n\n"
                f"Monitor position in Angel One app.\n"
                f"Stop loss is monthly close based - check manually."
            )
            print(f"Order placed! ID: {order_id}")
            send_telegram(msg)

        else:
            error = order_response.get('message', 'Unknown') if order_response else 'No response'
            msg = f"Order FAILED for {SYMBOL}: {error}"
            print(msg)
            send_telegram(f"ERROR: {msg}")
            sys.exit(1)

    except Exception as e:
        msg = f"Trade error for {SYMBOL}: {str(e)}"
        print(msg)
        send_telegram(f"ERROR: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    place_order()
