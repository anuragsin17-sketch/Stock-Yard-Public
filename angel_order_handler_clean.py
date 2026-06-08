#!/usr/bin/env python3
import os, sys, json, secrets, pyotp, logging
from SmartApi import SmartConnect
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)
app = Flask(__name__)

def load_credentials():
    creds = {
        'ANGEL_API_KEY': os.environ.get('ANGEL_API_KEY'),
        'ANGEL_CLIENT_ID': os.environ.get('ANGEL_CLIENT_ID'),
        'ANGEL_PASSWORD': os.environ.get('ANGEL_PASSWORD'),
        'ANGEL_TOTP_SECRET': os.environ.get('ANGEL_TOTP_SECRET'),
    }
    missing = [k for k, v in creds.items() if not v]
    if missing:
        logger.warning(f"Missing: {', '.join(missing)}")
        return None
    return creds

def get_angel_session():
    creds = load_credentials()
    if not creds:
        logger.error("Credentials not configured")
        return None
    try:
        smart = SmartConnect(api_key=creds['ANGEL_API_KEY'])
        totp = pyotp.TOTP(creds['ANGEL_TOTP_SECRET']).now()
        session = smart.generateSession(creds['ANGEL_CLIENT_ID'], creds['ANGEL_PASSWORD'], totp)
        if not isinstance(session, dict) or not session.get('status'):
            logger.error("Session failed")
            return None
        logger.info("Angel One connected")
        return smart
    except Exception as e:
        logger.error(f"Session error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    creds = load_credentials()
    if creds:
        return jsonify({'status': 'ok', 'service': 'angel-api'}), 200
    return jsonify({'status': 'error', 'error': 'No credentials'}), 503

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    try:
        data = request.json
        token = data.get('token', '').strip()
        if not token:
            return jsonify({'success': False, 'error': 'No token'}), 400
        
        if not os.path.exists('active_trade_tokens.json'):
            return jsonify({'success': False, 'error': 'No tokens'}), 404
        
        with open('active_trade_tokens.json') as f:
            tokens = json.load(f)
        
        if token not in tokens:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        token_data = tokens[token]
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            del tokens[token]
            with open('active_trade_tokens.json', 'w') as f:
                json.dump(tokens, f)
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        
        logger.info(f"Token verified: {token[:10]}...")
        return jsonify({'success': True, 'trade': token_data}), 200
    except Exception as e:
        logger.error(f"Verify error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/place-order', methods=['POST'])
def place_order():
    try:
        data = request.json
        token = data.get('token', '').strip()
        symbol = data.get('symbol')
        quantity = int(data.get('quantity', 1))
        entry_price = float(data.get('entry_price', 0))
        target_price = float(data.get('target_price', 0))
        stop_loss = float(data.get('stop_loss', 0))
        
        if not os.path.exists('active_trade_tokens.json'):
            return jsonify({'success': False, 'error': 'No token file'}), 401
        
        with open('active_trade_tokens.json') as f:
            tokens = json.load(f)
        
        if token not in tokens:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        token_data = tokens[token]
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        
        if token_data.get('ticker') != symbol:
            logger.warning(f"Symbol mismatch: {symbol} vs {token_data.get('ticker')}")
            return jsonify({'success': False, 'error': 'Symbol mismatch'}), 403
        
        logger.info(f"Order request: {symbol} x{quantity} @ Rs{entry_price}")
        
        smart = get_angel_session()
        if not smart:
            return jsonify({'success': False, 'error': 'Angel One connection failed'}), 401
        
        search_result = smart.searchScrip("NSE", symbol)
        if not search_result.get('data'):
            return jsonify({'success': False, 'error': f'Symbol {symbol} not found'}), 404
        
        scrip_data = None
        for result in search_result['data']:
            if result.get('tradingsymbol') == symbol + '-EQ':
                scrip_data = result
                break
        
        if not scrip_data:
            scrip_data = search_result['data'][0]
        
        trading_symbol = scrip_data.get('tradingsymbol')
        symbol_token = scrip_data.get('symboltoken')
        
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
        
        logger.info(f"Placing order: {trading_symbol}")
        result = smart.placeOrder(order_params)
        
        if isinstance(result, str):
            order_id = result
        elif isinstance(result, dict) and result.get('status'):
            order_id = result.get('data', result.get('orderid'))
        else:
            logger.error(f"Order failed: {result}")
            return jsonify({'success': False, 'error': 'Order placement failed'}), 400
        
        logger.info(f"Order placed: {order_id}")
        
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
        
        del tokens[token]
        with open('active_trade_tokens.json', 'w') as f:
            json.dump(tokens, f)
        
        return jsonify({'success': True, 'order_id': order_id, 'symbol': symbol, 'quantity': quantity}), 200
        
    except Exception as e:
        logger.error(f"Order error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/order-status/<order_id>', methods=['GET'])
def order_status(order_id):
    try:
        smart = get_angel_session()
        if not smart:
            return jsonify({'success': False, 'error': 'Connection failed'}), 401
        
        orders = smart.orderBook()
        if not isinstance(orders, dict) or not orders.get('data'):
            return jsonify({'success': False, 'error': 'No orders'}), 404
        
        for order in orders['data']:
            if order.get('orderid') == order_id:
                return jsonify({'success': True, 'order': {
                    'order_id': order.get('orderid'),
                    'symbol': order.get('tradingsymbol'),
                    'status': order.get('status'),
                    'quantity': order.get('quantity'),
                    'filled': order.get('filledshares'),
                    'price': order.get('price')
                }}), 200
        
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    creds = load_credentials()
    if not creds:
        logger.error("FATAL: Credentials not set!")
        sys.exit(1)
    logger.info("Angel API starting on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
