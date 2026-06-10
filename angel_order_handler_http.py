#!/usr/bin/env python3
"""
Angel One Order Handler - Using native HTTP server (no Flask dependency)
This version uses only stdlib http.server to avoid Flask dependency issues on EC2
"""
import os
import sys
import json
import pyotp
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from SmartApi import SmartConnect
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global SmartConnect session (cached)
_smart_session = None

def load_credentials():
    """Load credentials from environment"""
    creds = {
        'ANGEL_API_KEY': os.environ.get('ANGEL_API_KEY'),
        'ANGEL_CLIENT_ID': os.environ.get('ANGEL_CLIENT_ID'),
        'ANGEL_PASSWORD': os.environ.get('ANGEL_PASSWORD'),
        'ANGEL_TOTP_SECRET': os.environ.get('ANGEL_TOTP_SECRET'),
    }
    missing = [k for k, v in creds.items() if not v]
    if missing:
        logger.error(f"Missing credentials: {', '.join(missing)}")
        return None
    return creds

def get_angel_session():
    """Get authenticated SmartConnect session (cached)"""
    global _smart_session
    
    if _smart_session:
        try:
            # Test if session is still valid
            orders = _smart_session.orderBook()
            if isinstance(orders, dict) and 'data' in orders:
                return _smart_session
        except:
            _smart_session = None
    
    creds = load_credentials()
    if not creds:
        logger.error("Cannot authenticate: credentials missing")
        return None
    
    try:
        logger.info("Creating new Angel One session...")
        smart = SmartConnect(api_key=creds['ANGEL_API_KEY'])
        totp = pyotp.TOTP(creds['ANGEL_TOTP_SECRET']).now()
        
        session = smart.generateSession(
            creds['ANGEL_CLIENT_ID'],
            creds['ANGEL_PASSWORD'],
            totp
        )
        
        if not isinstance(session, dict) or not session.get('status'):
            logger.error(f"Session failed: {session}")
            return None
        
        logger.info("Angel One session created successfully")
        _smart_session = smart
        return smart
        
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        return None

def send_json_response(handler, status, data):
    """Send JSON response"""
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())

class OrderHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler"""
    
    def log_message(self, format, *args):
        """Override logging to use our logger"""
        logger.info(format % args)
    
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        
        if path == '/health':
            creds = load_credentials()
            if creds:
                send_json_response(self, 200, {
                    'status': 'ok',
                    'service': 'angel-order-handler',
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("Health check: OK")
            else:
                send_json_response(self, 503, {
                    'status': 'error',
                    'error': 'Missing credentials'
                })
                logger.warning("Health check: Credentials missing")
        else:
            send_json_response(self, 404, {'error': 'Not found'})
    
    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            send_json_response(self, 400, {'success': False, 'error': 'Invalid JSON'})
            return
        
        if path == '/api/verify-token':
            self.verify_token(data)
        elif path == '/api/place-order':
            self.place_order(data)
        elif path == '/api/order-status':
            self.order_status(data)
        else:
            send_json_response(self, 404, {'error': 'Not found'})
    
    def verify_token(self, data):
        """Verify trade confirmation token"""
        try:
            token = data.get('token', '').strip()
            
            if not token:
                logger.warning("Token verification: No token provided")
                send_json_response(self, 400, {
                    'success': False,
                    'error': 'No token provided'
                })
                return
            
            if not os.path.exists('active_trade_tokens.json'):
                logger.warning("Token verification: No tokens file")
                send_json_response(self, 404, {
                    'success': False,
                    'error': 'No active tokens'
                })
                return
            
            with open('active_trade_tokens.json') as f:
                tokens = json.load(f)
            
            if token not in tokens:
                logger.warning("Token verification: Invalid token")
                send_json_response(self, 401, {
                    'success': False,
                    'error': 'Invalid token'
                })
                return
            
            token_data = tokens[token]
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            
            if datetime.now() > expires_at:
                del tokens[token]
                with open('active_trade_tokens.json', 'w') as f:
                    json.dump(tokens, f, indent=2)
                logger.warning("Token verification: Token expired")
                send_json_response(self, 401, {
                    'success': False,
                    'error': 'Token expired'
                })
                return
            
            logger.info(f"Token verified: {token[:10]}...")
            send_json_response(self, 200, {
                'success': True,
                'trade': token_data,
                'token_expires_in_seconds': int((expires_at - datetime.now()).total_seconds())
            })
            
        except Exception as e:
            logger.error(f"Token verification error: {e}", exc_info=True)
            send_json_response(self, 500, {'success': False, 'error': str(e)})
    
    def place_order(self, data):
        """Place order on Angel One"""
        try:
            token = data.get('token', '').strip()
            symbol = data.get('symbol')
            quantity = int(data.get('quantity', 1))
            entry_price = float(data.get('entry_price', 0))
            target_price = float(data.get('target_price', 0))
            stop_loss = float(data.get('stop_loss', 0))
            
            # Verify token
            if not os.path.exists('active_trade_tokens.json'):
                logger.warning("Order placement: No tokens file")
                send_json_response(self, 401, {'success': False, 'error': 'No valid token'})
                return
            
            with open('active_trade_tokens.json') as f:
                tokens = json.load(f)
            
            if token not in tokens:
                logger.warning("Order placement: Invalid token")
                send_json_response(self, 401, {'success': False, 'error': 'Invalid token'})
                return
            
            token_data = tokens[token]
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            
            if datetime.now() > expires_at:
                del tokens[token]
                with open('active_trade_tokens.json', 'w') as f:
                    json.dump(tokens, f, indent=2)
                logger.warning("Order placement: Token expired")
                send_json_response(self, 401, {'success': False, 'error': 'Token expired'})
                return
            
            # Verify symbol matches
            if token_data.get('ticker') != symbol:
                logger.warning(f"Order placement: Symbol mismatch {symbol} vs {token_data.get('ticker')}")
                send_json_response(self, 403, {'success': False, 'error': 'Symbol mismatch'})
                return
            
            logger.info(f"Order request: {symbol} x{quantity} @ Rs{entry_price}")
            
            # Get session
            smart = get_angel_session()
            if not smart:
                logger.error("Order placement: Angel One connection failed")
                send_json_response(self, 401, {'success': False, 'error': 'Failed to connect to Angel One'})
                return
            
            # Search for symbol
            try:
                search_result = smart.searchScrip("NSE", symbol)
            except Exception as e:
                logger.error(f"Symbol search failed: {e}")
                send_json_response(self, 500, {'success': False, 'error': f'Symbol search failed: {e}'})
                return
            
            if not search_result.get('data'):
                logger.warning(f"Order placement: Symbol {symbol} not found")
                send_json_response(self, 404, {'success': False, 'error': f'Symbol {symbol} not found'})
                return
            
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
            
            logger.info(f"Placing order: {trading_symbol}")
            result = smart.placeOrder(order_params)
            
            if isinstance(result, str):
                order_id = result
            elif isinstance(result, dict) and result.get('status'):
                order_id = result.get('data', result.get('orderid'))
            else:
                logger.error(f"Order placement failed: {result}")
                send_json_response(self, 400, {'success': False, 'error': 'Order placement failed'})
                return
            
            logger.info(f"Order placed successfully: {order_id}")
            
            # Save order record
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
            
            # Append to log
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
            with open('active_trade_tokens.json', 'w') as f:
                json.dump(tokens, f, indent=2)
            
            send_json_response(self, 200, {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'quantity': quantity,
                'message': f'Order placed successfully! Order ID: {order_id}'
            })
            
        except Exception as e:
            logger.error(f"Order placement error: {e}", exc_info=True)
            send_json_response(self, 500, {'success': False, 'error': str(e)})
    
    def order_status(self, data):
        """Get order status"""
        try:
            order_id = data.get('order_id', '').strip()
            
            if not order_id:
                send_json_response(self, 400, {'success': False, 'error': 'No order ID'})
                return
            
            smart = get_angel_session()
            if not smart:
                logger.error("Order status: Angel One connection failed")
                send_json_response(self, 401, {'success': False, 'error': 'Connection failed'})
                return
            
            try:
                orders = smart.orderBook()
            except Exception as e:
                logger.error(f"Order book query failed: {e}")
                send_json_response(self, 500, {'success': False, 'error': f'Order book query failed: {e}'})
                return
            
            if not isinstance(orders, dict) or not orders.get('data'):
                logger.warning(f"Order status: No orders found")
                send_json_response(self, 404, {'success': False, 'error': 'No orders found'})
                return
            
            for order in orders['data']:
                if order.get('orderid') == order_id:
                    logger.info(f"Order status found: {order_id} - {order.get('status')}")
                    send_json_response(self, 200, {
                        'success': True,
                        'order': {
                            'order_id': order.get('orderid'),
                            'symbol': order.get('tradingsymbol'),
                            'status': order.get('status'),
                            'quantity': order.get('quantity'),
                            'filled': order.get('filledshares'),
                            'price': order.get('price')
                        }
                    })
                    return
            
            logger.warning(f"Order not found: {order_id}")
            send_json_response(self, 404, {'success': False, 'error': 'Order not found'})
            
        except Exception as e:
            logger.error(f"Order status error: {e}", exc_info=True)
            send_json_response(self, 500, {'success': False, 'error': str(e)})
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    creds = load_credentials()
    if not creds:
        logger.error("FATAL: Required environment variables not set!")
        sys.exit(1)
    
    logger.info("Angel One Order Handler starting")
    logger.info("Listening on 0.0.0.0:5000")
    
    server = HTTPServer(('0.0.0.0', 5000), OrderHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()
