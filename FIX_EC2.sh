#!/bin/bash
# Run this script on EC2 to fix the angel-api service

echo "Stopping angel-api service..."
sudo systemctl stop angel-api

echo "Backing up old file..."
sudo cp /home/ubuntu/angel_order_handler.py /home/ubuntu/angel_order_handler.py.backup

echo "Downloading fixed version..."
# You'll need to copy the file manually, but here's what to do:
# 1. Copy the ENTIRE content from your local angel_order_handler.py
# 2. Create the file on EC2:

sudo tee /home/ubuntu/angel_order_handler.py > /dev/null << 'EOF'
#!/usr/bin/env python3
"""
Angel One Order Handler API
Receives order confirmation from dashboard and places on Angel One
Designed to run as a systemd service on EC2 with environment variable credentials
"""

import os
import sys
import json
import secrets
import pyotp
import logging
import requests
from SmartApi import SmartConnect
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

# Configure logging for systemd
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for all routes (allow browser requests from GitHub Pages)
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/health": {
        "origins": ["*"],
        "methods": ["GET", "OPTIONS"]
    }
})

# Load Angel One credentials from environment variables
def load_credentials():
    """Load credentials from environment variables (for systemd service)"""
    credentials = {
        'ANGEL_API_KEY': os.environ.get('ANGEL_API_KEY'),
        'ANGEL_CLIENT_ID': os.environ.get('ANGEL_CLIENT_ID'),
        'ANGEL_PASSWORD': os.environ.get('ANGEL_PASSWORD'),
        'ANGEL_TOTP_SECRET': os.environ.get('ANGEL_TOTP_SECRET'),
    }
    
    # Verify all required credentials are present
    missing = [k for k, v in credentials.items() if not v]
    if missing:
        logger.warning(f"Missing credentials: {', '.join(missing)}")
        return None
    
    return credentials

