#!/usr/bin/env python3
"""
Local webhook server to receive Angel One order requests from GitHub Actions
Runs on your local machine with static IP or Cloudflare Tunnel
"""

import os
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

class WebhookHandler(BaseHTTPRequestHandler):
    
    def do_POST(self):
        """Handle incoming webhook from GitHub Actions"""
        if self.path == '/angel-order':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                
                # Validate webhook secret (optional but recommended)
                webhook_secret = os.environ.get('WEBHOOK_SECRET', '')
                if webhook_secret and data.get('secret') != webhook_secret:
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'Unauthorized')
                    return
                
                # Set environment variables for angel_trade.py
                os.environ['TRADE_SYMBOL'] = data['symbol']
                os.environ['TRADE_ACTION'] = data['action']
                os.environ['TRADE_PRICE'] = str(data['price'])
                os.environ['TRADE_QUANTITY'] = str(data['quantity'])
                
                print(f"\n📥 Received order request:")
                print(f"   Stock: {data['symbol']}")
                print(f"   Action: {data['action']}")
                print(f"   Price: ₹{data['price']}")
                print(f"   Quantity: {data['quantity']}")
                
                # Execute angel_trade.py
                result = subprocess.run(
                    ['python', 'angel_trade.py'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                response = {
                    'success': result.returncode == 0,
                    'message': 'Order executed' if result.returncode == 0 else 'Order failed',
                    'output': result.stdout + '\n' + result.stderr
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
                print(f"✅ Order processed: {response['message']}")
                
            except Exception as e:
                error_response = {
                    'success': False,
                    'message': f'Error: {str(e)}',
                    'output': ''
                }
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
                print(f"❌ Error: {e}")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=8888):
    server_address = ('', port)
    httpd = HTTPServer(server_address, WebhookHandler)
    
    print(f"")
    print(f"🚀 Angel One Webhook Server Started!")
    print(f"")
    print(f"📍 Listening on: http://localhost:{port}")
    print(f"📍 Webhook endpoint: http://localhost:{port}/angel-order")
    print(f"")
    print(f"💡 Setup Instructions:")
    print(f"")
    print(f"1. Install Cloudflare Tunnel (FREE):")
    print(f"   Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
    print(f"")
    print(f"2. Run Cloudflare Tunnel:")
    print(f"   cloudflared tunnel --url http://localhost:{port}")
    print(f"")
    print(f"3. Copy the public URL (e.g., https://xyz.trycloudflare.com)")
    print(f"")
    print(f"4. Update GitHub Actions workflow to POST to:")
    print(f"   https://your-tunnel-url.trycloudflare.com/angel-order")
    print(f"")
    print(f"Press Ctrl+C to stop")
    print(f"")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n🛑 Server stopped")
        httpd.server_close()


if __name__ == '__main__':
    # Check if Angel One credentials are set
    required_vars = ['ANGEL_API_KEY', 'ANGEL_CLIENT_ID', 'ANGEL_PASSWORD', 'ANGEL_TOTP_SECRET']
    missing = [v for v in required_vars if not os.environ.get(v)]
    
    if missing:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing)}")
        print(f"   Set them before running this server")
        print(f"")
    
    run_server(8888)
