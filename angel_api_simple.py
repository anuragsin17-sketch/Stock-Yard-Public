#!/usr/bin/env python3
import os
import sys
import json
import requests
import pyotp
from SmartApi import SmartConnect
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

def get_session():
    try:
        api_key = os.environ.get('ANGEL_API_KEY', '')
        client_id = os.environ.get('ANGEL_CLIENT_ID', '')
        password = os.environ.get('ANGEL_PASSWORD', '')
        totp_secret = os.environ.get('ANGEL_TOTP_SECRET', '')
        
        smart = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_secret).now()
        session = smart.generateSession(client_id, password, totp)
        
        if session.get('status'):
            return smart
        return None
    except Exception as e:
        print(f"Session error: {e}")
        return None

def send_telegram(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    if not token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
        return True
    except:
        return False

@app.route('/api/place-order', methods=['POST'])
def place_order():
    try:
        data = request.json
        ticker = data.get('ticker', '').upper()
        price = float(data.get('price', 0))
        quantity = int(data.get('quantity', 1))
        target = float(data.get('target', 0))
        stoploss = float(data.get('stoploss', 0))
        
        print(f"Placing order: {ticker} x{quantity} @ Rs{price}")
        
        smart = get_session()
        if not smart:
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
        
        search = smart.searchScrip("NSE", ticker)
        if not search.get('data'):
            return jsonify({'success': False, 'error': 'Symbol not found'}), 400
        
        scrip = None
        for s in search['data']:
            if s.get('tradingsymbol') == f"{ticker}-EQ":
                scrip = s
                break
        
        if not scrip:
            scrip = search['data'][0]
        
        trading_symbol = scrip.get('tradingsymbol')
        symbol_token = scrip.get('symboltoken')
        
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": trading_symbol,
            "symboltoken": symbol_token,
            "transactiontype": "BUY",
            "exchange": "NSE",
            "ordertype": "LIMIT",
            "producttype": "DELIVERY",
            "duration": "DAY",
            "price": str(int(price)),
            "quantity": str(quantity),
            "squareoff": "0",
            "stoploss": "0",
            "trailingstoploss": "0"
        }
        
        result = smart.placeOrder(order_params)
        
        if isinstance(result, str):
            order_id = result
        elif isinstance(result, dict) and result.get('status'):
            order_id = result.get('data', {}).get('orderid')
        else:
            return jsonify({'success': False, 'error': 'Order failed'}), 400
        
        if order_id:
            trade_value = price * quantity
            msg = f"ORDER PLACED\nStock: {ticker}\nQty: {quantity} @ Rs{price}\nValue: Rs{trade_value:,.0f}\nOrder ID: {order_id}"
            send_telegram(msg)
            
            return jsonify({
                'success': True,
                'order_id': order_id,
                'ticker': ticker,
                'quantity': quantity,
                'price': price
            }), 200
        else:
            return jsonify({'success': False, 'error': 'No order ID returned'}), 400
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'Stock Yard Angel One API'}), 200

if __name__ == '__main__':
    print("Starting Stock Yard Angel One Order API")
    print("Listening on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