def send_telegram_notification(message):
    """Send Telegram notification"""
    try:
        # Hardcoded credentials (since env vars aren't loading in systemd)
        token = "8253327701:AAGNFzBJ8QwKw8x8Hg-tlvWHg18DD4lgogQ"
        chat_id = "8901309420"
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("✓ Telegram notification sent")
            return True
        else:
            logger.warning(f"✗ Telegram failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.warning(f"✗ Telegram error: {e}")
        return False

def get_angel_session():
    """Get authenticated SmartConnect session"""
    credentials = load_credentials()
    
    if not credentials:
        logger.error("Cannot create session: credentials not configured")
        return None
    
    try:
        logger.info("Creating SmartConnect session...")
        smart = SmartConnect(api_key=credentials.get('ANGEL_API_KEY'))
        logger.info("SmartConnect object created, generating TOTP...")
        
        totp = pyotp.TOTP(credentials.get('ANGEL_TOTP_SECRET')).now()
        logger.info(f"TOTP generated: {totp}")
        
        logger.info("Calling generateSession...")
        session = smart.generateSession(
            credentials.get('ANGEL_CLIENT_ID'),
            credentials.get('ANGEL_PASSWORD'),
            totp
        )
        logger.info(f"Session response received: {type(session)}")
        
        if not isinstance(session, dict) or not session.get('status'):
            logger.error(f"Session generation failed: {session}")
            return None
        
        logger.info("Angel One session created successfully")
        return smart
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - NO authentication required"""
    try:
        credentials = load_credentials()
        if credentials:
            logger.info("Health check: OK")
            return jsonify({'status': 'ok', 'service': 'angel-order-handler', 'timestamp': datetime.now().isoformat()}), 200
        else:
            logger.warning("Health check: Missing credentials")
            return jsonify({'status': 'error', 'service': 'angel-order-handler', 'error': 'Missing credentials'}), 503
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/place-order', methods=['POST'])
def place_order():
    """Place order on Angel One"""
    try:
        data = request.json
        symbol = data.get('symbol')
        quantity = int(data.get('quantity', 1))
        entry_price = float(data.get('entry_price', 0))
        target_price = float(data.get('target_price', 0))
        stop_loss = float(data.get('stop_loss', 0))
        
        logger.info(f"Order request: {symbol} x{quantity} @ Rs{entry_price}")
        
        if not symbol:
            logger.warning("Order placement failed: No symbol provided")
            return jsonify({'success': False, 'error': 'No symbol provided'}), 400
        
        # Get session
        logger.info("Getting Angel One session...")
        smart = get_angel_session()
        if not smart:
            logger.error("Order placement failed: Could not connect to Angel One")
            return jsonify({'success': False, 'error': 'Failed to connect to Angel One'}), 401
        
        logger.info("Session obtained, searching for symbol...")
        # Search for symbol
        try:
            search_result = smart.searchScrip("NSE", symbol)
            logger.info(f"Search result received: {len(search_result.get('data', []))} results")
        except Exception as e:
            logger.error(f"Symbol search failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Symbol search failed: {e}'}), 500
        
        if not search_result.get('data'):
            logger.warning(f"Order placement failed: Symbol {symbol} not found")
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
        logger.info(f"Found trading symbol: {trading_symbol}, token: {symbol_token}")
        
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
        
        logger.info(f"Sending order to Angel One with params: {order_params}")
        try:
            result = smart.placeOrder(order_params)
            logger.info(f"Order result received: {result}")
        except Exception as e:
            logger.error(f"Place order API call failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Place order failed: {e}'}), 500
        
        if isinstance(result, str):
            order_id = result
        elif isinstance(result, dict) and result.get('status'):
            order_id = result.get('data', result.get('orderid'))
        else:
            logger.error(f"Order placement failed: Unexpected result {result}")
            return jsonify({'success': False, 'error': 'Order placement failed'}), 400
        
        logger.info(f"Order placed successfully: {order_id}")
        
        # Send Telegram notification
        trade_value = entry_price * quantity
        message = f"✅ *ORDER PLACED*\n\n🔹 *Symbol:* {symbol}\n🔹 *Quantity:* {quantity}\n🔹 *Entry Price:* ₹{entry_price}\n🔹 *Target:* ₹{target_price}\n🔹 *Stop Loss:* ₹{stop_loss}\n🔹 *Order Value:* ₹{trade_value:,.0f}\n🔹 *Order ID:* `{order_id}`"
        send_telegram_notification(message)
        
        # Save order to file
        order_record = {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_loss': stop_loss,
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
            except Exception as e:
                logger.warning(f"Could not read existing orders: {e}")
                orders_log = []
        
        orders_log.append(order_record)
        
        with open('angel_orders.json', 'w') as f:
            json.dump(orders_log, f, indent=2)
        
        logger.info(f"Order logged to angel_orders.json")
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'message': f'Order placed successfully! Order ID: {order_id}'
        }), 200
        
    except Exception as e:
        logger.error(f"Order placement error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/order-status/<order_id>', methods=['GET'])
def order_status(order_id):
    """Get order status from Angel One"""
    try:
        smart = get_angel_session()
        if not smart:
            logger.error("Order status query failed: Could not connect to Angel One")
            return jsonify({'success': False, 'error': 'Failed to connect to Angel One'}), 401
        
        orders = smart.orderBook()
        if not isinstance(orders, dict) or not orders.get('data'):
            logger.warning(f"Order status query: No orders found for {order_id}")
            return jsonify({'success': False, 'error': 'No orders found'}), 404
        
        for order in orders['data']:
            if order.get('orderid') == order_id:
                logger.info(f"Order status found: {order_id} - {order.get('status')}")
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
        
        logger.warning(f"Order not found: {order_id}")
        return jsonify({'success': False, 'error': 'Order not found'}), 404
        
    except Exception as e:
        logger.error(f"Order status error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Check if credentials are configured
    creds = load_credentials()
    if not creds:
        logger.error("FATAL: Required environment variables not set!")
        logger.error("Please set: ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET")
        sys.exit(1)
    
    logger.info("Angel One Order Handler API Starting")
    logger.info("Listening on 0.0.0.0:5000 (accessible from network)")
    
    # Bind to 0.0.0.0 so it's accessible from EC2 instance outside localhost
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
EOF

echo "Restarting service..."
sudo systemctl restart angel-api

echo "Checking status..."
sudo systemctl status angel-api --no-pager

echo "Viewing logs..."
sudo journalctl -u angel-api -n 30 --no-pager

echo "Done! Service should now be listening on 0.0.0.0:5000"
