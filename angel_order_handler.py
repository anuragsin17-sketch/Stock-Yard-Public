#!/usr/bin/env python3
"""
Angel One Order Handler API
Receives order confirmation from dashboard and places on Angel One
"""

import os
import json
import secrets
import pyotp
from SmartApi import SmartConnect
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# Load Angel One credentials
def load_credentials():
    """Load credentials from .env file"""
    credentials = {}
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    credentials[key] = value
    return credentials

def get_angel_session():
    """Get authenticated SmartConnect session"""
    credentials = load_credentials()
    
    try:
        smart = SmartConnect(api_key=credentials.get('ANGEL_API_KEY'))
        totp = pyotp.TOTP(credentials.get('ANGEL_TOTP_SECRET')).now()
        
        session = smart.generateSession(
            credentials.get('ANGEL_CLIENT_ID'),
            credentials.get('ANGEL_PASSWORD'),
            totp
        )
        
        if not isinstance(session, dict) or not session.get('status'):
            return None
        
        return smart
    except Exception as e:
        print(f"Session error: {e}")
        return None

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    """Verify trade confirmation token"""
    try:
        data = request.json
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 400
        
        tokens_file = 'active_trade_tokens.json'
        if not os.path.exists(tokens_file):
            return jsonify({'success': False, 'error': 'No active tokens'}), 404
        
        with open(tokens_file) as f:
            tokens = json.load(f)
        
        if token not in tokens:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        token_data = tokens[token]
        
        # Check expiration
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            del tokens[token]
            with open(tokens_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        
        # Return trade details
        return jsonify({
            'success': True,
            'trade': token_data,
            'token_expires_in_seconds': int((expires_at - datetime.now()).total_seconds())
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/place-order', methods=['POST'])
def place_order():
    """Place order on Angel One (requires valid token)"""
    try:
        data = request.json
        token = data.get('token', '').strip()
        symbol = data.get('symbol')
        quantity = int(data.get('quantity', 1))
        entry_price = float(data.get('entry_price', 0))
        target_price = float(data.get('target_price', 0))
        stop_loss = float(data.get('stop_loss', 0))
        
        # Verify token
        tokens_file = 'active_trade_tokens.json'
        if not os.path.exists(tokens_file):
            return jsonify({'success': False, 'error': 'No valid token'}), 401
        
        with open(tokens_file) as f:
            tokens = json.load(f)
        
        if token not in tokens:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        token_data = tokens[token]
        
        # Verify token not expired
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            del tokens[token]
            with open(tokens_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        
        # Verify symbol matches
        if token_data['ticker'] != symbol:
            return jsonify({'success': False, 'error': 'Symbol mismatch - possible security issue'}), 403
        
        print(f"\n📋 Order Placement Request:")
        print(f"   Stock: {symbol}")
        print(f"   Quantity: {quantity}")
        print(f"   Price: ₹{entry_price}")
        print(f"   Token: {token[:10]}... (verified)")
        
        # Get session
        smart = get_angel_session()
        if not smart:
            return jsonify({'success': False, 'error': 'Failed to connect to Angel One'}), 401
        
        # Search for symbol
        search_result = smart.searchScrip("NSE", symbol)
        if not search_result.get('data'):
            return jsonify({'success': False, 'error': f'Symbol {symbol} not found'}), 404
        
        # Find exact match
        scrip_data = None
        for result in search_result['data']:
            if result.get('tradingsymbol') == symbol + '-EQ':
                scrip_data = result
                break
        
        if not scrip_data:
            scrip_data = search_result['data'][0]
        
        trading_symbol = scrip_data.get('tradingsymbol')
        symbol_token = scrip_data.get('symboltoken')
        
        # Place limit order
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": trading_symbol,
            "symboltoken": symbol_token,
            "transactiontype": "BUY",
            "exchange": "NSE",
            "ordertype": "LIMIT",
            "producttype": "DELIVERY",
            "duration": "DAY",
            "price": str(int(entry_price)),
            "quantity": str(quantity),
            "squareoff": "0",
            "stoploss": "0",
            "trailingstoploss": "0"
        }
        
        print(f"   Sending to Angel One...")
        result = smart.placeOrder(order_params)
        
        if isinstance(result, str):
            order_id = result
        elif isinstance(result, dict) and result.get('status'):
            order_id = result.get('data', result.get('orderid'))
        else:
            return jsonify({'success': False, 'error': 'Order placement failed'}), 400
        
        print(f"✅ Order ID: {order_id}")
        
        # Save order to file
        order_record = {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'source': token_data['source'],
            'placed_at': datetime.now().isoformat(),
            'status': 'PENDING'
        }
        
        # Append to orders log
        orders_log = []
        if os.path.exists('angel_orders.json'):
            try:
                with open('angel_orders.json') as f:
                    orders_log = json.load(f)
                    if not isinstance(orders_log, list):
                        orders_log = []
            except:
                orders_log = []
        
        orders_log.append(order_record)
        
        with open('angel_orders.json', 'w') as f:
            json.dump(orders_log, f, indent=2)
        
        # Delete used token
        del tokens[token]
        with open(tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'message': f'Order placed successfully! Order ID: {order_id}'
        }), 200
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/order-status/<order_id>', methods=['GET'])
def order_status(order_id):
    """Get order status from Angel One"""
    try:
        smart = get_angel_session()
        if not smart:
            return jsonify({'success': False, 'error': 'Failed to connect to Angel One'}), 401
        
        orders = smart.orderBook()
        if not isinstance(orders, dict) or not orders.get('data'):
            return jsonify({'success': False, 'error': 'No orders found'}), 404
        
        for order in orders['data']:
            if order.get('orderid') == order_id:
                return jsonify({
                    'success': True,
                    'order': {
                        'order_id': order.get('orderid'),
                        'symbol': order.get('tradingsymbol'),
                        'status': order.get('status'),
                        'quantity': order.get('quantity'),
                        'filled': order.get('filledshares'),
                        'price': order.get('price')
                    }
                }), 200
        
        return jsonify({'success': False, 'error': 'Order not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n🚀 Angel One Order Handler API")
    print("Listening on http://localhost:5000")
    app.run(host='localhost', port=5000, debug=False)
