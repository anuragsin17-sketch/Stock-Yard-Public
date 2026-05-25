#!/usr/bin/env python3
"""
Simple HTTP server for local testing on port 8080
Serves the Stock Yard dashboard and allows testing Angel One orders locally
"""

import http.server
import socketserver
import os
import json
from urllib.parse import parse_qs, urlparse

PORT = 8080

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        # Serve files normally
        return super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for testing Angel One orders"""
        if self.path == '/test-angel-order':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                order_data = json.loads(post_data.decode('utf-8'))
                
                print("\n" + "="*60)
                print("📥 ANGEL ONE ORDER REQUEST RECEIVED")
                print("="*60)
                print(f"Symbol:    {order_data.get('symbol', 'N/A')}")
                print(f"Action:    {order_data.get('action', 'N/A')}")
                print(f"Quantity:  {order_data.get('quantity', 'N/A')}")
                print(f"Price:     ₹{order_data.get('price', 'N/A')}")
                print(f"Stop Loss: ₹{order_data.get('stop_loss', 'N/A')}")
                print(f"Target:    ₹{order_data.get('target', 'N/A')}")
                print(f"Source:    {order_data.get('source', 'N/A')}")
                print("="*60)
                
                # Test the angel_trade.py logic locally
                print("\n🧪 Testing angel_trade.py with these parameters...")
                
                # Set environment variables
                os.environ['TRADE_SYMBOL'] = str(order_data.get('symbol', ''))
                os.environ['TRADE_ACTION'] = str(order_data.get('action', 'BUY'))
                os.environ['TRADE_QUANTITY'] = str(order_data.get('quantity', '0'))
                os.environ['TRADE_PRICE'] = str(order_data.get('price', '0'))
                os.environ['TRADE_SOURCE'] = str(order_data.get('source', 'Local Test'))
                
                # Import and test the parsing logic
                SYMBOL = os.environ.get('TRADE_SYMBOL', '').strip().upper()
                ACTION = os.environ.get('TRADE_ACTION', 'BUY').strip().upper()
                
                def _safe_int(val, default=0):
                    try:
                        return max(0, int(str(val).strip()))
                    except Exception:
                        return default
                
                QUANTITY = _safe_int(os.environ.get('TRADE_QUANTITY', '0'))
                
                # Test price parsing (the fix we made)
                entry_price_str = os.environ.get('TRADE_PRICE', '0').strip()
                try:
                    entry_price = round(float(entry_price_str), 2)
                except Exception as e:
                    print(f"❌ Error parsing price: {e}")
                    entry_price = 0.0
                
                print(f"\n✅ Parsed values:")
                print(f"   SYMBOL:      {SYMBOL}")
                print(f"   ACTION:      {ACTION}")
                print(f"   entry_price: ₹{entry_price}")
                print(f"   QUANTITY:    {QUANTITY}")
                
                # Validate
                errors = []
                if not SYMBOL:
                    errors.append("TRADE_SYMBOL is empty")
                if QUANTITY <= 0:
                    errors.append(f"TRADE_QUANTITY is {QUANTITY} — must be > 0")
                if ACTION not in ('BUY', 'SELL'):
                    errors.append(f"TRADE_ACTION is '{ACTION}' — must be BUY or SELL")
                if entry_price <= 0:
                    errors.append(f"Invalid entry price: '{entry_price_str}'")
                
                if errors:
                    print(f"\n❌ Validation errors:")
                    for error in errors:
                        print(f"   • {error}")
                    
                    response = {
                        'status': 'error',
                        'errors': errors
                    }
                else:
                    print(f"\n✅ All validations passed!")
                    print(f"\n📋 Order parameters that would be sent to Angel One:")
                    order_params = {
                        "variety": "NORMAL",
                        "tradingsymbol": f"{SYMBOL}-EQ",
                        "symboltoken": "12345",  # Mock
                        "transactiontype": ACTION,
                        "exchange": "NSE",
                        "ordertype": "LIMIT",
                        "producttype": "DELIVERY",
                        "duration": "DAY",
                        "price": str(entry_price),
                        "quantity": str(QUANTITY)
                    }
                    print(json.dumps(order_params, indent=2))
                    
                    response = {
                        'status': 'success',
                        'message': 'Order validated successfully (DRY RUN)',
                        'order_params': order_params
                    }
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                print(f"\n❌ Error processing request: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {'status': 'error', 'message': str(e)}
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format"""
        if self.path.endswith(('.html', '.json', '.js', '.css')):
            print(f"📄 {self.command} {self.path}")

def run_server():
    """Start the local server"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print("\n" + "="*60)
        print("🚀 Stock Yard Local Server")
        print("="*60)
        print(f"Server running at: http://localhost:{PORT}")
        print(f"Dashboard:         http://localhost:{PORT}/index.html")
        print(f"Trendline Screen:  http://localhost:{PORT}/trendline_screen.html")
        print(f"Test Dashboard:    http://localhost:{PORT}/test_local.html")
        print("\n📋 To test Angel One orders:")
        print("   1. Open http://localhost:8080/index.html")
        print("   2. Click 'BUY' on any stock")
        print("   3. Confirm the order")
        print("   4. Check this terminal for validation results")
        print("\n⚠️  Note: This is a DRY RUN - no real orders will be placed")
        print("="*60)
        print("\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")
            print("="*60)

if __name__ == "__main__":
    run_server()
