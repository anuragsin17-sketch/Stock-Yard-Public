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
from SmartApi import SmartConnect
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

# Configure logging for systemd
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

def get_angel_session():
    """Get authenticated SmartConnect session"""
    credentials = load_credentials()
    
    if not credentials:
        logger.error("Cannot create session: credentials not configured")
        return None
    
    try:
        smart = SmartConnect(api_key=credentials.get('ANGEL_API_KEY'))
        totp = pyotp.TOTP(credentials.get('ANGEL_TOTP_SECRET')).now()
        
        session = smart.generateSession(
            credentials.get('ANGEL_CLIENT_ID'),
            credentials.get('ANGEL_PASSWORD'),
            totp
        )
        
        if not isinstance(session, dict) or not session.get('status'):
            logger.error("Session generation failed")
            return None
        
        logger.info("Angel One session created successfully")
        return smart
    except Exception as e:
        logger.error(f"Session error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    credentials = load_credentials()
    if credentials:
        logger.info("Health check: OK")
        return jsonify({'status': 'ok', 'service': 'angel-order-handler'}), 200
    else:
        logger.warning("Health check: Missing credentials")
        return jsonify({'status': 'error', 'service': 'angel-order-handler', 'error': 'Missing credentials'}), 503

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    """Verify trade confirmation token"""
    try:
        data = request.json
        token = data.get('token', '').strip()
        
        if not token:
            logger.warning("Token verification failed: No token provided")
            return jsonify({'success': False, 'error': 'No token provided'}), 400
        
        tokens_file = 'active_trade_tokens.json'
        if not os.path.exists(tokens_file):
            logger.warning("Token verification failed: No active tokens file")
            return jsonify({'success': False, 'error': 'No active tokens'}), 404
        
        with open(tokens_file) as f:
            tokens = json.load(f)
        
        if token not in tokens:
            logger.warning("Token verification failed: Invalid token")
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        token_data = tokens[token]
        
        # Check expiration
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            del tokens[token]
            with open(tokens_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            logger.warning("Token verification failed: Token expired")
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        
        logger.info(f"Token verified: {token[:10]}...")
        # Return trade details
        return jsonify({
            'success': True,
            'trade': token_data,
            'token_expires_in_seconds': int((expires_at - datetime.now()).total_seconds())
        }), 200
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
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
            logger.warning("Order placement failed: No valid token file")
            return jsonify({'success': False, 'error': 'No valid token'}), 401
        
        with open(tokens_file) as f:
            tokens = json.load(f)
        
        if token not in tokens:
            logger.warning("Order placement failed: Invalid token")
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        token_data = tokens[token]
        
        # Verify token not expired
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            del tokens[token]
            with open(tokens_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            logger.warning("Order placement failed: Token expired")
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        
        # Verify symbol matches
        if token_data['ticker'] != symbol:
            logger.warning(f"Order placement failed: Symbol mismatch - {symbol} vs {token_data['ticker']}")
            return jsonify({'success': False, 'error': 'Symbol mismatch - possible security issue'}), 403
        
        logger.info(f"Order Placement Request: {symbol} x{quantity} @ Rs{entry_price}")
        
        # Get session
        smart = get_angel_session()
        if not smart:
            logger.error("Order placement failed: Could not connect to Angel One")
            return jsonify({'success': False, 'error': 'Failed to connect to Angel One'}), 401
        
        # Search for symbol
        search_result = smart.searchScrip("NSE", symbol)
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
        
        logger.info(f"Sending order to Angel One: {trading_symbol}")
        result = smart.placeOrder(order_params)
        
        if isinstance(result, str):
            order_id = result
        elif isinstance(result, dict) and result.get('status'):
            order_id = result.get('data', result.get('orderid'))
        else:
            logger.error(f"Order placement failed: {result}")
            return jsonify({'success': False, 'error': 'Order placement failed'}), 400
        
        logger.info(f"Order placed successfully: {order_id}")
        
        # Save order to file
        order_record = {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'source': token_data.get('source', 'unknown'),
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
